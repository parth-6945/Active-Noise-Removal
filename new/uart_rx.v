module uart_rx #
(
    parameter CLK_FREQ  = 20_000_000,
    parameter BAUD_RATE = 921600
)
(
    input  wire clk,
    input  wire rx,
    output reg  [7:0] data = 0,
    output reg  valid = 0
);

// ============================================================
// BIT TIMING
// ============================================================
localparam integer CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

// ============================================================
// Synchronizer (important for async RX)
// ============================================================
reg rx_sync_0 = 1;
reg rx_sync_1 = 1;

always @(posedge clk) begin
    rx_sync_0 <= rx;
    rx_sync_1 <= rx_sync_0;
end

// ============================================================
// Edge detect (start bit detection)
// ============================================================
reg rx_prev = 1;
always @(posedge clk)
    rx_prev <= rx_sync_1;

wire start_edge = (rx_prev == 1) && (rx_sync_1 == 0);

// ============================================================
// FSM
// ============================================================
localparam IDLE=0, START=1, DATA=2, STOP=3, DONE=4;
reg [2:0] state = IDLE;

reg [15:0] clk_count = 0;
reg [2:0] bit_index = 0;
reg [7:0] rx_shift = 0;

always @(posedge clk)
begin
    valid <= 0;

    case (state)

    // --------------------------------------------------------
    IDLE:
    begin
        clk_count <= 0;
        bit_index <= 0;

        if (start_edge)
            state <= START;
    end

    // --------------------------------------------------------
    // Wait HALF bit → align to center of start bit
    START:
    begin
        if (clk_count < (CLKS_PER_BIT >> 1))   // divide by 2
            clk_count <= clk_count + 1;
        else begin
            clk_count <= 0;

            // Confirm valid start bit
            if (rx_sync_1 == 0)
                state <= DATA;
            else
                state <= IDLE; // false trigger
        end
    end

    // --------------------------------------------------------
    // Sample each bit at its center
    DATA:
    begin
        if (clk_count < CLKS_PER_BIT-1)
            clk_count <= clk_count + 1;
        else begin
            clk_count <= 0;

            rx_shift[bit_index] <= rx_sync_1;

            if (bit_index == 7)
                state <= STOP;
            else
                bit_index <= bit_index + 1;
        end
    end

    // --------------------------------------------------------
    STOP:
    begin
        if (clk_count < CLKS_PER_BIT-1)
            clk_count <= clk_count + 1;
        else begin
            clk_count <= 0;
            state <= DONE;
        end
    end

    // --------------------------------------------------------
    DONE:
    begin
        data  <= rx_shift;
        valid <= 1;
        state <= IDLE;
    end

    endcase
end

endmodule