#!/usr/bin/env python3
"""
FINAL Conservative PDF Anonymizer
- Precise term-based redaction only
- Preserves paper structure
- Uses updated Dropbox token
"""

import os
import pandas as pd
import dropbox
import unicodedata
from typing import Set

# Configuration with updated token
DROPBOX_ACCESS_TOKEN = "sl.u.AGSDEemh3KB4DXlC7aKYzy6rVbTje1sTKJGeZC1VYEmk2GaecHP0G63x2TuSuiUz26MujHm1P0sPe-vZr42IPDibHMtmyDXrcN0JOhpUzhZ_6Lc7IRMwtmpSMzRqL-bErZqnDv640dtr-p5Jo1buRLeczQTpgD3IwFstKJLwFLU3MSkmZc_uqcj8-dKdwN0Qp7WJ10p4wumbNMbK7impXaxIRHa6j54ogRWt_3TegyMfiwywWxitvwkNts_5RPWpMgr0lXFPj_mS12RQqhQ5P7PMucs22UF5B7Zx0AhB2_OAPyO0jkLnpxfPBmOiEKZJ058KYlo2qLGiQdtzafwrr_TveH8jKyYCCJ3OVDP2RmRophJLiFB8NWet14Rv6XWQtsb7zlqxJqSfCryfukNvJ0PP-3wHUosaD9m1FhclLrEL_f-IhS_NEkkrORgNPKqONurGYvFsmqRRLJIsUFja3OYQKPA7zuTNChgq-3OjZS-du115PVGZ1wonCua4Aq2oEasUdPPDGEB5wS6EnQUdtdpo5mV8ty8l2FTi24nymkUfU1MkgEaTh3jXJtbqf6wrHmo4mODcV7uFcRoAaqXk_ljrfUCxATLQQ2XJHE4DyrEpowMXFf7-TsZbmCm8fHuvT15SD78OgFxTMtGdT5AXEalN_CYD3eBX6KxspO-Oz83np3fELyyfggFW5es6iOs6Hy-MKTfxY-5p5ucFmIn_t1RhRNiniS4OAfZvpj8R6Jl5HUB5GEvQ_ICB6ND91w5fYkfTZwVAG7yrpr1NUponBzlrbMXuKBWhBV-Xj4f4im3n7CPmk0fzdi7YRFB9zMcYnWvjB7K84-gednmJR1skUa_IjRWYBrfbUyjozbkC5dHsMLJxYZQusHc6hD12rOoK4GDNpQmOi"
DROPBOX_FOLDER = "/StrategyScience2026"
INPUT_EXCEL = "meta_cleaned.csv"
OUTPUT_DIR = "anonymized_pdfs"


def normalize_text(text: str) -> str:
    """Normalize string for comparison."""
    if not isinstance(text, str):
        return ""
    return unicodedata.normalize("NFKD", text).lower().strip()


def get_sensitive_terms(row) -> Set[str]:
    """Extract all sensitive terms from a row."""
    terms = set()

    # Columns with sensitive info
    cols = [
        "Name",
        "Email",
        "institution",
        "Co author name",
        "Coauthor emails",
        "Coauthor institution",
        "Coauthor 2\xa0",
        "Coauthor 2 email",
        "Coauthor institution.1",
        "Coauthor 3",
        "coauthor 3 email",
        "coauthor 3 instituti",
    ]

    for col in cols:
        if col in row and pd.notna(row[col]):
            val = str(row[col]).strip()
            # Split values and filter short strings
            parts = [p.strip() for p in val.replace(",", ";").split(";")]
            for part in parts:
                if len(part) > 2:  # Only meaningful terms
                    terms.add(part)

    return terms


def redact_pdf_conservative(input_path: str, output_path: str, terms: Set[str]):
    """Conservative redaction: remove only specific terms."""
    try:
        import fitz

        doc = fitz.open(input_path)

        # Redact specific terms on first page only
        page = doc[0]
        redacted_count = 0

        for term in terms:
            quads = page.search_for(term)
            for quad in quads:
                page.add_redact_annot(quad)
                redacted_count += 1

        # Apply redactions
        page.apply_redactions()

        # Save
        doc.save(output_path)
        doc.close()

        return True, redacted_count

    except Exception as e:
        print(f"   ✗ Redaction failed: {e}")
        return False, 0


def main():
    print("=" * 60)
    print("Strategy Science 2026 - Conservative PDF Anonymizer")
    print("=" * 60)

    # Create output dir
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 Output directory: {OUTPUT_DIR}")

    # Load metadata
    print(f"\n📊 Loading metadata from {INPUT_EXCEL}...")
    try:
        df = pd.read_csv(INPUT_EXCEL)
        print(f"✓ Loaded {len(df)} papers")
    except Exception as e:
        print(f"✗ Failed to load metadata: {e}")
        return

    # Connect to Dropbox
    print("\n📁 Connecting to Dropbox...")
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        account = dbx.users_get_current_account()
        print(f"✓ Connected as: {account.name.display_name}")
    except Exception as e:
        print(f"✗ Dropbox connection failed: {e}")
        return

    # Process all papers conservatively
    success_count = 0
    for idx, row in df.iterrows():
        response_id = str(row.get("ResponseId", ""))
        filename = str(row.get("Paper_Name", ""))
        terms = get_sensitive_terms(row)

        print(f"\n[{idx + 1}/{len(df)}] {filename[:40]}...")
        print(f"   Found {len(terms)} sensitive terms to redact")

        # Find matching file in Dropbox
        dbx_entry = None
        try:
            result = dbx.files_list_folder(DROPBOX_FOLDER)
            for entry in result.entries:
                if entry.name.lower().endswith(".pdf") and response_id in entry.name:
                    dbx_entry = entry
                    break
        except Exception as e:
            print(f"   ✗ Dropbox search failed: {e}")
            continue

        if not dbx_entry:
            print(f"   ✗ File not found for ID: {response_id}")
            continue

        # Download and process
        local_path = os.path.join(OUTPUT_DIR, f"temp_{response_id}.pdf")
        final_path = os.path.join(OUTPUT_DIR, f"{response_id}.pdf")

        try:
            # Download
            with open(local_path, "wb") as f:
                metadata, res = dbx.files_download(path=dbx_entry.path_display)
                f.write(res.content)

            # Redact conservatively
            success, redacted_count = redact_pdf_conservative(
                local_path, final_path, terms
            )

            if success:
                print(f"   ✓ Redacted {redacted_count} terms")
                success_count += 1
            else:
                print("   ✗ Redaction failed")

            # Cleanup temp file
            if os.path.exists(local_path):
                os.remove(local_path)

        except Exception as e:
            print(f"   ✗ Error: {e}")
            continue

    print(f"\n✅ Successfully processed {success_count} papers to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
