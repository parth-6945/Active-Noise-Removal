// lms_q31.c
// Q1.31 LMS in C — reads noise.mem & noisy.mem, writes filtered_q31.mem
// Compile: gcc -O2 lms_q31.c -o lms_q31
// Usage: ./lms_q31 <noise.mem> <noisy.mem> <out_filtered.mem> [taps] [mu_shift]
// Example ./lms_q31 q31_out/noise.mem q31_out/noisy.mem q31_out/filtered_from_c.mem 16 10

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

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

// ---------------- read mem (hex) into int32 array ----------------
// skip empty lines and lines starting with '@' or '#'
int32_t *read_mem_q31(const char *path, size_t *out_len) {
    FILE *f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "Error: cannot open %s\n", path);
        return NULL;
    }

    size_t cap = 16384;
    size_t n = 0;
    int32_t *buf = malloc(cap * sizeof(int32_t));
    if (!buf) { fclose(f); return NULL; }

    char line[256];
    while (fgets(line, sizeof(line), f)) {
        // trim leading spaces
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == '\0' || *p == '\n' || *p == '\r') continue;
        if (*p == '@' || *p == '#' || *p == '/' ) continue;

        // parse hex (allow leading 0x or not)
        unsigned long long val = 0;
        if (sscanf(p, "%llx", &val) != 1) continue;

        uint32_t u32 = (uint32_t)val;
        // reinterpret bit pattern as signed
        int32_t s32 = (int32_t)u32;

        if (n >= cap) {
            cap *= 2;
            int32_t *tmp = realloc(buf, cap * sizeof(int32_t));
            if (!tmp) { free(buf); fclose(f); return NULL; }
            buf = tmp;
        }
        buf[n++] = s32;
    }
    fclose(f);
    *out_len = n;
    return buf;
}

// ---------------- write mem (hex) from int32 array ----------------
int write_mem_q31(const char *path, const int32_t *data, size_t n) {
    FILE *f = fopen(path, "w");
    if (!f) return -1;
    for (size_t i = 0; i < n; ++i) {
        fprintf(f, "%08x\n", (uint32_t)data[i]);
    }
    fclose(f);
    return 0;
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

    const size_t progress_interval = 10000;
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

        if ((idx + 1) % progress_interval == 0) {
            double elapsed = (double)(clock() - t0) / CLOCKS_PER_SEC;
            double pct = 100.0 * (double)(idx + 1) / (double)n;
            printf("   Progress: %.1f%% (%zu/%zu) | Elapsed: %.1fs\n", pct, idx+1, n, elapsed);
            fflush(stdout);
        }
    }

    double total = (double)(clock() - t0) / CLOCKS_PER_SEC;
    printf("[✓] LMS complete in %.2fs\n", total);

    free(w);
    free(x);
}

// ---------------- main ----------------
int main(int argc, char **argv) {
    if (argc < 4) {
        printf("Usage: %s <noise.mem> <noisy.mem> <out_filtered.mem> [taps] [mu_shift]\n", argv[0]);
        return 1;
    }

    const char *noise_path = argv[1];
    const char *noisy_path = argv[2];
    const char *out_path = argv[3];
    int taps = (argc >= 5) ? atoi(argv[4]) : 16;
    int mu_shift = (argc >= 6) ? atoi(argv[5]) : 10;

    size_t len_x=0, len_d=0;
    int32_t *x_q31 = read_mem_q31(noise_path, &len_x);
    if (!x_q31) { fprintf(stderr, "failed to read %s\n", noise_path); return 1; }
    int32_t *d_q31 = read_mem_q31(noisy_path, &len_d);
    if (!d_q31) { free(x_q31); fprintf(stderr, "failed to read %s\n", noisy_path); return 1; }

    size_t n = (len_x < len_d) ? len_x : len_d;
    int32_t *e_q31 = malloc(n * sizeof(int32_t));
    if (!e_q31) { free(x_q31); free(d_q31); fprintf(stderr, "alloc fail\n"); return 1; }

    printf("[→] Running Q1.31 LMS on %zu samples (taps=%d mu_shift=%d)\n", n, taps, mu_shift);
    lms_q31(x_q31, d_q31, e_q31, n, taps, mu_shift);

    if (write_mem_q31(out_path, e_q31, n) != 0) {
        fprintf(stderr, "failed to write output\n");
    } else {
        printf("[✓] Wrote %s (%zu samples)\n", out_path, n);
    }

    free(x_q31);
    free(d_q31);
    free(e_q31);
    return 0;
}
