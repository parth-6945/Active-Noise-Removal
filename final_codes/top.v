// Map tx to U11
module top(

    input clk,
    output tx

);

reg send = 0;
reg [7:0] data;
wire busy;

reg [1:0] state = 0;
reg [25:0] delay_counter = 0;

uart_tx uart0 (

    .clk(clk),
    .send(send),
    .data(data),
    .tx(tx),
    .busy(busy)

);

always @(posedge clk)
begin

    send <= 0;

    if(delay_counter < 50_000_000)
    begin
        delay_counter <= delay_counter + 1;
    end
    else
    begin

        delay_counter <= 0;

        if(!busy)
        begin

            send <= 1;

            case(state)

                2'd0: data <= 8'h11;
                2'd1: data <= 8'h22;
                2'd2: data <= 8'h33;
                2'd3: data <= 8'h44;

            endcase

            state <= state + 1;

        end

    end

end

endmodule