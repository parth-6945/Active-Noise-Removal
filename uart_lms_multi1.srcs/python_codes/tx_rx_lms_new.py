import serial
import struct
import time

# ==============================
# CONFIG
# ==============================
PORT = '/dev/ttyUSB1'
BAUD = 1250000

X_FILE = '/home/parth/Documents/noisy.mem'
D_FILE = '/home/parth/Documents/noise.mem'
OUT_FILE = '/home/parth/Documents/output_fpga.mem'

# ==============================
# READ MEM FILE
# ==============================
def read_mem_file(filename):
    with open(filename, 'r') as f:
        # Faster list comprehension reading
        return [int(line.strip(), 16) for line in f if line.strip() != ""]

print("Loading files...")
x_vals = read_mem_file(X_FILE)
d_vals = read_mem_file(D_FILE)

if len(x_vals) != len(d_vals):
    print("ERROR: File lengths do not match!")
    exit()

num_samples = len(x_vals)
print(f"Loaded {num_samples} samples")

# ==============================
# PREPARE ALL TX DATA
# ==============================
print("Pre-packing TX data...")
# Pre-pack everything outside the loop to eliminate Python execution overhead
# B = 1 byte unsigned, I = 4 bytes unsigned (bitwise identical to signed packing)
packer = struct.Struct('>BII') 
tx_data = bytearray()
for x, d in zip(x_vals, d_vals):
    tx_data.extend(packer.pack(0xAA, x, d))

# ==============================
# UART Pipelined Communication
# ==============================
ser = serial.Serial(PORT, BAUD, timeout=2)
ser.reset_input_buffer()
ser.reset_output_buffer()

results = []
# CHUNK_SIZE = 500 samples * 4 bytes/RX = 2000 bytes. 
# Keeping this below 4096 bytes prevents the OS RX buffer from overflowing.
CHUNK_SIZE = 500  

print("Starting transmission...")
start_time = time.time()

for i in range(0, num_samples, CHUNK_SIZE):
    chunk_samples = min(CHUNK_SIZE, num_samples - i)
    
    start_byte = i * 9
    end_byte = start_byte + (chunk_samples * 9)
    
    # 1. Send a big chunk of data at once (keeps TX buffer full)
    ser.write(tx_data[start_byte:end_byte])
    
    # 2. Read the response chunk (waits efficiently)
    expected_bytes = chunk_samples * 4
    resp = bytearray()
    
    while len(resp) < expected_bytes:
        chunk = ser.read(expected_bytes - len(resp))
        if not chunk:
            print(f"Timeout at sample index {i + len(resp)//4}")
            break
        resp.extend(chunk)
        
    # 3. Unpack the response block
    # Unpacking as unsigned gets the exact same bytes directly
    for j in range(0, len(resp), 4):
        y_hex = struct.unpack('>I', resp[j:j+4])[0]
        results.append(y_hex)
        
    if i % 8000 < CHUNK_SIZE:
        print(f"Processed {i} samples...")

end_time = time.time()
ser.close()

elapsed = end_time - start_time
print(f"\nProcessed {num_samples} samples in {elapsed:.2f} seconds.")
print(f"Effective frequency: {num_samples/elapsed:.2f} Hz")

# ==============================
# SAVE OUTPUT FILE
# ==============================
print("Saving output...")
with open(OUT_FILE, 'w') as f:
    for val in results:
        f.write(f"{val:08X}\n")

print(f"Saved FPGA output to: {OUT_FILE}")

