module uart_lms_top
(
    input clk,   // 100 MHz input
    input rx,
    output tx
);

// ============================================================
// CLOCK WIZARD (100 MHz → 20 MHz)
// ============================================================
wire clk_20mhz;
wire pll_locked;

clk_wiz_0 clk_gen ( .clk(clk_20mhz), .reset(1'b0), .locked(pll_locked), .clk_in1(clk) );

// ============================================================
// UART (100 MHz domain)
// ============================================================
wire [7:0] rx_data;
wire rx_valid;

reg tx_send = 0;
reg [7:0] tx_data = 0;
wire tx_busy;

uart_rx uart_rx_inst (
    .clk(clk),
    .rx(rx),
    .data(rx_data),
    .valid(rx_valid)
);

uart_tx uart_tx_inst (
    .clk(clk),
    .send(tx_send),
    .data(tx_data),
    .tx(tx),
    .busy(tx_busy)
);

// ============================================================
// FRAME RECEIVER (100 MHz domain)
// ============================================================
reg receiving = 0;
reg [2:0] byte_count = 0;

reg [31:0] speech = 0;
reg [31:0] noise  = 0;

reg new_sample = 0;

// Simple stop-and-wait: treat 0xAA as frame start AND as implicit ACK
parameter ACK_BYTE = 8'hAA;
reg processing = 0; // high while FPGA holds/serves current sample

always @(posedge clk)
begin
    new_sample <= 0;
    // If PLL not locked, ignore incoming frames and reset receiver state
    if (!pll_locked) begin
        receiving <= 0;
        byte_count <= 0;
        processing <= 0;
    end
    else if (rx_valid)
    begin
        if (processing)
        begin
            // When processing, accept 0xAA as implicit ACK from PC and start next frame
            if (rx_data == ACK_BYTE)
            begin
                processing <= 0;
                receiving <= 1;
                byte_count <= 0;
            end
            // otherwise ignore bytes while processing
        end
        else
        begin
            if (!receiving)
            begin
                if (rx_data == ACK_BYTE)
                begin
                    receiving <= 1;
                    byte_count <= 0;
                end
            end
            else
            begin
                case(byte_count)
                0: speech[31:24] <= rx_data;
                1: speech[23:16] <= rx_data;
                2: speech[15:8]  <= rx_data;
                3: speech[7:0]   <= rx_data;
                4: noise[31:24]  <= rx_data;
                5: noise[23:16]  <= rx_data;
                6: noise[15:8]   <= rx_data;
                7: begin
                    noise[7:0] <= rx_data;
                    new_sample <= 1;     // one pulse
                    receiving <= 0;
                    processing <= 1;     // mark we're processing this sample
                end
                endcase

                byte_count <= byte_count + 1;
            end
        end
    end
end

// ============================================================
// CDC: 100 MHz → 20 MHz (SAFE DATA + TOGGLE)
// ============================================================

// Latch data in 100 MHz domain
reg [31:0] speech_buf = 0;
reg [31:0] noise_buf  = 0;
reg toggle_100 = 0;

always @(posedge clk)
begin
    if(new_sample)
    begin
        speech_buf <= speech;
        noise_buf  <= noise;
        toggle_100 <= ~toggle_100;
    end
end

// Synchronize toggle into LMS domain
reg toggle_meta = 0;
reg toggle_lms  = 0;

always @(posedge clk_20mhz)
begin
    toggle_meta <= toggle_100;
    toggle_lms  <= toggle_meta;
end

wire new_sample_lms = toggle_meta ^ toggle_lms;

// ============================================================
// LATCH DATA (20 MHz domain)
// ============================================================
reg [31:0] x_reg = 0;
reg [31:0] d_reg = 0;

always @(posedge clk_20mhz)
begin
    if(!pll_locked)
    begin
        x_reg <= 0;
        d_reg <= 0;
    end
    else if(new_sample_lms)
    begin
        x_reg <= speech_buf;
        d_reg <= noise_buf;
    end
end

// ============================================================
// LMS (20 MHz domain)
// ============================================================
wire [31:0] lms_out;
wire lms_valid_out;

lms_q31_hls lms_inst (
    .clk(clk_20mhz),
    .rst(~pll_locked),           // proper reset
    .valid_in(new_sample_lms),   // one pulse per sample
    .x_in(x_reg),
    .d_in(d_reg),
    .valid_out(lms_valid_out),
    .e_out(lms_out)
);

// ============================================================
// CDC BACK: 20 MHz → 100 MHz
// ============================================================

reg toggle_out_lms = 0;
reg [31:0] result_latched = 0;

always @(posedge clk_20mhz)
begin
    if(lms_valid_out)
    begin
        result_latched <= lms_out;
        toggle_out_lms <= ~toggle_out_lms;
    end
end

reg toggle_out_meta = 0;
reg toggle_out_100  = 0;

always @(posedge clk)
begin
    toggle_out_meta <= toggle_out_lms;
    toggle_out_100  <= toggle_out_meta;
end

wire result_ready = toggle_out_meta ^ toggle_out_100;

// ============================================================
// TX STATE MACHINE (100 MHz domain)
// ============================================================
reg [2:0] tx_state = 0;
reg [31:0] tx_buffer = 0;

always @(posedge clk)
begin
    tx_send <= 0;

    if (!pll_locked) begin
        tx_state <= 0;
    end
    else begin
        case(tx_state)

        0:
        begin
            if(result_ready)
            begin
                tx_buffer <= result_latched;
                tx_state <= 1;
            end
        end

        1: if(!tx_busy) begin tx_data <= tx_buffer[31:24]; tx_send <= 1; tx_state <= 2; end
        2: if(!tx_busy) begin tx_data <= tx_buffer[23:16]; tx_send <= 1; tx_state <= 3; end
        3: if(!tx_busy) begin tx_data <= tx_buffer[15:8];  tx_send <= 1; tx_state <= 4; end
        4: if(!tx_busy) begin tx_data <= tx_buffer[7:0];   tx_send <= 1; tx_state <= 0; end

        endcase
    end
end

endmodule