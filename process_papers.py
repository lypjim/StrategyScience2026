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
DROPBOX_ACCESS_TOKEN = "sl.u.AGTQQrIcfFL5u_FXsPsPA2GEa3gKN7w2RnO3teI63UJTqDu-dgSFdAY91L1SzRYEDgB3b65bDx83MlinJzKYNSZXJ2hvo2pwHD_mQXfEZ3O41xIdhZXHm6wS9YAH7P_MV26Zlez1LenxjZYbk2Wj7hsvMZJTVP1QVJpE0T-qzui1GJ7v2WmTCemGzDGlKTg5Qpd7nNgEGwnEf0OJZsYbqwG1eWyAJMWIPd8ikwpLj6AmubXGuNiXVOmJz1BTrqRkZN9UnzWFZQ6Z9kcsIM2TaLaa-lWyse0nL_DrEaLfnTTr94aqEQaMKRj5i6KFoJky36ctVD8HxFO2buPg-nfu1_y-BgM3pmSGlVLqmGeMEdPoRAil9IwjKhom0G2xxDXEA131IB-jVjXAac_IfsMvKLbC2PIb02B84VDQ6yykxLP_pFg7II9EphTlcBhce8DGFEibplJ4gONQzb_9JjOXWzitvgezUqQX-3DzbYKqjvv__6kMzxi3nSYG_jo9SUUkKvkPLmzTzPSRUI1Kt4VkpSXLfVF-AXqyOrQMVgXLvp0a07r1P56hwwiXjxgORgBF6rPIiFQEYEETH57C7eEl3ESn74uUOyidIvLDeaGk_qofxKK5Xj-g-SHstEJlzDJSuLf6I_6FYiaRTdhjxzZcncn-VduIjV4nyi4cKF1IoIJnJy2VuNDuxxaDCP_JM49e0fiaM-LZpCQ2czJesxN4nokuOb-WD1aie82GZXW5ZC08-zMSi5x-_5bmRygGJdeC5GgcMMTUZxaPbnwJEkszW1na8Yy1TgmI0MR_1TBcSqKmkV-rZmkGItxJ5pJiXmYVsiWl5c2Sz9vzw7ZqPsMUUyb-GcKOQLbuJYKGXn2ELWkqn8-GMFp7CE1iYEPS7zdgLC8ohU24NC4WAadSRj_yq_EoCLdmMvJ6Gd9TlF3bxx9UtKJVShaRczf_DH4iqOHA1aZjBOd50HUEyvQktScbvTv4qodIjz1nbNyeieaZkCO0Ntve4kQDqdg53YdywfZ3mnX9w7fDym2qoxnYb0WUb7auT0UUiAxeFuQasxl2mLtV8XoWfBU4kSER-0RuFNMtGM1OtM0qMxk9-FaPmuAKlwTu_MVYi8thsePjhDFNdfg1pU3NXCyBkDKJtBAlYFWemy-BC1wrtEsWjY_BwlQjI_fJ-aTWBMOE24d-C6mIeL9CSdmVbvl45gIKNnFhcTzdzqFe1CdFjY8d6R5B2vWrnENkkePaTY3lgnH9___zfAzaF9oDjCJ4rCeNh3CE6j4k6ZQ"

DROPBOX_FOLDER = "/StrategyScience2026"
OUTPUT_CSV = "papers_import.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"  # Faster model, keeping improved prompt/parsing


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
            timeout=300  # Increased timeout for qwen3:14b
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

1. TITLE: The actual paper title in Title Case (not ALL CAPS, not journal name)
2. ABSTRACT: The paper's COMPLETE abstract exactly as written (usually 150-300 words, preserve the full text)
3. KEYWORDS: 5-6 lowercase topic keywords describing what the paper is about

Filename hint: {filename}

Paper text:
{text[:8000]}

Respond in EXACTLY this format (no other text):
TITLE: [Title In Title Case Like This]
ABSTRACT: [complete abstract text, include ALL sentences]
KEYWORDS: [keyword1, keyword2, keyword3, keyword4, keyword5]"""

    response = query_llm(prompt, max_tokens=1500)  # Increased for full abstracts
    
    result = {
        'title': '',
        'abstract': '',
        'keywords': ''
    }
    
    if not response:
        return result
    
    # Parse response - handle multiline abstracts
    lines = response.split('\n')
    current_field = None
    abstract_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.upper().startswith('TITLE:'):
            result['title'] = line_stripped[6:].strip()
            current_field = 'title'
        elif line_stripped.upper().startswith('ABSTRACT:'):
            abstract_lines.append(line_stripped[9:].strip())
            current_field = 'abstract'
        elif line_stripped.upper().startswith('KEYWORDS:'):
            result['keywords'] = line_stripped[9:].strip()
            current_field = 'keywords'
        elif current_field == 'abstract' and line_stripped:
            # Continue collecting abstract lines
            abstract_lines.append(line_stripped)
    
    result['abstract'] = ' '.join(abstract_lines).strip()
    
    # Normalize formatting for consistency
    if result['title']:
        # Convert to Title Case (handles ALL CAPS titles)
        result['title'] = result['title'].title()
        # Fix common words that should be lowercase
        for word in ['A', 'An', 'And', 'As', 'At', 'But', 'By', 'For', 'In', 'Of', 'On', 'Or', 'The', 'To', 'With']:
            result['title'] = result['title'].replace(f' {word} ', f' {word.lower()} ')
        # Keep first word capitalized
        if result['title']:
            result['title'] = result['title'][0].upper() + result['title'][1:]
    
    if result['keywords']:
        # Lowercase all keywords
        result['keywords'] = result['keywords'].lower()
    
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
    
    # Helper to save papers to CSV
    fieldnames = ['id', 'title', 'link', 'keywords', 'abstract', 'original_filename']
    def save_papers(papers_list, is_final=False):
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(papers_list)
        if is_final:
            print(f"\n✓ Final save: {len(papers_list)} papers to {OUTPUT_CSV}")
        else:
            print(f"       💾 Batch saved: {len(papers_list)} papers so far")
    
    # Process each file
    papers = []
    total_files = len(files)
    import time
    start_time = time.time()
    
    for i, file_entry in enumerate(sorted(files, key=lambda x: x.name)):
        paper_id = f"P{str(i + 1).zfill(3)}"
        filename = file_entry.name
        
        elapsed = time.time() - start_time
        avg_time = elapsed / (i + 1) if i > 0 else 0
        remaining = avg_time * (total_files - i - 1) if i > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"[{paper_id}] ({i+1}/{total_files}) Processing: {filename[:45]}...")
        print(f"    Elapsed: {elapsed/60:.1f} min | Est. remaining: {remaining/60:.1f} min")
        print(f"{'='*60}")
        
        # Download PDF
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                _, response = dbx.files_download(file_entry.path_display)
                tmp.write(response.content)
                tmp_path = tmp.name
            print(f"    ✓ Downloaded PDF")
        except Exception as e:
            print(f"    ✗ Download failed: {e}")
            continue
        
        # Get shareable link
        try:
            link = get_shared_link(dbx, file_entry.path_display)
            print(f"    ✓ Link generated")
        except Exception as e:
            print(f"    ✗ Link failed: {e}")
            link = ""
        
        # Extract text
        text = extract_text_from_pdf(tmp_path)
        print(f"    ✓ Extracted {len(text)} chars from PDF")
        
        # Use LLM to extract everything
        print(f"    ⏳ Calling LLM for extraction...")
        info = extract_paper_info(text, filename)
        
        # Fallback title if LLM fails
        if not info['title']:
            info['title'] = filename.replace('.pdf', '').replace('.PDF', '')[:80]
        
        print(f"    ✓ Title: {info['title'][:50]}...")
        if info['abstract']:
            print(f"    ✓ Abstract: {len(info['abstract'])} chars (~{len(info['abstract'].split())} words)")
        else:
            print(f"    ⚠ No abstract extracted")
        if info['keywords']:
            print(f"    ✓ Keywords: {info['keywords'][:50]}...")
        
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
        
        # Batch save every 5 papers
        if len(papers) % 5 == 0:
            save_papers(papers, is_final=False)
    
    # Final save
    print(f"\n📝 Final save to {OUTPUT_CSV}...")
    save_papers(papers, is_final=True)
    
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"Done! Processed {len(papers)} papers in {total_time/60:.1f} minutes")
    print(f"Average: {total_time/len(papers):.1f} seconds per paper")
    print("=" * 60)


if __name__ == "__main__":
    main()
