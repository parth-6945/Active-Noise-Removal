`timescale 1ns/1ps
module lms_q31_fsm #
(
    parameter TAPS = 16,
    parameter Q = 31,
    parameter MU_SHIFT = 10
)
(
    input  wire        clk,
    input  wire        rst,
    input  wire        valid_in,
    input  wire [31:0] x_in,
    input  wire [31:0] d_in,

    output reg         valid_out,
    output reg  [31:0] e_out
);

// FSM states
localparam IDLE        = 0;
localparam SHIFT       = 1;
localparam FIR_MUL     = 2;
localparam FIR_ACC     = 3;
localparam ERROR       = 4;
localparam UPDATE_MUL  = 5;
localparam UPDATE_ACC  = 6;
localparam OUT         = 7;

reg [2:0] state;

// storage
reg signed [31:0] x [0:TAPS-1];
reg signed [31:0] w [0:TAPS-1];
reg signed [31:0] x_next [0:TAPS-1];

reg signed [31:0] x_in_r, d_in_r;

reg signed [63:0] acc;
reg signed [31:0] y;
reg signed [31:0] e;

// 👉 NEW: temp for correct same-cycle computation
reg signed [31:0] y_temp;

// ---- add these registers at top (outside always) ----
reg signed [63:0] mult_res0, mult_res1;

reg [4:0] k;

integer i;

// DSP-friendly register
(* use_dsp = "yes" *) reg signed [63:0] mult_res;

// saturation
function automatic signed [31:0] sat_q31(input signed [63:0] v);
begin
    if (v > 64'sh0000_0000_7FFF_FFFF)
        sat_q31 = 32'sh7FFF_FFFF;
    else if (v < 64'shFFFF_FFFF_8000_0000)
        sat_q31 = 32'sh8000_0000;
    else
        sat_q31 = v[31:0];
end
endfunction

always @(posedge clk) begin

    if (rst) begin
        state <= IDLE;
        valid_out <= 0;
        e_out <= 0;
        k <= 0;

        acc <= 0;
        y   <= 0;
        e   <= 0;

        for (i = 0; i < TAPS; i = i + 1) begin
            x[i] <= 0;
            w[i] <= 0;
        end
    end
    else begin

        valid_out <= 0;

        case(state)

        // ---------------- IDLE ----------------
        IDLE:
        begin
            if (valid_in) begin
                x_in_r <= x_in;
                d_in_r <= d_in;
                state <= SHIFT;
            end
        end

        // ---------------- SHIFT ----------------
        SHIFT:
        begin
            x_next[0] = x_in_r;
            for (i = 1; i < TAPS; i = i + 1)
                x_next[i] = x[i-1];

            acc <= 0;
            k <= 0;
            state <= FIR_MUL;
        end

        // ---------------- FIR MUL (2 taps) ----------------
        FIR_MUL:
        begin
            mult_res0 <= w[k]     * x_next[k];
            mult_res1 <= w[k + 1] * x_next[k + 1];
            state <= FIR_ACC;
        end
        
        // ---------------- FIR ACC (2 taps) ----------------
        FIR_ACC:
        begin
            acc <= acc + mult_res0 + mult_res1;
        
            if (k >= TAPS-2)
                state <= ERROR;
            else begin
                k <= k + 2;
                state <= FIR_MUL;
            end
        end

        // ---------------- ERROR (FIXED) ----------------
        ERROR:
        begin
            // compute BOTH in same cycle (matches HLS)
            y_temp = sat_q31(acc >>> Q);
            y      <= y_temp;
            e      <= sat_q31($signed(d_in_r) - $signed(y_temp));

            k <= 0;
            state <= UPDATE_MUL;
        end

        // ---------------- UPDATE MUL ----------------
        UPDATE_MUL:
        begin
            mult_res <= e * x_next[k];
            state <= UPDATE_ACC;
        end

        // ---------------- UPDATE ACC ----------------
        UPDATE_ACC:
        begin
            w[k] <= sat_q31(
                        w[k] + ((mult_res >>> Q) >>> MU_SHIFT)
                    );

            if (k == TAPS-1)
                state <= OUT;
            else begin
                k <= k + 1;
                state <= UPDATE_MUL;
            end
        end

        // ---------------- OUTPUT ----------------
        OUT:
        begin
            for (i = 0; i < TAPS; i = i + 1)
                x[i] <= x_next[i];

            e_out <= e;
            valid_out <= 1;

            state <= IDLE;
        end

        endcase
    end
end

endmodule