#!/usr/bin/env python3
"""
Helper to extract just the abstract from a PDF
"""
import re

def extract_abstract_from_text(full_text):
    """
    Extract just the abstract section from paper text.
    Returns abstract text or first ~800 chars if no abstract found.
    """
    # Look for abstract section
    # Common patterns: "Abstract", "ABSTRACT", "Abstract."
    abstract_patterns = [
        r'Abstract[:\.\s]+(.*?)(?=\n\s*\n|\nIntroduction|\n1\.|\nKeywords:|\nJEL)',
        r'ABSTRACT[:\.\s]+(.*?)(?=\n\s*\n|\nINTRODUCTION|\n1\.|\nKEYWORDS:)',
        r'abstract[:\.\s]+(.*?)(?=\n\s*\n|\nintroduction|\n1\.|\nkeywords:)',
    ]

    for pattern in abstract_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # Clean up: remove excessive whitespace
            abstract = re.sub(r'\s+', ' ', abstract)
            # Limit to reasonable length (~500 words ≈ 3500 chars)
            if 100 < len(abstract) < 5000:
                return abstract[:3500]

    # Fallback: if no abstract found, take first chunk after title
    # Skip first 200 chars (usually title/author info)
    fallback = full_text[200:3700]
    fallback = re.sub(r'\s+', ' ', fallback).strip()
    return fallback
