#!/usr/bin/env python3
"""
Test improved title and abstract extraction
"""

import sys
sys.path.insert(0, '/Volumes/ORICO/Documents/CodingProject/Review')

from process_papers import extract_title_from_pdf, extract_abstract_from_pdf

pdf_path = "/Users/yupengliu/Library/CloudStorage/Dropbox/StrategyScience2026/17 - Cardon et al. 2009.pdf"

print("=" * 60)
print("TITLE EXTRACTION:")
print("=" * 60)
title = extract_title_from_pdf(pdf_path)
print(f"Title: {title}")
print(f"Length: {len(title)} chars")

print("\n" + "=" * 60)
print("ABSTRACT EXTRACTION:")
print("=" * 60)
abstract = extract_abstract_from_pdf(pdf_path)
print(f"Abstract: {abstract[:500]}...")
print(f"Length: {len(abstract)} chars")
