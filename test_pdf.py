#!/usr/bin/env python3
"""
Test script to examine PDF structure and improve extraction
"""

import pdfplumber
import re

# Test with one paper
pdf_path = "/Users/yupengliu/Library/CloudStorage/Dropbox/StrategyScience2026/17 - Cardon et al. 2009.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print("=" * 60)
    print("PAGE 1:")
    print("=" * 60)
    page1 = pdf.pages[0].extract_text()
    print(page1[:2000])
    
    print("\n" + "=" * 60)
    print("PAGE 2:")
    print("=" * 60)
    page2 = pdf.pages[1].extract_text()
    print(page2[:2000])
    
    print("\n" + "=" * 60)
    print("PAGE 3:")
    print("=" * 60)
    if len(pdf.pages) > 2:
        page3 = pdf.pages[2].extract_text()
        print(page3[:2000])
