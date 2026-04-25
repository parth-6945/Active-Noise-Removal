module uart_lms_top
(
    input clk,
    input rx,
    output tx
);

// ============================================================
// INTERNAL POWER-ON RESET
// ============================================================
reg [3:0] rst_cnt = 0;
reg rst = 1;

always @(posedge clk)
begin
    if (rst_cnt < 4'd10) begin
        rst_cnt <= rst_cnt + 1;
        rst <= 1;
    end else begin
        rst <= 0;
    end
end

// ============================================================
// UART
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
// FRAME RECEIVER
// ============================================================
reg receiving = 0;
reg [2:0] byte_count = 0;

reg [31:0] speech = 0;
reg [31:0] noise  = 0;

reg new_sample = 0;
reg new_sample_d = 0;
reg lms_busy = 0;

always @(posedge clk)
begin
    if (rst)
    begin
        receiving   <= 0;
        byte_count  <= 0;
        speech      <= 0;
        noise       <= 0;
        new_sample  <= 0;
    end
    else
    begin
        new_sample <= 0;

        if (rx_valid)
        begin
            if (!lms_busy)
            begin
                if (!receiving)
                begin
                    if (rx_data == 8'hAA)
                    begin
                        receiving  <= 1;
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

                    4: noise[31:24] <= rx_data;
                    5: noise[23:16] <= rx_data;
                    6: noise[15:8]  <= rx_data;

                    7:
                    begin
                        noise[7:0] <= rx_data;
                        new_sample <= 1;
                        receiving  <= 0;
                    end

                    endcase

                    byte_count <= byte_count + 1;
                end
            end
        end
    end
end

// edge detect
always @(posedge clk)
begin
    if (rst)
        new_sample_d <= 0;
    else
        new_sample_d <= new_sample;
end

wire new_sample_edge = new_sample & ~new_sample_d;

// ============================================================
// LMS CONTROL
// ============================================================
reg [31:0] x_reg = 0;
reg [31:0] d_reg = 0;

reg valid_in_lms = 0;

wire [31:0] lms_out;
wire lms_valid_out;

always @(posedge clk)
begin
    if (rst)
    begin
        valid_in_lms <= 0;
        lms_busy     <= 0;
        x_reg        <= 0;
        d_reg        <= 0;
    end
    else
    begin
        valid_in_lms <= 0;

        if (new_sample_edge && !lms_busy)
        begin
            x_reg <= noise;    // noise reference → filter input
            d_reg <= speech;   // noisy signal   → desired

            valid_in_lms <= 1;
            lms_busy <= 1;
        end

        if (lms_valid_out)
        begin
            lms_busy <= 0;
            $display("[TX DBG] LMS DONE @%0t -> e = %08x", $time, lms_out);
        end
    end
end

// ============================================================
// LMS INSTANCE
// ============================================================
lms_q31_fsm lms_inst (
    .clk(clk),
    .rst(rst),
    .valid_in(valid_in_lms),
    .x_in(x_reg),
    .d_in(d_reg),
    .valid_out(lms_valid_out),
    .e_out(lms_out)
);

// ============================================================
// TX STATE MACHINE (DECLARE FIRST to avoid warning)
// ============================================================
reg [2:0] tx_state = 0;
reg [31:0] tx_buffer = 0;

// ============================================================
// 🔥 FIXED: LMS OUTPUT LATCH (VALID + DATA)
// ============================================================
reg lms_valid_hold = 0;
reg [31:0] lms_out_hold = 0;

always @(posedge clk)
begin
    if (rst)
    begin
        lms_valid_hold <= 0;
        lms_out_hold   <= 0;
    end
    else
    begin
        if (lms_valid_out)
        begin
            lms_valid_hold <= 1;
            lms_out_hold   <= lms_out;   // ✅ latch data safely
            $display("[TX DBG] LATCHED DATA @%0t -> %08x", $time, lms_out);
        end
        else if (tx_state == 1 && !tx_busy)
        begin
            lms_valid_hold <= 0;         // clear when TX starts
        end
    end
end

// ============================================================
// TX FSM
// ============================================================
always @(posedge clk)
begin
    if (rst)
    begin
        tx_state  <= 0;
        tx_send   <= 0;
        tx_data   <= 0;
        tx_buffer <= 0;
    end
    else
    begin
        tx_send <= 0;

        case(tx_state)

        0:
        begin
            if(lms_valid_hold)
            begin
                tx_buffer <= lms_out_hold;  // ✅ use latched data
                tx_state <= 1;
                $display("[TX DBG] TX START @%0t -> %08x", $time, lms_out_hold);
            end
        end

        1: if(!tx_busy && !tx_send) begin tx_data <= tx_buffer[31:24]; tx_send <= 1; tx_state <= 2; $display("[TX DBG] BYTE0 = %02x", tx_buffer[31:24]); end
        2: if(!tx_busy && !tx_send) begin tx_data <= tx_buffer[23:16]; tx_send <= 1; tx_state <= 3; $display("[TX DBG] BYTE1 = %02x", tx_buffer[23:16]); end
        3: if(!tx_busy && !tx_send) begin tx_data <= tx_buffer[15:8];  tx_send <= 1; tx_state <= 4; $display("[TX DBG] BYTE2 = %02x", tx_buffer[15: 8]); end
        4: if(!tx_busy && !tx_send) begin tx_data <= tx_buffer[7:0];   tx_send <= 1; tx_state <= 0; $display("[TX DBG] BYTE3 = %02x", tx_buffer[ 7: 0]); end

        endcase
    end
end

endmodule