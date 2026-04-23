`timescale 1ns/1ps
module lms_q31_hls (
    input  wire        clk,
    input  wire        rst,      // active high reset
    input  wire        valid_in,
    input  wire [31:0] x_in,
    input  wire [31:0] d_in,

    output reg         valid_out,
    output reg  [31:0] e_out
);

localparam TAPS = 16;
localparam Q    = 31;
localparam MU_SHIFT = 10;

// -------------------------------------------------
// State (matches HLS static arrays)
// -------------------------------------------------
reg signed [31:0] x [0:TAPS-1];
reg signed [31:0] w [0:TAPS-1];

// Temporary "next" version of x to match HLS ordering
reg signed [31:0] x_next [0:TAPS-1];

// -------------------------------------------------
// Temporaries
// -------------------------------------------------
reg signed [63:0] acc;
reg signed [31:0] y;
reg signed [63:0] e;
reg signed [63:0] prod;
reg signed [63:0] grad;
reg signed [63:0] delta;

// -------------------------------------------------
// Q31 saturation (matches your C exactly)
// -------------------------------------------------
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

// -------------------------------------------------
// Main sequential logic
// -------------------------------------------------
integer i;
always @(posedge clk) begin

    valid_out <= 1'b0;   // default

    // ---------- RESET (matches HLS) ----------
    if (rst) begin
        for (i = 0; i < TAPS; i = i + 1) begin
            x[i] <= 0;
            w[i] <= 0;
        end
        e_out <= 0;
    end

    // ---------- NORMAL OPERATION ----------
    else if (valid_in) begin

        // 1) BUILD SHIFTED x_next (THIS IS THE KEY FIX)
        x_next[0] = $signed(x_in);
        for (i = TAPS-1; i > 0; i = i - 1)
            x_next[i] = x[i-1];   // use old x for shifting

        // 2) FIR USING x_next (matches HLS)
        acc = 0;
        for (i = 0; i < TAPS; i = i + 1)
            acc = acc + ($signed(w[i]) * $signed(x_next[i]));

        y = sat_q31(acc >>> Q);

        // 3) ERROR
        e = sat_q31($signed(d_in) - $signed(y));

        // 4) LMS UPDATE USING x_next (matches HLS)
        for (i = 0; i < TAPS; i = i + 1) begin
            prod  = $signed(e) * $signed(x_next[i]); // Q62
            grad  = prod >>> Q;                     // Q31
            delta = grad >>> MU_SHIFT;              // apply mu
            w[i]  <= sat_q31($signed(w[i]) + delta);
        end

        // 5) COMMIT SHIFTED ARRAY
        for (i = 0; i < TAPS; i = i + 1)
            x[i] <= x_next[i];

        // 6) OUTPUT
        e_out     <= e;
        valid_out <= 1'b1;
    end
end

endmodule
