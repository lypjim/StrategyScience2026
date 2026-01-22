#!/usr/bin/env python3
"""
Compare qwen2.5:7b vs qwen3:8b keyword extraction on sample papers
"""

import csv
import re
import os
import tempfile
import requests

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("pdfplumber not installed")
    exit(1)

OLLAMA_URL = "http://localhost:11434/api/generate"
SAMPLE_IDS = ['P001', 'P008', 'P013', 'P019']  # Mix of quantitative, qualitative, conceptual


def extract_abstract_from_text(full_text):
    """Extract abstract section."""
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
    """Extract text from PDF."""
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text[:3000]
    except Exception as e:
        return ""


def extract_keywords(text, title, model):
    """Extract keywords using specified model."""
    if not text:
        return ""

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
                "model": model,
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
            raw_answer = result.get('response', '').strip()

            # Parse keywords
            method_pattern = r'(qualitative|quantitative|mixed|conceptual)[,\s]+([a-zA-Z0-9][a-zA-Z0-9\s,\-_]+)'
            match = re.search(method_pattern, raw_answer, re.IGNORECASE)
            if match:
                keywords = match.group(0).strip()
                keywords = re.sub(r'\s+', ' ', keywords)
                keywords = keywords.split('\n')[0]
                if len(keywords) < 250:
                    return keywords[:200]

            # Handle "method, ..." format
            if raw_answer.lower().startswith('method,'):
                keywords_part = raw_answer[7:].strip().split('\n')[0]
                kw_lower = keywords_part.lower()
                if any(word in kw_lower for word in ['quantitative', 'empirical', 'data', 'experiment', 'patent', 'evidence']):
                    return f"quantitative, {keywords_part}"[:200]
                elif any(word in kw_lower for word in ['theory', 'theoretical', 'framework', 'view', 'conceptual']):
                    return f"conceptual, {keywords_part}"[:200]
                elif any(word in kw_lower for word in ['qualitative', 'case', 'interview']):
                    return f"qualitative, {keywords_part}"[:200]

            return ""
        else:
            return ""
    except Exception as e:
        print(f"Error with {model}: {e}")
        return ""


def download_pdf(url):
    """Download PDF from shared link."""
    download_url = url.replace('?dl=0', '?dl=1').replace('&dl=0', '&dl=1')
    try:
        response = requests.get(download_url, timeout=60)
        if response.status_code == 200:
            return response.content
    except:
        pass
    return None


def main():
    print("=" * 80)
    print("QWEN2.5:7B vs QWEN3:8B COMPARISON")
    print("=" * 80)

    # Read papers
    papers = {}
    with open('papers_import.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] in SAMPLE_IDS:
                papers[row['id']] = row

    for paper_id in SAMPLE_IDS:
        if paper_id not in papers:
            continue

        paper = papers[paper_id]
        print(f"\n[{paper_id}] {paper['title'][:60]}...")

        # Download PDF
        pdf_content = download_pdf(paper['link'])
        if not pdf_content:
            print("  ✗ Failed to download")
            continue

        # Extract text
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name

        text = extract_text_from_pdf(tmp_path)
        os.unlink(tmp_path)

        if not text:
            print("  ✗ No text extracted")
            continue

        # Extract with both models
        print("\n  Extracting with qwen2.5:7b...")
        keywords_25 = extract_keywords(text, paper['title'], "qwen2.5:7b")
        print(f"  ├─ {keywords_25}")

        print("\n  Extracting with qwen3:8b...")
        keywords_3 = extract_keywords(text, paper['title'], "qwen3:8b")
        print(f"  └─ {keywords_3}")

        # Compare
        if keywords_25 and keywords_3:
            method_25 = keywords_25.split(',')[0].strip()
            method_3 = keywords_3.split(',')[0].strip()

            if method_25.lower() == method_3.lower():
                print(f"\n  ✓ Same method: {method_25}")
            else:
                print(f"\n  ⚠ Different methods: {method_25} vs {method_3}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
