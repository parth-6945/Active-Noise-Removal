`timescale 1ns/1ps
module tb_uart_lms_top;

    // =========================================================
    // CLOCK
    // =========================================================
    reg clk = 0;
    always #5 clk = ~clk;   // 100 MHz

    // =========================================================
    // DEBUG CYCLE COUNTER
    // =========================================================
    integer cycle = 0;
    always @(posedge clk) begin
        cycle <= cycle + 1;
        if (cycle % 1000000 == 0)
            $display(">> Cycle = %0d", cycle);
    end

    // =========================================================
    // UART WIRES
    // =========================================================
    wire tx;
    reg  rx = 1;

    // =========================================================
    // DUT
    // =========================================================
    uart_lms_top dut (
        .clk(clk),
        .rx(rx),
        .tx(tx)
    );

    // =========================================================
    // UART PARAMETERS
    // =========================================================
    localparam BAUD     = 625000;
    localparam BIT_TIME = 1_000_000_000 / BAUD;  // ns

    // =========================================================
    // MEMORY
    // =========================================================
    localparam N = 1000;

    reg [31:0] x_mem [0:N-1];
    reg [31:0] d_mem [0:N-1];

    initial begin
        $readmemh("/home/parth/Documents/Vitis_HLS/noisy.mem", x_mem);
        $readmemh("/home/parth/Documents/Vitis_HLS/noise.mem", d_mem);
    end

    // =========================================================
    // UART SEND BYTE
    // =========================================================
    task uart_send_byte(input [7:0] data);
        integer i;
        begin
            $display("[%0d] TX BYTE: %02x", cycle, data);

            // START BIT
            rx = 0;
            #(BIT_TIME);

            // DATA BITS (LSB first)
            for (i = 0; i < 8; i = i + 1) begin
                rx = data[i];
                #(BIT_TIME);
            end

            // STOP BIT
            rx = 1;
            #(BIT_TIME);
        end
    endtask

    // =========================================================
    // SEND FULL PACKET (AA + 8 BYTES)
    // =========================================================
    task send_packet(input [31:0] x, input [31:0] d);
        begin
            uart_send_byte(8'hAA);

            uart_send_byte(x[31:24]);
            uart_send_byte(x[23:16]);
            uart_send_byte(x[15:8]);
            uart_send_byte(x[7:0]);

            uart_send_byte(d[31:24]);
            uart_send_byte(d[23:16]);
            uart_send_byte(d[15:8]);
            uart_send_byte(d[7:0]);
        end
    endtask

    // =========================================================
    // UART RX INSTANCE (reuse proven hardware receiver)
    // =========================================================
    wire [7:0] tb_rx_data;
    wire       tb_rx_valid;

    uart_rx tb_uart_rx_inst (
        .clk(clk),
        .rx(tx),            // DUT's tx -> our rx
        .data(tb_rx_data),
        .valid(tb_rx_valid)
    );

    // =========================================================
    // BYTE CAPTURE FIFO (collects bytes as they arrive)
    // =========================================================
    reg [7:0]  rx_fifo [0:15];
    reg [4:0]  rx_wr_ptr = 0;
    reg [4:0]  rx_rd_ptr = 0;

    wire [4:0] rx_count = rx_wr_ptr - rx_rd_ptr;

    always @(posedge clk) begin
        if (tb_rx_valid) begin
            rx_fifo[rx_wr_ptr[3:0]] <= tb_rx_data;
            rx_wr_ptr <= rx_wr_ptr + 1;
            $display("[%0d] RX BYTE: %02x", cycle, tb_rx_data);
        end
    end

    // =========================================================
    // TASK: wait until N bytes are available in FIFO
    // =========================================================
    task wait_rx_bytes(input integer count);
        begin
            while (rx_count < count)
                @(posedge clk);
        end
    endtask

    // =========================================================
    // OUTPUT STORAGE
    // =========================================================
    reg [31:0] result_mem [0:N-1];

    integer i;

    // =========================================================
    // MAIN TEST
    // =========================================================
    initial begin

        rx = 1;

        // allow DUT reset to complete
        #(100000);

        for (i = 0; i < N; i = i + 1) begin

            $display("\n=============================");
            $display(" SAMPLE %0d START @ cycle %0d", i, cycle);
            $display("=============================");

            // -------------------------------------------------
            // SEND INPUT
            // -------------------------------------------------
            send_packet(x_mem[i], d_mem[i]);

            // -------------------------------------------------
            // RECEIVE 4 BYTES (using hardware uart_rx + FIFO)
            // -------------------------------------------------
            wait_rx_bytes(4);

            result_mem[i][31:24] = rx_fifo[rx_rd_ptr[3:0]]; rx_rd_ptr = rx_rd_ptr + 1;
            result_mem[i][23:16] = rx_fifo[rx_rd_ptr[3:0]]; rx_rd_ptr = rx_rd_ptr + 1;
            result_mem[i][15:8]  = rx_fifo[rx_rd_ptr[3:0]]; rx_rd_ptr = rx_rd_ptr + 1;
            result_mem[i][7:0]   = rx_fifo[rx_rd_ptr[3:0]]; rx_rd_ptr = rx_rd_ptr + 1;

            $display("RESULT[%0d] = %08x", i, result_mem[i]);

            // spacing between samples
            repeat (5000) @(posedge clk);
        end

        // SAVE OUTPUT
        $writememh(
            "/home/parth/Documents/Vitis_HLS/rtl_uart_out.mem",
            result_mem
        );

        $display("\nSaved UART output file.");
        $finish;
    end

    // =========================================================
    // GLOBAL TIMEOUT
    // =========================================================
    initial begin
        #300_000_000;
        $display("GLOBAL TIMEOUT at cycle %0d", cycle);
        $finish;
    end

endmodule