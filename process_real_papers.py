#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - Real Paper Processor
Merges Metadata (CSV) with Dropbox Files + ANONYMIZATION.

1. Reads meta_cleaned.csv for Title, Abstract, Keywords, and AUTHORS/AFFILIATIONS.
   - Index by ResponseID for robust matching.
2. Scans Dropbox for matching filenames (extracting ResponseID).
3. Checks PDF Page 1 for Author Names using Robust Regex.
4. If found -> Removes Page 1 (Anonymizes).
5. Uploads Anonymized PDF to /StrategyScience2026/Anonymized.
6. Generates Dropbox Link (to anonymized version if applicable).
7. Outputs papers_real.csv for import.
"""

import os
import csv
import io
import time
import re
import pandas as pd
import dropbox
from dropbox.exceptions import ApiError
from dropbox.files import WriteMode
import pypdf

# =====================
# CONFIGURATION
# =====================
DROPBOX_ACCESS_TOKEN = "sl.u.AGSnheXxkSK25BQbckKQM6Re6uw0vSSN55CojaYDHPai9A5aUapdwYfdRMnefuLDVTRLqoFcH1BscP7qMJm9DfutBhOWb7x07HndsRO1WplMkDtevBVp0KxC17mrb5GsdEa9BVzramSNwkFsm6Qg1Y19lhdb6lZ2mWgr4DdhQMx12L_WkBy6ByBhrvn9BOWDLGSjuNMShSQTc4QxEsMcxL3JGYZ6gTcZsLdUZN6hMUAHwBnKyxUveYlB6vnNGhicaMoA_rmy1PnYx-kKL0XVtGK0bAr4lx4Aohj6Cfi26bRjpqZSxh1uz9IVC48KGNHLCK4ED8Razwxjpc_f0ftx6zACY64OiCwqRnRrxoWA1tMVzPF6bsK4B3crEXcBcdnKHFztHftSdlRt712MHf28rFjKoUl8BagO2f3_1Ou4r5lp1RzlvqlNcBYIq9pBymsEfi3DoXfaS9lFYXq16bTFUVeXgumw5-CeS3k-JB4PPy9hR12vhbFTfYkPlJqC8tS5N_9CvBa3Vq1QeqTtsCucGUurATwhk0pMF0VPx_3GaKw9jN0X-PONEPeefeD5nXJ6jUGQocvrYOuVq4dnVogbGSeZrxt2VZPrJeMyfgFYvtSn3Ei5PPJ-ooofv7mv3Nq_yCl0xadg0qanWr_VcZk_4RakgdW2WPOY08KmKMQDxcjEwacy9zb5Qj4uLMJkMtHcooimhJlrNwJc0uPOF6Xe3nOCVg45Hou41oOueldYGdSB7MFKYgW_91FpE32QY4NtV_hmw0Q4Sdam0eHFUDpwaN6ZCawUVzU6EETW1ybOiz0P6NQ71LixR9-C8Hww9MEXdDf3VoQ56SUBQO1CIV6isCG_rc1aO2mYMab5xa5fAGnsTT9tLdZJiS46_FCz66CYG1dWwMsKgCd_a4T0qoW4jeC6R7L5rPzSfJlXbvEvK9FviTcVXmQWYiCY9bd5uqe9Te-mUthSCMmSD-70O3VHD_t7QX_pRVk42WDtyyXI6D8wEpcIGF3nTw4U_mXk89qGw9_zcYC1fCmb7jFXYra0VbrW-N2FBRDV3RohQgfw1vzGYIYlVnsA68RmN99KPpTr9wdeftZr-XSB7L7Nq4LhPyXBkXim0Tx8olV6eWIC-y9DpLPzjPvcych4l0_0f7U4RW-oS2RG9i14jVT5bGw1eVv0kzKZJNtB47kvRJxsImUHjiT7YKb5B3SbqRaSeb89Xb78w718n6fsxKjAQyXIFn9HUKheV0g4pttJbuwWu4ClA5Do280warB9NLF1rmbbpYk"

DROPBOX_FOLDER = "/StrategyScience2026"
ANONYMIZED_FOLDER = "/StrategyScience2026/Anonymized"
METADATA_FILE = "meta_cleaned.csv"
OUTPUT_CSV = "papers_real.csv"

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
        print(f"       ⚠ Link Warning: {e}")
        return ""

def upload_file(dbx, content_bytes, path):
    """Uploads bytes to Dropbox, overwriting if exists."""
    dbx.files_upload(content_bytes, path, mode=WriteMode('overwrite'))

def check_and_anonymize(pdf_bytes, authors):
    """
    Checks if first page contains any author names using Regex.
    If yes, removes first page.
    Returns: (is_modified, new_pdf_bytes, reason)
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) < 1:
            return False, pdf_bytes, "Empty PDF"

        page1_text = reader.pages[0].extract_text()
        # Clean text: keep case but remove excess whitespace/newlines
        page1_clean = re.sub(r'\s+', ' ', page1_text)
        
        found_match = False
        matched_name = ""

        for auth in authors:
            if not auth or len(auth) < 4: continue 
            
            # Split Auth into First and Last
            # "Jenny Kuan" -> First: J..., Last: Kuan
            parts = auth.split()
            if len(parts) >= 2:
                last_name = parts[-1]
                first_name_initial = parts[0][0]
                
                # Logic: Find Last Name. If found, look for First Initial or Name preceding it.
                if re.search(rf"\b{re.escape(last_name)}\b", page1_clean, re.IGNORECASE):
                    # Robust Pattern:
                    # \b{Initial}[a-z]* (Starts with Initial)
                    # (?:.{0,40})       (Up to 40 chars of anything - middle names, spaces)
                    # \b{Last}\b        (Last Name)
                    pat = rf"\b{re.escape(first_name_initial)}[a-z]*\b(?:.{{0,50}})\b{re.escape(last_name)}\b"
                    
                    if re.search(pat, page1_clean, re.IGNORECASE):
                         found_match = True
                         matched_name = auth
                         break
            else:
                 # Single word name? Exact match only
                 if str(auth).lower() in page1_clean.lower():
                     found_match = True
                     matched_name = auth
                     break
            
        if found_match:
            # Anonymize: Create new PDF without Page 1
            writer = pypdf.PdfWriter()
            for i in range(1, len(reader.pages)):
                writer.add_page(reader.pages[i])
            
            out_stream = io.BytesIO()
            writer.write(out_stream)
            return True, out_stream.getvalue(), f"Found author: {matched_name}"
            
        return False, pdf_bytes, "Clean"

    except Exception as e:
        return False, pdf_bytes, f"Error reading PDF: {e}"

def main():
    print("=" * 60)
    print("Strategy Science '26 - Real Paper Processor (Matches by ResponseID)")
    print("=" * 60)

    # 1. Load Metadata
    print(f"\n📊 Reading metadata from {METADATA_FILE}...")
    try:
        df = pd.read_csv(METADATA_FILE)
    except Exception as e:
        print(f"   ✗ Error reading metadata: {e}")
        return

    # Create Dictionary: ResponseID -> Row Data
    meta_by_id = {}
    
    for _, row in df.iterrows():
        # Get Response ID (Key)
        rid = str(row.get('ResponseId', '')).strip()
        fname = str(row.get('Paper_Name', '')).strip()
        
        if rid:
            authors = []
            affiliations = []

            # 1. Main Author
            if pd.notna(row.get('Name')): 
                authors.append(str(row['Name']).strip())
            if pd.notna(row.get('institution')): 
                affiliations.append(str(row['institution']).strip())

            # 2. Coauthor 1
            if pd.notna(row.get('Co author name')): 
                authors.append(str(row['Co author name']).strip())
            if pd.notna(row.get('Coauthor institution')): 
                affiliations.append(str(row['Coauthor institution']).strip())
            
            # 3. Coauthor 2 - tricky name logic
            c2_name = [c for c in df.columns if 'Coauthor 2' in c and 'email' not in c.lower() and 'institution' not in c.lower()]
            if c2_name: 
                 val = str(row.get(c2_name[0], '')).strip()
                 if val and val.lower() != 'nan': authors.append(val)
            
            c2_aff = [c for c in df.columns if 'Coauthor 2' in c and 'institution' in c.lower()] # Note: 'Coauthor institution.1' often
            if not c2_aff:
                c2_aff = [c for c in df.columns if 'Coauthor institution.1' in c] # direct check
            
            if c2_aff:
                 val = str(row.get(c2_aff[0], '')).strip()
                 if val and val.lower() != 'nan': affiliations.append(val)

            # 4. Coauthor 3
            c3_name = [c for c in df.columns if 'Coauthor 3' in c and 'email' not in c.lower() and 'institution' not in c.lower()]
            if c3_name: 
                 val = str(row.get(c3_name[0], '')).strip()
                 if val and val.lower() != 'nan': authors.append(val)
            
            c3_aff = [c for c in df.columns if 'coauthor 3 instituti' in c.lower()]
            if c3_aff:
                 val = str(row.get(c3_aff[0], '')).strip()
                 if val and val.lower() != 'nan': affiliations.append(val)

            # Deduplicate affiliations
            unique_aff = []
            seen_aff = set()
            for aff in affiliations:
                if aff and aff not in seen_aff:
                    unique_aff.append(aff)
                    seen_aff.add(aff)

            meta_by_id[rid] = {
                'title': str(row.get('Paper', '')).strip(),
                'abstract': str(row.get('Abstract', '')).strip(),
                'keywords': str(row.get('Keywords', '')).strip(),
                'clean_filename_hint': fname,
                'authors_list': authors, # List for anonymization
                'authors_str': ", ".join(authors), # String for CSV
                'affiliations_str': "; ".join(unique_aff) # String for CSV
            }
            
    print(f"   ✓ Indexed {len(meta_by_id)} metadata entries by ResponseId")

    # 2. Connect Dropbox
    print("\n📁 Connecting to Dropbox...")
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        result = dbx.files_list_folder(DROPBOX_FOLDER)
        files = [entry for entry in result.entries if entry.name.lower().endswith('.pdf')]
    except ApiError as e:
        print(f"   ✗ Connection/List Error: {e}")
        return
    
    print(f"   ✓ Found {len(files)} PDF files")

    # 3. Match and Process
    papers = []
    print("\n🔄 Processing papers...")
    
    total_files = len(files)
    
    for i, file_entry in enumerate(sorted(files, key=lambda x: x.name)):
        filename = file_entry.name
        
        # Match Logic: Extract ResponseID from filename?
        match = re.search(r"(R_[A-Za-z0-9]+)", filename)
        rid_found = match.group(1) if match else None
        
        meta = None
        if rid_found and rid_found in meta_by_id:
            meta = meta_by_id[rid_found]
            status_icon = "✓"
        else:
             meta = {
                 'title': filename, 'abstract': '', 'keywords': '', 
                 'authors_list': [], 'authors_str': '', 'affiliations_str': ''
             }
             status_icon = "⚠"

        paper_id = f"P{str(i + 1).zfill(3)}"
        print(f"   [{i+1}/{total_files}] {paper_id} {status_icon} ({rid_found}) {filename[:20]}...", end='', flush=True)

        # Download content
        try:
            _, res = dbx.files_download(file_entry.path_display)
            pdf_bytes = res.content
        except Exception as e:
            print(f" ✗ Download Error: {e}")
            papers.append({
                'id': paper_id,
                'title': meta['title'],
                'link': "", # Failed
                'keywords': meta['keywords'],
                'abstract': meta['abstract'],
                'authors': meta['authors_str'],
                'affiliations': meta['affiliations_str'],
                'original_filename': filename,
                'original_id': rid_found or ""
            })
            continue

        # Anonymize Check
        is_mod, new_bytes, reason = check_and_anonymize(pdf_bytes, meta['authors_list'])
        
        final_path = file_entry.path_display # Default to original
        
        if is_mod:
            print(f" -> ✂️  ANONYMIZED ({reason})", end='', flush=True)
            anon_filename = f"Anonymized_{paper_id}_{filename}"
            anon_path = f"{ANONYMIZED_FOLDER}/{anon_filename}"
            try:
                upload_file(dbx, new_bytes, anon_path)
                final_path = anon_path
                print(" -> Uploaded", end='', flush=True)
            except Exception as e:
                print(f" -> ✗ Upload Fail: {e}")
        else:
            print(f" -> Clean ({reason})", end='', flush=True)

        # Generate Link
        link = get_shared_link(dbx, final_path)
        print(" -> Linked")

        papers.append({
            'id': paper_id,
            'title': meta['title'],
            'link': link,
            'keywords': meta['keywords'],
            'abstract': meta['abstract'],
            'authors': meta['authors_str'],
            'affiliations': meta['affiliations_str'],
            'original_filename': filename,
            'original_id': rid_found or ""
        })

    # 5. Save CSV
    fieldnames = ['id', 'title', 'link', 'keywords', 'abstract', 'authors', 'affiliations', 'original_filename', 'original_id']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)

    print(f"\n{'='*60}")
    print(f"Done! Processed {len(papers)} papers. CSV Saved.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
