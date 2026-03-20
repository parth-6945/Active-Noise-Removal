module uart_tx #
(
    parameter CLK_FREQ = 100_000_000,
    parameter BAUD_RATE = 115200
)
(
    input clk,
    input send,
    input [7:0] data,
    output reg tx = 1,
    output reg busy = 0
);

localparam CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

reg [31:0] clk_count = 0;
reg [3:0] bit_index = 0;
reg [9:0] shift_reg = 10'b1111111111;

always @(posedge clk)
begin

    if(send && !busy)
    begin
        busy <= 1;
        shift_reg <= {1'b1, data, 1'b0}; // stop, data, start
        bit_index <= 0;
        clk_count <= 0;
    end

    if(busy)
    begin
        if(clk_count < CLKS_PER_BIT-1)
        begin
            clk_count <= clk_count + 1;
        end
        else
        begin
            clk_count <= 0;

            tx <= shift_reg[0];
            shift_reg <= {1'b1, shift_reg[9:1]};

            bit_index <= bit_index + 1;

            if(bit_index == 9)
                busy <= 0;
        end
    end

end

endmodule