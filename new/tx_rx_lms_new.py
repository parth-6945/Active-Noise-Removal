import serial
import struct

# ==============================
# CONFIG
# ==============================
PORT = '/dev/ttyUSB1'
BAUD = 921600

X_FILE = '/home/parth/Documents/Vitis_HLS/noisy.mem'
D_FILE = '/home/parth/Documents/Vitis_HLS/noise.mem'
OUT_FILE = '/home/parth/Documents/Vitis_HLS/output_fpga.mem'

# ==============================
# READ MEM FILE
# ==============================
def read_mem_file(filename):
    values = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                values.append(int(line, 16))
    return values

# ==============================
# LOAD DATA
# ==============================
x_vals = read_mem_file(X_FILE)
d_vals = read_mem_file(D_FILE)

if len(x_vals) != len(d_vals):
    print("ERROR: File lengths do not match!")
    exit()

print(f"Loaded {len(x_vals)} samples")

# ==============================
# UART
# ==============================
ser = serial.Serial(PORT, BAUD, timeout=0.1)

ser.reset_input_buffer()
ser.reset_output_buffer()

results = []

# ==============================
# MAIN LOOP
# ==============================
for i in range(len(x_vals)):
    x = x_vals[i]
    d = d_vals[i]

    x_signed = struct.unpack('>i', struct.pack('>I', x))[0]
    d_signed = struct.unpack('>i', struct.pack('>I', d))[0]

    packet = b'\xAA' + struct.pack('>ii', x_signed, d_signed)

    print(f"TX[{i}]:", packet.hex())

    ser.write(packet)

    # Read exactly 4 bytes
    resp = ser.read(4)

    print(f"RX[{i}]:", resp.hex())

    if len(resp) != 4:
        print(f"Timeout at index {i}")
        break

    y = struct.unpack('>i', resp)[0]
    y_hex = struct.unpack('>I', struct.pack('>i', y))[0]

    results.append(y_hex)

ser.close()

# ==============================
# SAVE OUTPUT FILE
# ==============================
with open(OUT_FILE, 'w') as f:
    for val in results:
        f.write(f"{val:08X}\n")

print(f"\nSaved FPGA output to: {OUT_FILE}")