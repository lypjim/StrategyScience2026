#!/usr/bin/env python3
import pdfplumber
import re

pdf_path = "/Users/yupengliu/Library/CloudStorage/Dropbox/StrategyScience2026/17 - Cardon et al. 2009.pdf"

with pdfplumber.open(pdf_path) as pdf:
    full_text = ""
    for page_num in range(min(3, len(pdf.pages))):
        page_text = pdf.pages[page_num].extract_text()
        if page_text:
            full_text += page_text + "\n"
    
    full_text = re.sub(r'\s+', ' ', full_text)
    lines = full_text.split('.')
    
    found_university = False
    for i, sentence in enumerate(lines[:50]):
        if 'university' in sentence.lower() or 'college' in sentence.lower():
            found_university = True
            print(f"[{i}] UNIVERSITY FOUND")
            # Print next 5 sentences
            for j in range(i+1, min(i+6, len(lines))):
                print(f"[{j}] (len={len(lines[j].strip())}): {lines[j].strip()[:150]}")
            break
