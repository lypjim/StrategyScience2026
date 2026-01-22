#!/usr/bin/env python3
"""
Fix the two papers with placeholder keywords
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
OLLAMA_MODEL = "qwen3:8b"


def extract_abstract_from_text(full_text):
    """Extract just the abstract section from paper text."""
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

    fallback = full_text[200:1500]
    return re.sub(r'\s+', ' ', fallback).strip()


def extract_text_from_pdf(pdf_path, max_pages=2):
    """Extract text from first 2 pages of PDF."""
    if not PDF_SUPPORT:
        return ""

    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text[:3000]
    except Exception as e:
        print(f"       ⚠ PDF read error: {e}")
        return ""


def extract_keywords_with_llm(text, title):
    """Extract keywords with improved prompt to avoid placeholders."""
    if not text:
        return ""

    abstract = extract_abstract_from_text(text)

    # More explicit prompt to avoid placeholder output
    prompt = f"""Based on this academic paper, classify its research method and extract key topics.

Title: {title}
Abstract: {abstract}

Task:
1. Identify the research method: quantitative (uses numbers/statistics/data analysis), qualitative (case studies/interviews), conceptual (pure theory/framework), or mixed
2. Extract 5-6 main topics/themes from the abstract

Output format (replace with actual values, do NOT use placeholders):
[method], [actual topic 1], [actual topic 2], [actual topic 3], [actual topic 4], [actual topic 5]

Answer:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 300
                }
            },
            timeout=90
        )

        if response.status_code == 200:
            result = response.json()
            raw_answer = result.get('response', '').strip()

            print(f"       DEBUG: {raw_answer[:150]}")

            # Simple cleaning
            if ',' in raw_answer:
                keywords = raw_answer.split('\n')[0].strip()
                keywords = re.sub(r'\s+', ' ', keywords)

                # Check if it has placeholders
                if 'keyword1' in keywords.lower() or '[' in keywords:
                    print(f"       ⚠ Still got placeholders: {keywords[:60]}")
                    return ""

                return keywords[:200]

            return ""
        else:
            return ""
    except Exception as e:
        print(f"       ⚠ LLM error: {e}")
        return ""


def download_pdf_from_link(url):
    """Download PDF from Dropbox shared link."""
    download_url = url.replace('?dl=0', '?dl=1').replace('&dl=0', '&dl=1')
    try:
        response = requests.get(download_url, timeout=60)
        if response.status_code == 200:
            return response.content
    except Exception as e:
        print(f"       ⚠ Download error: {e}")
    return None


def main():
    print("🔧 Fixing P011 and P021 with placeholder keywords...\n")

    papers = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        papers = list(reader)

    target_ids = ['P011', 'P021']
    fixed_count = 0

    for paper in papers:
        if paper['id'] not in target_ids:
            continue

        print(f"[{paper['id']}] {paper['title'][:50]}...")

        if not paper.get('link'):
            print(f"       ⚠ No link available")
            continue

        try:
            pdf_content = download_pdf_from_link(paper['link'])
            if not pdf_content:
                print(f"       ⚠ Failed to download PDF")
                continue

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_content)
                tmp_path = tmp.name

            text = extract_text_from_pdf(tmp_path)
            os.unlink(tmp_path)

            if text:
                keywords = extract_keywords_with_llm(text, paper['title'])
                if keywords and len(keywords) > 20:
                    paper['keywords'] = keywords
                    print(f"       ✓ {keywords}")
                    fixed_count += 1
                else:
                    print(f"       ○ No valid keywords extracted")
        except Exception as e:
            print(f"       ⚠ Error: {e}")

    # Write updated CSV
    fieldnames = ['id', 'title', 'link', 'keywords', 'original_filename']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)

    print(f"\n✓ Fixed {fixed_count}/2 papers")


if __name__ == "__main__":
    main()
