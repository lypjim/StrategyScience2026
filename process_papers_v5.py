#!/usr/bin/env python3
"""
Strategy Science 2026 - Paper Processor V5 (Excel Based)
(Metadata from Excel version)

Flow:
1. Reads metadata (Title, Abstract, Keywords) from 'meta.xlsx'
2. Connects to Dropbox to find matching PDFs and generate links
3. Merges data and outputs 'papers_import.csv'
"""

import os
import csv
import pandas as pd
import dropbox
from dropbox.exceptions import ApiError
import time
from typing import Dict, List, Optional, Tuple
import unicodedata

# =====================
# CONFIGURATION
# =====================
DROPBOX_ACCESS_TOKEN = "sl.u.AGSDEemh3KB4DXlC7aKYzy6rVbTje1sTKJGeZC1VYEmk2GaecHP0G63x2TuSuiUz26MujHm1P0sPe-vZr42IPDibHMtmyDXrcN0JOhpUzhZ_6Lc7IRMwtmpSMzRqL-bErZqnDv640dtr-p5Jo1buRLeczQTpgD3IwFstKJLwFLU3MSkmZc_uqcj8-dKdwN0Qp7WJ10p4wumbNMbK7impXaxIRHa6j54ogRWt_3TegyMfiwywWxitvwkNts_5RPWpMgr0lXFPj_mS12RQqhQ5P7PMucs22UF5B7Zx0AhB2_OAPyO0jkLnpxfPBmOiEKZJ058KYlo2qLGiQdtzafwrr_TveH8jKyYCCJ3OVDP2RmRophJLiFB8NWet14Rv6XWQtsb7zlqxJqSfCryfukNvJ0PP-3wHUosaD9m1FhclLrEL_f-IhS_NEkkrORgNPKqONurGYvFsmqRRLJIsUFja3OYQKPA7zuTNChgq-3OjZS-du115PVGZ1wonCua4Aq2qoEasUdPPDGEB5wS6EnQUdtdpo5mV8ty8l2FTi24nymkUfU1MkgEaTh3jXJtbqf6wrHmo4mODcV7uFcRoAaqXk_ljrfUCxATLQQ2XJHE4DyrEpowmxJJeTddeLxHDkvuIzuZHV1NuafPmyhXepKOvDs6awFMwG2lT_yuUtQ5i1v29wHlkV7MYoV-o5WzFybjRN8ST0Xy4kveJq2O7pFvWboPNUTSYwT76yanL3IpiMVoZmihfTHYLMjK_0BL6qEIJqHOa1T17KruP9kqBZMe-sKHff5xh-yLj6SoX1b685CV934J1reOQ8m0Vm8h7Bhxiq-QURhnpU8TfBCIp854pqwfvvTk_CpBkQ-Sh0gL7_4fSeuk69EOBfeehjax8HDUNXAV3vNNzYnSo7N3Cx2UDlzMDWcmeyZs6smcTBr1jFDhBRGh2vfQZNEPb8ovkdWLrJe-uVkcas_TsZbmCm8fHuvT15SD78OgFxTMtGdT5AXEalN_CYD3eBX6KxspO-Oz83np3fELyyfggFW5es6iOs6Hy-MKTfxY-5p5ucFmIn_t1RhRNiniS4OAfZvpj8R6Jl5HUB5GEvQ_ICB6ND91w5fYkfTZwVAG7yrpr1NUponBzlrbMXuKBWhBV-Xj4f4im3n7CPmk0fzdi7YRFB9zMcYnWvjB7K84-gednmJR1skUa_IjRWYBrfbUyjozbkXCpWs2jKRglKNWHCePcVxWSTfZG01igiNmCqGeEwt1Ld4CnW3GIVi-JDXNGv4PO6vK11Zk"
DROPBOX_FOLDER = "/StrategyScience2026"
INPUT_EXCEL = "meta_cleaned.csv"
OUTPUT_CSV = "papers_import.csv"


def normalize_text(text: str) -> str:
    """Normalize string for comparison (lowercase, strip, simple normalization)."""
    if not isinstance(text, str):
        return ""
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    return text.lower().strip()


def get_shared_link(dbx: dropbox.Dropbox, path: str) -> str:
    """Get or create a shareable link for a file."""
    try:
        shared_link = dbx.sharing_create_shared_link_with_settings(path)
        return shared_link.url.replace("?dl=0", "?dl=1")
    except ApiError as e:
        if e.error.is_shared_link_already_exists():
            links = dbx.sharing_list_shared_links(path=path, direct_only=True)
            if links.links:
                return links.links[0].url.replace("?dl=0", "?dl=1")
        raise e


def main():
    print("=" * 60)
    print("Strategy Science 2026 - Paper Processor V5 (Cleaned & Robust)")
    print("=" * 60)

    # 1. Load Excel Metadata
    print(f"\n📊 Loading metadata from {INPUT_EXCEL}...")
    try:
        # Changed to CSV read
        df = pd.read_csv(INPUT_EXCEL)
        print(f"✓ Loaded {len(df)} records")
    except Exception as e:
        print(f"✗ Failed to load metadata: {e}")
        return

    # 2. Connect to Dropbox
    print("\n📁 Connecting to Dropbox...")
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        account = dbx.users_get_current_account()
        print(f"✓ Connected as: {account.name.display_name}")
    except Exception as e:
        print(f"✗ Dropbox connection failed: {e}")
        return

    # 3. List Dropbox Files
    print(f"\n📄 Scanning folder: {DROPBOX_FOLDER}")
    dbx_files = {}  # response_id -> entry
    try:
        result = dbx.files_list_folder(DROPBOX_FOLDER)
        for entry in result.entries:
            if entry.name.lower().endswith(".pdf"):
                # Map by ResponseID Prefix (R_XXXX)
                parts = entry.name.split("_")
                if len(parts) > 1:
                    possible_id = f"{parts[0]}_{parts[1]}"
                    if possible_id.startswith("R_"):
                        dbx_files[possible_id] = entry

        print(f"✓ Mapped {len(dbx_files)} files by Response ID")

    except ApiError as e:
        print(f"✗ Dropbox listing failed: {e}")
        return

    # 4. Match and Process
    print("\n🔗 Matching papers to files...")
    matched_papers = []
    missing_files = []

    # Iterate through Excel records
    for idx, row in df.iterrows():
        # Cleaned CSV columns
        response_id = str(row.get("ResponseId", ""))
        orig_filename = str(row.get("Paper_Name", ""))
        title = str(row.get("Paper", "Untitled"))
        abstract = str(row.get("Abstract", ""))
        keywords = str(row.get("Keywords", ""))

        # Clean title
        title = title.strip().replace("\n", " ")

        # Attempt match by ResponseID
        dbx_entry = dbx_files.get(response_id)

        link = ""
        if dbx_entry:
            print(f"   ✓ Matched ID {response_id}: {dbx_entry.name[:30]}...")
            try:
                link = get_shared_link(dbx, dbx_entry.path_display)
            except Exception as e:
                print(f"     ⚠ Link generation failed: {e}")
        else:
            print(f"   ✗ File missing for ID {response_id} ({orig_filename})")
            missing_files.append(orig_filename)

        # Use ResponseID as paper ID now for consistency
        paper_id = response_id

        matched_papers.append(
            {
                "id": paper_id,
                "title": title,
                "link": link,
                "keywords": keywords,
                "abstract": abstract,
                "original_filename": orig_filename,
            }
        )

    # 5. Save Output
    print(f"\n📝 Saving {len(matched_papers)} papers to {OUTPUT_CSV}...")

    fieldnames = ["id", "title", "link", "keywords", "abstract", "original_filename"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matched_papers)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Processed records: {len(matched_papers)}")
    print(f"✓ Output saved: {OUTPUT_CSV}")
    if missing_files:
        print(f"⚠ Missing files ({len(missing_files)}):")

        for mf in missing_files[:5]:
            print(f"  - {mf}")
        if len(missing_files) > 5:
            print(f"  ... and {len(missing_files) - 5} more")


if __name__ == "__main__":
    main()
