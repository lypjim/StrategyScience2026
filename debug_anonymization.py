
import os
import csv
import io
import pandas as pd
import dropbox
import pypdf

DROPBOX_ACCESS_TOKEN = "sl.u.AGSnheXxkSK25BQbckKQM6Re6uw0vSSN55CojaYDHPai9A5aUapdwYfdRMnefuLDVTRLqoFcH1BscP7qMJm9DfutBhOWb7x07HndsRO1WplMkDtevBVp0KxC17mrb5GsdEa9BVzramSNwkFsm6Qg1Y19lhdb6lZ2mWgr4DdhQMx12L_WkBy6ByBhrvn9BOWDLGSjuNMShSQTc4QxEsMcxL3JGYZ6gTcZsLdUZN6hMUAHwBnKyxUveYlB6vnNGhicaMoA_rmy1PnYx-kKL0XVtGK0bAr4lx4Aohj6Cfi26bRjpqZSxh1uz9IVC48KGNHLCK4ED8Razwxjpc_f0ftx6zACY64OiCwqRnRrxoWA1tMVzPF6bsK4B3crEXcBcdnKHFztHftSdlRt712MHf28rFjKoUl8BagO2f3_1Ou4r5lp1RzlvqlNcBYIq9pBymsEfi3DoXfaS9lFYXq16bTFUVeXgumw5-CeS3k-JB4PPy9hR12vhbFTfYkPlJqC8tS5N_9CvBa3Vq1QeqTtsCucGUurATwhk0pMF0VPx_3GaKw9jN0X-PONEPeefeD5nXJ6jUGQocvrYOuVq4dnVogbGSeZrxt2VZPrJeMyfgFYvtSn3Ei5PPJ-ooofv7mv3Nq_yCl0xadg0qanWr_VcZk_4RakgdW2WPOY08KmKMQDxcjEwacy9zb5Qj4uLMJkMtHcooimhJlrNwJc0uPOF6Xe3nOCVg45Hou41oOueldYGdSB7MFKYgW_91FpE32QY4NtV_hmw0Q4Sdam0eHFUDpwaN6ZCawUVzU6EETW1ybOiz0P6NQ71LixR9-C8Hww9MEXdDf3VoQ56SUBQO1CIV6isCG_rc1aO2mYMab5xa5fAGnsTT9tLdZJiS46_FCz66CYG1dWwMsKgCd_a4T0qoW4jeC6R7L5rPzSfJlXbvEvK9FviTcVXmQWYiCY9bd5uqe9Te-mUthSCMmSD-70O3VHD_t7QX_pRVk42WDtyyXI6D8wEpcIGF3nTw4U_mXk89qGw9_zcYC1fCmb7jFXYra0VbrW-N2FBRDV3RohQgfw1vzGYIYlVnsA68RmN99KPpTr9wdeftZr-XSB7L7Nq4LhPyXBkXim0Tx8olV6eWIC-y9DpLPzjPvcych4l0_0f7U4RW-oS2RG9i14jVT5bGw1eVv0kzKZJNtB47kvRJxsImUHjiT7YKb5B3SbqRaSeb89Xb78w718n6fsxKjAQyXIFn9HUKheV0g4pttJbuwWu4ClA5Do280warB9NLF1rmbbpYk"

METADATA_FILE = "meta_cleaned.csv"
TARGET_FILE_SUBSTRING = "diamond kuan 2026.pdf" # P010

def main():
    print("DEBUG MODE: Checking one file...")
    
    # 1. Load Data
    df = pd.read_csv(METADATA_FILE)
    print("Columns:", df.columns.tolist())
    
    # 2. Find target
    target_row = None
    target_fname = ""
    
    for _, row in df.iterrows():
        fname = str(row.get('Paper_Name', ''))
        if TARGET_FILE_SUBSTRING in fname:
            target_row = row
            target_fname = fname
            break
            
    if target_row is None:
        print("Target file not found in metadata!")
        return

    print(f"Found Metadata for: {target_fname}")
    
    # Extract Authors
    authors = []
    # Dump row keys to see exact names
    # print(target_row)
    
    # Try multiple variants for Columns
    for col in df.columns:
        if 'Name' in col or 'Author' in col or 'author' in col:
            val = str(target_row[col]).strip()
            if val and val.lower() != 'nan':
                print(f"  Field '{col}': {val}")
                # Naively add everything for debug
                # authors.append(val)

    # Re-impl extraction logic
    if pd.notna(target_row.get('Name')): authors.append(str(target_row['Name']).strip())
    if pd.notna(target_row.get('Co author name')): authors.append(str(target_row['Co author name']).strip())
    # Guessing column names based on print output earlier
    # "Coauthor 2 " might have space
    c2 = [c for c in df.columns if 'Coauthor 2' in c]
    if c2: 
        val = str(target_row[c2[0]]).strip()
        if val != 'nan': authors.append(val)

    print("Extracted Authors to check:", authors)
    
    # 3. Download PDF
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    res = dbx.files_list_folder("/StrategyScience2026")
    file_path = None
    for entry in res.entries:
        if TARGET_FILE_SUBSTRING in entry.name:
            file_path = entry.path_display
            print("Found file in Dropbox:", file_path)
            break
            
    if not file_path:
        print("File not found in Dropbox")
        return
        
    _, res = dbx.files_download(file_path)
    pdf_bytes = res.content
    
    # 4. Check Text
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    page1 = reader.pages[0].extract_text()
    
    print("-" * 20)
    print("PAGE 1 TEXT (First 500 chars):")
    print(page1[:500])
    print("-" * 20)
    
    print("checking matches...")
    for auth in authors:
        if auth.lower() in page1.lower():
            print(f"MATCH FOUND: '{auth}'")
        else:
            print(f"No match for '{auth}'")

if __name__ == "__main__":
    main()
