module uart_tx #
(
    parameter CLK_FREQ  = 20_000_000,
    parameter BAUD_RATE = 921600
)
(
    input clk,
    input send,
    input [7:0] data,
    output reg tx = 1,
    output reg busy = 0
);

// ============================================================
// BIT TIMING
// ============================================================
localparam integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

// ============================================================
// REGISTERS
// ============================================================
reg [15:0] clk_count = 0;
reg [3:0]  bit_index = 0;
reg [9:0]  shift_reg = 10'b1111111111;

// ============================================================
// UART TX LOGIC
// ============================================================
always @(posedge clk)
begin
    // --------------------------------------------------------
    // Start transmission
    if (send && !busy)
    begin
        busy      <= 1;
        shift_reg <= {1'b1, data, 1'b0}; // stop, data[7:0], start
        bit_index <= 0;
        clk_count <= 0;
        tx        <= 0; // immediately drive start bit
    end

    // --------------------------------------------------------
    // Transmitting bits
    else if (busy)
    begin
        if (clk_count < CLKS_PER_BIT-1)
            clk_count <= clk_count + 1;
        else
        begin
            clk_count <= 0;

            tx <= shift_reg[0];                 // output LSB
            shift_reg <= {1'b1, shift_reg[9:1]};

            bit_index <= bit_index + 1;

            if (bit_index == 9)
            begin
                busy <= 0;
                tx   <= 1; // ensure idle high after done
            end
        end
    end
end

endmodule