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
// FRAME RECEIVER (LOCK-STEP SAFE)
// ============================================================
reg receiving = 0;
reg [2:0] byte_count = 0;

reg [31:0] speech = 0;
reg [31:0] noise  = 0;

reg new_sample = 0;
reg lms_busy = 0;

always @(posedge clk)
begin
    new_sample <= 0;

    if (rx_valid)
    begin
        // 🚫 IGNORE everything while LMS busy
        if (lms_busy)
        begin
            // do nothing (drop incoming safely)
        end
        else
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
                    new_sample <= 1;
                    receiving <= 0;
                end

                endcase

                byte_count <= byte_count + 1;
            end
        end
    end
end

// ============================================================
// LMS CONTROL (STRICT HANDSHAKE)
// ============================================================
reg [31:0] x_reg = 0;
reg [31:0] d_reg = 0;

reg valid_in_lms = 0;

wire [31:0] lms_out;
wire lms_valid_out;

always @(posedge clk)
begin
    valid_in_lms <= 0;

    // start LMS
    if (new_sample && !lms_busy)
    begin
        x_reg <= speech;
        d_reg <= noise;

        valid_in_lms <= 1;  // 1-cycle pulse
        lms_busy <= 1;
    end

    // finish LMS
    if (lms_valid_out)
    begin
        lms_busy <= 0;
    end
end

// ============================================================
// LMS INSTANCE
// ============================================================
lms_q31_fsm lms_inst (
    .clk(clk),
    .rst(1'b0),
    .valid_in(valid_in_lms),
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
