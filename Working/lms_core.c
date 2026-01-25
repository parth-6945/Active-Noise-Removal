#include<stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <math.h>

#define Q           31
#define MAX_Q31     0x7FFFFFFFLL
#define MIN_Q31    -0x80000000LL

// saturate 64-bit value to int32 range
static inline int32_t sat32_from_i128(__int128 v) {
    if (v > (__int128)MAX_Q31) return (int32_t)MAX_Q31;
    if (v < (__int128)MIN_Q31) return (int32_t)MIN_Q31;
    return (int32_t)( (int64_t)v );
}
static inline int32_t sat32_from_i64(int64_t v) {
    if (v > (int64_t)MAX_Q31) return (int32_t)MAX_Q31;
    if (v < (int64_t)MIN_Q31) return (int32_t)MIN_Q31;
    return (int32_t)v;
}

// ---------------- Q1.31 LMS ----------------
// x_q31: reference noise (int32, Q1.31)
// d_q31: desired noisy signal (int32, Q1.31)
// e_q31: output buffer (int32, Q1.31) should be preallocated with length n
void lms_q31(const int32_t *x_q31, const int32_t *d_q31, int32_t *e_q31,
             size_t n, int taps, int mu_shift)
{
    if (taps <= 0) taps = 1;
    // weights stored in 64-bit to accumulate updates; we saturate to 32-bit range after updates
    int64_t *w = calloc(taps, sizeof(int64_t));
    int64_t *x = calloc(taps, sizeof(int64_t));
    if (!w || !x) { fprintf(stderr, "alloc fail\n"); exit(1); }

    clock_t t0 = clock();

    for (size_t idx = 0; idx < n; ++idx) {
        // shift delay-line
        for (int i = taps - 1; i > 0; --i) x[i] = x[i-1];
        x[0] = (int64_t)x_q31[idx];

        // MAC using 128-bit accumulator (to avoid overflow)
        __int128 acc = 0;
        for (int i = 0; i < taps; ++i) {
            acc += (__int128)w[i] * (__int128)x[i]; // w (int64) * x (int64) => int128
        }
        // shift down from Q62 to Q31
        __int128 y_q31_128 = acc >> Q;
        int32_t y_q31 = sat32_from_i128(y_q31_128);

        // error e = d - y
        int64_t e64 = (int64_t)d_q31[idx] - (int64_t)y_q31;
        int32_t e32 = sat32_from_i64(e64);
        e_q31[idx] = e32;

        // ---- DEBUG PRINT ----
        printf("idx=%zu  y=%d  e=%d  |  w:", idx, y_q31, e32);
        for (int k = 0; k < taps; k++) {
            printf(" %lld", (long long)w[k]);
        }
        printf("\n");
        // ----------------------

        // update weights: delta = ((e * x[i]) >> Q) >> mu_shift
        for (int i = 0; i < taps; ++i) {
            __int128 prod = (__int128)e64 * (__int128)x[i]; // Q62
            __int128 prod_q31 = prod >> Q;                 // Q31
            __int128 delta = prod_q31 >> mu_shift;         // scaled
            __int128 wnew = (__int128)w[i] + delta;
            // saturate to 32-bit signed range (same as python clip to int32)
            if (wnew > (__int128)MAX_Q31) wnew = (__int128)MAX_Q31;
            if (wnew < (__int128)MIN_Q31) wnew = (__int128)MIN_Q31;
            w[i] = (int64_t)wnew;
        }
    }

    free(w);
    free(x);
}

int main()
{
    const size_t n = 10;
    const int taps = 8;
    const int mu_shift = 8;

    int32_t x_q31[n];
    int32_t d_q31[n];
    int32_t e_q31[n];

    for (size_t i = 0; i < n; i++) {
        int32_t x_val = (i + 1) * 10;   // 10,20,30...
        int32_t d_val = (i + 1);        // 1,2,3...

        x_q31[i] = x_val * (1LL << 28);   // convert to Q31
        d_q31[i] = d_val * (1LL << 28);   // convert to Q31
    }

    lms_q31(x_q31, d_q31, e_q31, n, taps, mu_shift);

    printf("\nError values (e[n]):\n");
    for (size_t i = 0; i < n; i++) {
        printf("e[%zu] = %d\n", i, e_q31[i]);
    }

    return 0;
}
