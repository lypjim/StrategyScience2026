#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - Paper Processing Script V3

Enhanced version with:
- Anonymized titles (author names removed)
- LLM-based keyword extraction using Ollama + Qwen
- Single combined keywords column
"""

import os
import re
import csv
import json
import tempfile
import requests
import dropbox
from dropbox.exceptions import ApiError

# Try to import pdfplumber for text extraction
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: pdfplumber not installed. PDF text extraction disabled.")

# =====================
# CONFIGURATION
# =====================
DROPBOX_ACCESS_TOKEN = "sl.u.AGSca_oogXOCEe0XcOpwZukt_CH7WK8XnyGxAyJWV45HxByrLJl12w_SBgkabiac5RA_coEy-J0srhHX5UEPRf8G_4Nlr3DWc8onRPfqxOKyAIpFQnGv_dWTxXaV9usIajZ2ryVGYFcXqsvXeWWMR1IP9rln7R7ePCPUeb2sbr0V2yPG7a3uvspKTU2WUxH7qv6C4Ul46qo2xuRnQnV0pSQUoFYx6p_VRN4SIDqKBYXTcWytFT9jOPm-NJv8rwOj8A8jrPz658cjKLcIoVn_hee0FanzCgWUElcu4UgXudEwB4EQciz15F6pZmnSvzSBGtLxvzfdRkI5XoVl3JzzzSuCKzu4gKHrOGdP4M1RBLkTv8SebjuzxBIDWM1EJ_pD-Jl34MbTFhIdbIMhqjcwTnjcggI8gAZMzFvbW0heh8mb07J99BEeDbUFTK1ifSrX1XNsafkhaddDV9VLHgEzIuA8UjMSIAf-ahjMlngb7pTLyQS_Njb8khlu5I53z-LMFUgHriOXsVnyuRHndPDfD-hT3wPODXY8LoPYwMN-9CSIEwEdZCr9SQYGbPwxuq5CjGdZdS7H64nwNPGTYEssW_6bzLZADBzo6DTV_yO0f11pP2yKywlshjEcZzV1JKQiRjelVPNbzzYrybQKYccjibT6v2hw5w371yWQa2moOeUBLZXztpl8EfhDSvhx75IOBLerUxUqK1-oTSFL6_5OxsfhTGdOud2vfU10P-GFBw90SSeAdUCZnQ5uPl12i5gvGcmy0vpYEWqpIhZ5mxkCw9eh2OSlRA5ykqg-so43EywB_kcfRcrZW5Ir2QYChdCvXqRL8z0CoM50_EUNRwW27hU67UQDMrIGRR7-Ax0yu9vwJDeRCTuFgki0X-lunecUdIQ0f2vtJZbDdYaCdvSD91Tl5pp1P9shx-Dj4MBA_l3NEzfG887Np-4wRGSFS8tTkkisY_nk1eeiXDy-8BcS3NSkRvzjRltnsqZ3RIGZ8SoMsR65pCMURzoGKqm8uq5kV624_bOc9qvVd8H1z9vz0YO8kzIn7aGxUCjGsiHpax5akbBeaJ9eUvVMygrHGMJonZYq-t9X1Ubtz9OfnrV2ckkWFDcTjvu01hxFsGUiQkqGyScByWsNiVzNex8Ws9-O-HtdAbVQ7egQ32SycgXvo86FQOmIA4IPOK6_eQkrCInO1-ToMP0CXgrrwpLLxw1nI3f5qAn1TYI3U2Qf2BS-GDWilzUTJvwCW7bjTVkttmqv3cvpmb1lUbsU7q3pXe03rqA"

DROPBOX_FOLDER = "/StrategyScience2026"
OUTPUT_CSV = "papers_import.csv"

# Ollama settings
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"  # More reliable output without thinking mode


def extract_anonymous_title(filename: str) -> str:
    """
    Extract just the paper title, removing author names and year.
    """
    name = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Pattern 1: Author(s) (Year). Title
    match = re.search(r'\(\d{4}\)[.\s]*(.+)$', name)
    if match:
        title = match.group(1).strip()
        title = re.sub(r'[-–—]\s*$', '', title).strip()
        return title[:100] if len(title) > 100 else title
    
    # Pattern 2: Author, Author, Year, Title
    match = re.search(r'\d{4}[,\s]+(.+)$', name)
    if match:
        title = match.group(1).strip()
        return title[:100] if len(title) > 100 else title
    
    # Pattern 3: Author Year - Title
    match = re.search(r'\d{4}\s*[-–—]\s*(.+)$', name)
    if match:
        title = match.group(1).strip()
        return title[:100] if len(title) > 100 else title
    
    # Fallback
    title = name[:80]
    title = re.sub(r'^[-–—\s]+', '', title)
    return title


def extract_abstract_from_text(full_text: str) -> str:
    """Extract just the abstract section from paper text."""
    # Look for abstract section with various patterns
    abstract_patterns = [
        r'Abstract[:\.\s]+(.*?)(?=\n\s*\n[A-Z]|\nIntroduction|\n1\.|\nKeywords:)',
        r'ABSTRACT[:\.\s]+(.*?)(?=\n\s*\n[A-Z]|\nINTRODUCTION|\n1\.)',
    ]

    for pattern in abstract_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            abstract = re.sub(r'\s+', ' ', abstract)
            if 100 < len(abstract) < 3000:
                return abstract[:2000]

    # Fallback: use first chunk after initial metadata
    fallback = full_text[200:1500]
    return re.sub(r'\s+', ' ', fallback).strip()


def extract_text_from_pdf(pdf_path: str, max_pages: int = 2) -> str:
    """Extract text from first 2 pages of PDF (usually contains abstract)."""
    if not PDF_SUPPORT:
        return ""

    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text[:3000]  # Get first 2 pages
    except Exception as e:
        print(f"       ⚠ PDF read error: {e}")
        return ""


def parse_keywords_from_llm_output(raw_output: str) -> str:
    """
    Parse keywords from LLM output that may contain thinking/reasoning.
    Looks for the actual keyword list in the output.
    """
    if not raw_output:
        return ""

    # Pattern 1: Look for method followed by commas (actual answer format)
    # Match patterns like "quantitative, topic1, topic2, ..." or "Quantitative, ..."
    method_pattern = r'(qualitative|quantitative|mixed|conceptual)[,\s]+([a-zA-Z0-9][a-zA-Z0-9\s,\-_]+)'
    match = re.search(method_pattern, raw_output, re.IGNORECASE)
    if match:
        keywords = match.group(0).strip()
        # Clean up and limit
        keywords = re.sub(r'\s+', ' ', keywords)
        keywords = keywords.split('\n')[0]  # First line only
        if len(keywords) < 250:
            return keywords[:200]

    # Pattern 2: Look for explicit "Keywords:" or "Answer:" label
    match = re.search(r'(Keywords|Answer):\s*([a-zA-Z][a-zA-Z0-9_,\s\-]+)', raw_output, re.IGNORECASE)
    if match:
        keywords = match.group(2).strip()
        keywords = keywords.split('\n')[0].strip()
        if any(keywords.lower().startswith(m) for m in ['qualitative', 'quantitative', 'mixed', 'conceptual']):
            return keywords[:200]

    # Pattern 3: Last line with commas and reasonable length
    lines = [l.strip() for l in raw_output.split('\n') if l.strip()]
    for line in reversed(lines):
        if ',' in line and 50 < len(line) < 250:
            # Check if it starts with a method
            if any(line.lower().startswith(m) for m in ['qualitative', 'quantitative', 'mixed', 'conceptual']):
                return line[:200]

    return ""


def extract_keywords_with_llm(text: str, title: str) -> str:
    """
    Use Ollama + Qwen3 to extract keywords from paper abstract.
    Handles thinking mode output properly.
    """
    if not text:
        return ""

    # Extract abstract from text
    abstract = extract_abstract_from_text(text)

    prompt = f"""Classify this paper and extract keywords.

Method (choose ONE): quantitative (numbers/stats/data), qualitative (cases/interviews), mixed (both), conceptual (pure theory)

Title: {title}
Abstract: {abstract}

Output exactly in this format: method, keyword1, keyword2, keyword3, keyword4, keyword5

Answer:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 400
                }
            },
            timeout=90
        )

        if response.status_code == 200:
            result = response.json()

            # qwen2.5 puts answer directly in 'response' field
            raw_answer = result.get('response', '').strip()

            # Parse to extract clean keywords
            keywords = parse_keywords_from_llm_output(raw_answer)
            return keywords
        else:
            print(f"       ⚠ Ollama error: {response.status_code}")
            return ""
    except requests.exceptions.ConnectionError:
        print("       ⚠ Ollama not running (start with: ollama serve)")
        return ""
    except Exception as e:
        print(f"       ⚠ LLM error: {e}")
        return ""


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
    """Check if Ollama is running and the model is available."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            # Check if qwen3:8b or similar is available
            for name in model_names:
                if 'qwen' in name.lower():
                    return True
            print(f"⚠ Qwen model not found. Available: {model_names}")
            print("  Run: ollama pull qwen3:8b")
            return False
    except:
        print("⚠ Ollama not running. Start with: ollama serve")
        return False
    return False


def main():
    print("=" * 60)
    print("Strategy Science Conference 2026 - Paper Processor V3")
    print("=" * 60)
    print("Features: Anonymized titles, LLM keyword extraction (Qwen)")
    
    # Check Ollama
    print("\n🤖 Checking Ollama...")
    llm_available = check_ollama_available()
    if llm_available:
        print("✓ Ollama + Qwen ready")
    else:
        print("⚠ LLM extraction disabled (falling back to no keywords)")
    
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
        
        # Anonymized title
        title = extract_anonymous_title(filename)
        print(f"[{paper_id}] {title[:50]}...")
        
        # Get shareable link
        try:
            link = get_shared_link(dbx, file_entry.path_display)
            print(f"       ✓ Link generated")
        except Exception as e:
            print(f"       ✗ Link failed: {e}")
            link = ""
        
        # Extract keywords using LLM
        keywords = ""
        text = ""
        if llm_available and PDF_SUPPORT:
            try:
                # Download PDF to temp file
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    _, response = dbx.files_download(file_entry.path_display)
                    tmp.write(response.content)
                    tmp_path = tmp.name
                
                # Extract text
                text = extract_text_from_pdf(tmp_path)
                os.unlink(tmp_path)
                
                if text:
                    print(f"       ⏳ Extracting keywords with Qwen...")
                    keywords = extract_keywords_with_llm(text, title)
                    if keywords:
                        print(f"       ✓ Keywords: {keywords[:50]}...")
                    else:
                        print(f"       ○ No keywords extracted")
            except Exception as e:
                print(f"       ⚠ Error: {e}")
        
        papers.append({
            'id': paper_id,
            'title': title,
            'link': link,
            'keywords': keywords,
            'abstract': extract_abstract_from_text(text) if llm_available and PDF_SUPPORT and text else "",
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
    print("Done! Titles anonymized, keywords extracted with LLM.")
    print("=" * 60)


if __name__ == "__main__":
    main()
