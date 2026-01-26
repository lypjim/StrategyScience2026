#!/usr/bin/env python3
"""
Clean Metadata Script
1. Reads meta.xlsx
2. Filters out rows where 'Paper_Type' (last column) is missing (meaning no file uploaded)
3. Filters out rows where Name is "Ollie Peterson" or "Tony T." (Test entries)
4. Saves to meta_cleaned.csv (CSV is easier for downstream)
"""

import pandas as pd
import os

INPUT_FILE = "meta.xlsx"
OUTPUT_FILE = "meta_cleaned.csv"


def main():
    print(f"Reading {INPUT_FILE}...")
    df = pd.read_excel(INPUT_FILE)

    # 1. Filter out header info rows (Qualtrics exports often have 2-3 header rows)
    # We identify real data by checking if 'StartDate' is a date-like string or ResponseId looks valid
    # In this case, Row 0 and 1 are usually metadata descriptions.
    # We'll drop rows where 'ResponseId' is missing/NaN first.
    # Also explicitly drop the header description row (where ResponseId == "Response ID")
    df = df[df["ResponseId"].notna()]
    df = df[df["ResponseId"] != "Response ID"]

    # 2. Filter out entries with no paper uploaded
    # The last column 'Paper_Type' or 'Paper_Name' should be present
    print(f"Total rows with ResponseId: {len(df)}")

    df = df[df["Paper_Name"].notna()]
    print(f"Rows with uploaded paper: {len(df)}")

    # 3. Filter out test entries
    # Name "Ollie Peterson" or "Tony T."
    test_names = ["Ollie Peterson", "Tony T."]
    df = df[~df["Name"].isin(test_names)]
    print(f"Rows after removing test users: {len(df)}")

    # Also explicitly remove "Test file.docx" if it exists
    df = df[df["Paper_Name"] != "Test file.docx"]

    # Save
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved cleaned metadata to {OUTPUT_FILE}")

    # Show sample IDs for verification
    print("\nSample Response IDs:")
    print(df["ResponseId"].head().tolist())


if __name__ == "__main__":
    main()
