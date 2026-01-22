#!/usr/bin/env python3
"""Test V4 LLM extraction on one paper"""

import sys
sys.path.insert(0, '/Volumes/ORICO/Documents/CodingProject/Review')

from process_papers import extract_text_from_pdf, extract_paper_info

pdf_path = "/Users/yupengliu/Library/CloudStorage/Dropbox/StrategyScience2026/17 - Cardon et al. 2009.pdf"
filename = "17 - Cardon et al. 2009.pdf"

print("Extracting text...")
text = extract_text_from_pdf(pdf_path)
print(f"Got {len(text)} chars\n")

print("Querying LLM...")
info = extract_paper_info(text, filename)

print("=" * 60)
print(f"TITLE: {info['title']}")
print("=" * 60)
print(f"ABSTRACT: {info['abstract'][:300]}...")
print("=" * 60)
print(f"KEYWORDS: {info['keywords']}")
print("=" * 60)
