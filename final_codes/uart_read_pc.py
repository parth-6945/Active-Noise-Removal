import serial
import time

PORT = "/dev/ttyUSB1"
BAUD = 115200
OUTPUT_FILE = "uart_output.bin"

ser = serial.Serial(PORT, BAUD, timeout=1)

print("Reading from", PORT)

with open(OUTPUT_FILE, "wb") as f:

    start = time.time()
    total = 0

    try:
        while True:
            byte = ser.read(1)

            if byte:
                value = byte[0]
                print(f"HEX: {value:02X}  DEC: {value}")

                f.write(byte)
                total += 1


    except KeyboardInterrupt:
        print("\nStopped")

ser.close()
print("Saved to", OUTPUT_FILE)