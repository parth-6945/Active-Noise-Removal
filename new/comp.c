#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

/**
 * Reads hexadecimal numbers from two files concurrently and compares them numerically.
 */
int compare_hex_files_numerically(const char* file1_path, const char* file2_path) {
    FILE *fp1, *fp2;
    unsigned long long num1, num2;
    int result = 0; // Assume files are equal initially
    int scan1, scan2;

    // Open both files in read mode
    fp1 = fopen(file1_path, "r");
    fp2 = fopen(file2_path, "r");

    if (fp1 == NULL || fp2 == NULL) {
        perror("Error opening files");
        if (fp1) fclose(fp1);
        if (fp2) fclose(fp2);
        return -1; // Error in file opening
    }

    // Read and compare numbers until the end of either file
    while (1) {
        // Use %llx format specifier to read unsigned long long in hex format
        scan1 = fscanf(fp1, "%llx", &num1);
        scan2 = fscanf(fp2, "%llx", &num2);

        // Check for end of file or read errors
        if (scan1 == EOF && scan2 == EOF) {
            break; // Both files ended, they are equal in content
        } else if (scan1 == EOF || scan2 == EOF || scan1 != 1 || scan2 != 1) {
            result = 1; // One file ended before the other or a reading error occurred
            break;
        }

        // Compare the numeric values
        if (num1 != num2) {
            printf("Difference found: 0x%llx in File 1 is not equal to 0x%llx in File 2\n", num1, num2);
            result = 1; // Files are different
            break;
        }
    }

    // Close the files
    fclose(fp1);
    fclose(fp2);

    if (result == 0) {
        printf("The hexadecimal values in both files are numerically equal.\n");
    } else {
        printf("The hexadecimal values in the files are numerically different.\n");
    }

    return result;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <file1_path> <file2_path>\n", argv[0]);
        return 1;
    }

    return compare_hex_files_numerically(argv[1], argv[2]);
}
