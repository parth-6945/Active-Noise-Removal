module uart_rx #
(
    parameter CLK_FREQ  = 100_000_000,
    parameter BAUD_RATE = 625000
)
(
    input  wire clk,
    input  wire rx,
    output reg  [7:0] data = 0,
    output reg  valid = 0
);

localparam CLKS_PER_SAMPLE = CLK_FREQ / (BAUD_RATE * 16);

// Synchronizer
reg rx_sync_0 = 1;
reg rx_sync_1 = 1;

always @(posedge clk) begin
    rx_sync_0 <= rx;
    rx_sync_1 <= rx_sync_0;
end

// Edge detect
reg rx_prev = 1;
always @(posedge clk)
    rx_prev <= rx_sync_1;

wire start_edge = (rx_prev == 1) && (rx_sync_1 == 0);

// FSM
localparam IDLE=0, START=1, DATA=2, STOP=3, DONE=4;
reg [2:0] state = IDLE;

reg [15:0] clk_count = 0;
reg [3:0] sample_count = 0;
reg [2:0] bit_index = 0;
reg [7:0] rx_shift = 0;

always @(posedge clk)
begin
    valid <= 0;

    case (state)

    IDLE:
    begin
        clk_count <= 0;
        sample_count <= 0;
        bit_index <= 0;

        if (start_edge)
            state <= START;
    end

    START:
    begin
        if (clk_count < CLKS_PER_SAMPLE-1)
            clk_count <= clk_count + 1;
        else begin
            clk_count <= 0;
            sample_count <= sample_count + 1;

            if (sample_count == 7) begin
                if (rx_sync_1 == 0) begin
                    sample_count <= 0;
                    state <= DATA;
                end else
                    state <= IDLE;
            end
        end
    end

    DATA:
    begin
        if (clk_count < CLKS_PER_SAMPLE-1)
            clk_count <= clk_count + 1;
        else begin
            clk_count <= 0;
            sample_count <= sample_count + 1;

            if (sample_count == 15) begin
                rx_shift[bit_index] <= rx_sync_1;
                sample_count <= 0;

                if (bit_index == 7)
                    state <= STOP;
                else
                    bit_index <= bit_index + 1;
            end
        end
    end

    STOP:
    begin
        if (clk_count < CLKS_PER_SAMPLE-1)
            clk_count <= clk_count + 1;
        else begin
            clk_count <= 0;
            sample_count <= sample_count + 1;

            if (sample_count == 15) begin
                state <= DONE;
                sample_count <= 0;
            end
        end
    end

    DONE:
    begin
        data  <= rx_shift;
        valid <= 1;
        state <= IDLE;
    end

    endcase
end

endmodule