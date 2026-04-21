module uart_lms_top
(
    input clk,
    input rx,
    output tx
);

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
// FRAME RECEIVER (0xAA)
// ============================================================
reg receiving = 0;
reg [2:0] byte_count = 0;

reg [31:0] speech = 0;
reg [31:0] noise  = 0;

reg new_sample = 0;

always @(posedge clk)
begin
    new_sample <= 0;

    if (rx_valid)
    begin
        if (!receiving)
        begin
            if (rx_data == 8'hAA)
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

            4: noise[31:24] <= rx_data;
            5: noise[23:16] <= rx_data;
            6: noise[15:8]  <= rx_data;
            7: begin
                noise[7:0] <= rx_data;
                new_sample <= 1;     // ✅ one complete sample received
                receiving <= 0;
            end

            endcase

            byte_count <= byte_count + 1;
        end
    end
end

// ============================================================
// SAMPLE LATCH + VALID PULSE GENERATION (FIXED)
// ============================================================
reg [31:0] x_reg = 0;
reg [31:0] d_reg = 0;
reg valid_in_reg = 0;

always @(posedge clk)
begin
    valid_in_reg <= 0;   // default: no valid sample

    if(new_sample)
    begin
        x_reg <= speech;
        d_reg <= noise;
        valid_in_reg <= 1;   // ✅ exactly 1 clock pulse
    end
end

// ============================================================
// LMS
// ============================================================
wire [31:0] lms_out;
wire lms_valid_out;

// Optional reset (recommended for stable startup)
reg rst_lms = 1;
reg [7:0] rst_cnt = 0;

always @(posedge clk)
begin
    if (rst_cnt < 100)
    begin
        rst_cnt <= rst_cnt + 1;
        rst_lms <= 1;
    end
    else
        rst_lms <= 0;
end

lms_q31_hls lms_inst (
    .clk(clk),
    .rst(rst_lms),              // ✅ proper reset
    .valid_in(valid_in_reg),    // ✅ FIXED: one update per sample
    .x_in(x_reg),
    .d_in(d_reg),
    .valid_out(lms_valid_out),
    .e_out(lms_out)
);

// ============================================================
// TX STATE MACHINE
// ============================================================
reg [2:0] tx_state = 0;
reg [31:0] tx_buffer = 0;

always @(posedge clk)
begin
    tx_send <= 0;

    case(tx_state)

    0:
    begin
        if(lms_valid_out)
        begin
            tx_buffer <= lms_out;
            tx_state <= 1;
        end
    end

    1: if(!tx_busy) begin tx_data <= tx_buffer[31:24]; tx_send <= 1; tx_state <= 2; end
    2: if(!tx_busy) begin tx_data <= tx_buffer[23:16]; tx_send <= 1; tx_state <= 3; end
    3: if(!tx_busy) begin tx_data <= tx_buffer[15:8];  tx_send <= 1; tx_state <= 4; end
    4: if(!tx_busy) begin tx_data <= tx_buffer[7:0];   tx_send <= 1; tx_state <= 0; end

    endcase
end

endmodule