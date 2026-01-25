import sys
import os

def compare_mem_files(file1, file2, show_differences=False):
    """Compare two .mem files line by line (bit-exact check)."""
    if not os.path.exists(file1) or not os.path.exists(file2):
        print("❌ One or both files do not exist.")
        return

    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        lines1 = [line.strip() for line in f1.readlines()]
        lines2 = [line.strip() for line in f2.readlines()]

    if len(lines1) != len(lines2):
        print(f"❌ Line count mismatch: {len(lines1)} vs {len(lines2)}")
        return

    diff_count = 0
    for i, (a, b) in enumerate(zip(lines1, lines2)):
        if a != b:
            diff_count += 1
            if show_differences and diff_count <= 10:  # limit printing
                print(f"Line {i+1}:")
                print(f"  File1: {a}")
                print(f"  File2: {b}")

    if diff_count == 0:
        print(f"✅ Files are bit-identical ({len(lines1)} lines checked)")
    else:
        print(f"❌ Files differ in {diff_count} lines")
        if not show_differences:
            print("   (Use show_differences=True to print mismatched lines)")

if __name__ == "__main__":
    print("=== MEM File Comparator ===")
    f1 = input("Enter path to first .mem file: ").strip()
    f2 = input("Enter path to second .mem file: ").strip()
    compare_mem_files(f1, f2, show_differences=True)
