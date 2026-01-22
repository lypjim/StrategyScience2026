#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - Paper Processing Script V4

Uses LLM for ALL extraction:
- Title extraction via Qwen
- Abstract extraction via Qwen  
- Method + Keywords extraction via Qwen
"""

import os
import re
import csv
import tempfile
import requests
import dropbox
from dropbox.exceptions import ApiError

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: pdfplumber not installed.")

# =====================
# CONFIGURATION
# =====================
DROPBOX_ACCESS_TOKEN = "sl.u.AGSca_oogXOCEe0XcOpwZukt_CH7WK8XnyGxAyJWV45HxByrLJl12w_SBgkabiac5RA_coEy-J0srhHX5UEPRf8G_4Nlr3DWc8onRPfqxOKyAIpFQnGv_dWTxXaV9usIajZ2ryVGYFcXqsvXeWWMR1IP9rln7R7ePCPUeb2sbr0V2yPG7a3uvspKTU2WUxH7qv6C4Ul46qo2xuRnQnV0pSQUoFYx6p_VRN4SIDqKBYXTcWytFT9jOPm-NJv8rwOj8A8jrPz658cjKLcIoVn_hee0FanzCgWUElcu4UgXudEwB4EQciz15F6pZmnSvzSBGtLxvzfdRkI5XoVl3JzzzSuCKzu4gKHrOGdP4M1RBLkTv8SebjuzxBIDWM1EJ_pD-Jl34MbTFhIdbIMhqjcwTnjcggI8gAZMzFvbW0heh8mb07J99BEeDbUFTK1ifSrX1XNsafkhaddDV9VLHgEzIuA8UjMSIAf-ahjMlngb7pTLyQS_Njb8khlu5I53z-LMFUgHriOXsVnyuRHndPDfD-hT3wPODXY8LoPYwMN-9CSIEwEdZCr9SQYGbPwxuq5CjGdZdS7H64nwNPGTYEssW_6bzLZADBzo6DTV_yO0f11pP2yKywlshjEcZzV1JKQiRjelVPNbzzYrybQKYccjibT6v2hw5w371yWQa2moOeUBLZXztpl8EfhDSvhx75IOBLerUxUqK1-oTSFL6_5OxsfhTGdOud2vfU10P-GFBw90SSeAdUCZnQ5uPl12i5gvGcmy0vpYEWqpIhZ5mxkCw9eh2OSlRA5ykqg-so43EywB_kcfRcrZW5Ir2QYChdCvXqRL8z0CoM50_EUNRwW27hU67UQDMrIGRR7-Ax0yu9vwJDeRCTuFgki0X-lunecUdIQ0f2vtJZbDdYaCdvSD91Tl5pp1P9shx-Dj4MBA_l3NEzfG887Np-4wRGSFS8tTkkisY_nk1eeiXDy-8BcS3NSkRvzjRltnsqZ3RIGZ8SoMsR65pCMURzoGKqm8uq5kV624_bOc9qvVd8H1z9vz0YO8kzIn7aGxUCjGsiHpax5akbBeaJ9eUvVMygrHGMJonZYq-t9X1Ubtz9OfnrV2ckkWFDcTjvu01hxFsGUiQkqGyScByWsNiVzNex8Ws9-O-HtdAbVQ7egQ32SycgXvo86FQOmIA4IPOK6_eQkrCInO1-ToMP0CXgrrwpLLxw1nI3f5qAn1TYI3U2Qf2BS-GDWilzUTJvwCW7bjTVkttmqv3cvpmb1lUbsU7q3pXe03rqA"

DROPBOX_FOLDER = "/StrategyScience2026"
OUTPUT_CSV = "papers_import.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"


def extract_text_from_pdf(pdf_path: str, max_pages: int = 3) -> str:
    """Extract text from first pages of PDF."""
    if not PDF_SUPPORT:
        return ""
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        # Clean up
        text = re.sub(r'\(cid:\d+\)', '', text)
        return text[:6000]
    except Exception as e:
        print(f"       ⚠ PDF read error: {e}")
        return ""


def query_llm(prompt: str, max_tokens: int = 500) -> str:
    """Query Ollama with prompt, return response."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": max_tokens
                }
            },
            timeout=120
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
    except Exception as e:
        print(f"       ⚠ LLM error: {e}")
    return ""


def extract_paper_info(text: str, filename: str) -> dict:
    """
    Use LLM to extract title, abstract, and keywords from paper text.
    Returns dict with 'title', 'abstract', 'keywords'.
    """
    prompt = f"""You are extracting information from an academic paper PDF.

IGNORE all metadata like:
- JSTOR links, DOIs, "Downloaded from", "Terms and Conditions"
- Author profiles, citations counts, "See Profile"
- Journal names alone (like "Management Science")
- Publisher info, page numbers, dates

From the text below, extract:

1. TITLE: The actual paper title (not journal name, not author names)
2. ABSTRACT: The paper's abstract (the summary paragraph, NOT introduction text)
3. KEYWORDS: 5-6 topic keywords describing what the paper is about

Filename hint: {filename}

Paper text:
{text[:4000]}

Respond in EXACTLY this format (no other text):
TITLE: [paper title here]
ABSTRACT: [abstract text here, 2-4 sentences]
KEYWORDS: [keyword1, keyword2, keyword3, keyword4, keyword5]"""

    response = query_llm(prompt, max_tokens=600)
    
    result = {
        'title': '',
        'abstract': '',
        'keywords': ''
    }
    
    if not response:
        return result
    
    # Parse response
    for line in response.split('\n'):
        line = line.strip()
        if line.upper().startswith('TITLE:'):
            result['title'] = line[6:].strip()
        elif line.upper().startswith('ABSTRACT:'):
            result['abstract'] = line[9:].strip()
        elif line.upper().startswith('KEYWORDS:'):
            result['keywords'] = line[9:].strip()
    
    return result


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


def check_ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            for m in models:
                if 'qwen' in m.get('name', '').lower():
                    return True
            print("⚠ Qwen model not found")
    except:
        print("⚠ Ollama not running")
    return False


def main():
    print("=" * 60)
    print("Strategy Science Conference 2026 - Paper Processor V4")
    print("=" * 60)
    print("Using LLM for ALL extraction (title, abstract, keywords)")
    
    # Check Ollama
    print("\n🤖 Checking Ollama...")
    if not check_ollama_available():
        print("✗ Ollama not available. Exiting.")
        return
    print("✓ Ollama + Qwen ready")
    
    # Initialize Dropbox
    print("\n📁 Connecting to Dropbox...")
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    
    try:
        account = dbx.users_get_current_account()
        print(f"✓ Connected as: {account.name.display_name}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # List files
    print(f"\n📄 Scanning folder: {DROPBOX_FOLDER}")
    try:
        result = dbx.files_list_folder(DROPBOX_FOLDER)
        files = [entry for entry in result.entries if entry.name.lower().endswith('.pdf')]
    except ApiError as e:
        print(f"✗ Error: {e}")
        return
    
    print(f"✓ Found {len(files)} PDF files\n")
    
    # Process each file
    papers = []
    for i, file_entry in enumerate(sorted(files, key=lambda x: x.name)):
        paper_id = f"P{str(i + 1).zfill(3)}"
        filename = file_entry.name
        
        print(f"[{paper_id}] Processing {filename[:50]}...")
        
        # Download PDF
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                _, response = dbx.files_download(file_entry.path_display)
                tmp.write(response.content)
                tmp_path = tmp.name
        except Exception as e:
            print(f"       ✗ Download failed: {e}")
            continue
        
        # Get shareable link
        try:
            link = get_shared_link(dbx, file_entry.path_display)
            print(f"       ✓ Link generated")
        except Exception as e:
            print(f"       ✗ Link failed: {e}")
            link = ""
        
        # Extract text
        text = extract_text_from_pdf(tmp_path)
        
        # Use LLM to extract everything
        print(f"       ⏳ Extracting with LLM...")
        info = extract_paper_info(text, filename)
        
        # Fallback title if LLM fails
        if not info['title']:
            info['title'] = filename.replace('.pdf', '').replace('.PDF', '')[:80]
        
        print(f"       ✓ Title: {info['title'][:50]}...")
        if info['abstract']:
            print(f"       ✓ Abstract: {len(info['abstract'])} chars")
        if info['keywords']:
            print(f"       ✓ Keywords: {info['keywords'][:50]}...")
        
        # Clean up
        if tmp_path:
            os.unlink(tmp_path)
        
        papers.append({
            'id': paper_id,
            'title': info['title'],
            'link': link,
            'keywords': info['keywords'],
            'abstract': info['abstract'],
            'original_filename': filename
        })
    
    # Write CSV
    print(f"\n📝 Writing {OUTPUT_CSV}...")
    fieldnames = ['id', 'title', 'link', 'keywords', 'abstract', 'original_filename']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)
    
    print(f"✓ Saved {len(papers)} papers to {OUTPUT_CSV}")
    print("\n" + "=" * 60)
    print("Done! All fields extracted via LLM.")
    print("=" * 60)


if __name__ == "__main__":
    main()
