#!/usr/bin/env python3
"""
Re-extract keywords for papers that have bad keywords (thinking text)
"""

import os
import csv
import re
import tempfile
import requests

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

INPUT_CSV = "papers_import.csv"
OUTPUT_CSV = "papers_import.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"  # Better model with thinking mode


def extract_abstract_from_text(full_text):
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


def extract_text_from_pdf(pdf_path, max_pages=2):
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


def parse_keywords_from_llm_output(raw_output):
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


def extract_keywords_with_llm(text, title):
    """Use Ollama + Qwen3 to extract keywords from paper abstract."""
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

            # qwen3 puts reasoning in 'thinking' field, answer in 'response' field
            raw_answer = result.get('response', '').strip()
            thinking = result.get('thinking', '').strip()

            # Debug: print what we got from LLM
            if not raw_answer and not thinking:
                print(f"       ⚠ LLM returned empty response")
                return ""

            # Parse to extract clean keywords from response (not thinking)
            keywords = parse_keywords_from_llm_output(raw_answer)

            # If parsing failed, show what we got for debugging
            if not keywords and raw_answer:
                print(f"       DEBUG: Raw answer = {raw_answer[:100]}")

            return keywords
        else:
            return ""
    except Exception as e:
        print(f"       ⚠ LLM error: {e}")
        return ""


def needs_fixing(keywords):
    """Check if keywords need to be re-extracted."""
    # Re-extract all to get better method classification
    return True

def is_valid_keywords(keywords):
    """Check if extracted keywords are valid."""
    if not keywords or len(keywords.strip()) == 0:
        return False
    # Should start with a method
    kw_lower = keywords.lower()
    if not (kw_lower.startswith('qualitative') or kw_lower.startswith('quantitative') or
            kw_lower.startswith('mixed') or kw_lower.startswith('conceptual')):
        return False
    return True


def download_pdf_from_link(url):
    """Download PDF from Dropbox shared link."""
    # Convert dl=0 to dl=1 for direct download
    download_url = url.replace('?dl=0', '?dl=1').replace('&dl=0', '&dl=1')
    try:
        response = requests.get(download_url, timeout=60)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"       ⚠ Download error: {e}")
    return None


def main():
    print("🔧 Re-extracting keywords with qwen3:8b...\n")

    # Read CSV
    papers = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        papers = list(reader)

    # Find papers that need fixing
    to_fix = [p for p in papers if needs_fixing(p['keywords'])]
    print(f"Found {len(to_fix)} papers to re-extract\n")

    # Fix each paper
    fixed_count = 0
    for paper in to_fix:
        print(f"[{paper['id']}] {paper['title'][:50]}...")

        if not paper.get('link'):
            print(f"       ⚠ No link available")
            continue

        try:
            # Download PDF from shared link
            pdf_content = download_pdf_from_link(paper['link'])
            if not pdf_content:
                print(f"       ⚠ Failed to download PDF")
                continue

            # Save to temp file and extract text
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_content)
                tmp_path = tmp.name

            text = extract_text_from_pdf(tmp_path)
            os.unlink(tmp_path)

            if text:
                keywords = extract_keywords_with_llm(text, paper['title'])
                if keywords and is_valid_keywords(keywords):
                    paper['keywords'] = keywords
                    print(f"       ✓ {keywords[:60]}...")
                    fixed_count += 1
                else:
                    print(f"       ○ Still no keywords")
            else:
                print(f"       ⚠ No text extracted")
        except Exception as e:
            print(f"       ⚠ Error: {e}")

    # Write updated CSV
    fieldnames = ['id', 'title', 'link', 'keywords', 'original_filename']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)

    print(f"\n✓ Fixed {fixed_count}/{len(to_fix)} papers")


if __name__ == "__main__":
    main()
