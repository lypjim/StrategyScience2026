#!/usr/bin/env python3
"""
Clean up keywords in papers_import.csv by removing LLM thinking text
"""

import csv
import re

INPUT_CSV = "papers_import.csv"
OUTPUT_CSV = "papers_import.csv"

def clean_keywords(keywords_text):
    """Extract clean keywords from LLM output that may contain thinking text."""
    if not keywords_text or len(keywords_text.strip()) == 0:
        return ""

    # If it starts with thinking text, try to extract keywords from later in the text
    if keywords_text.startswith("Okay,") or keywords_text.startswith("Keywords:"):
        # Look for patterns like "Keywords: actual, keywords, here"
        match = re.search(r'Keywords:\s*([^\n]+)', keywords_text)
        if match:
            keywords_text = match.group(1).strip()
        else:
            # If no "Keywords:" found, try to find comma-separated words after the thinking
            # Look for the last line or a pattern of comma-separated lowercase words
            lines = keywords_text.split('\n')
            for line in reversed(lines):
                # Check if line looks like keywords (has commas, not too long)
                if ',' in line and len(line) < 300 and not line.startswith('Okay'):
                    keywords_text = line.strip()
                    break
            else:
                # If still nothing found, return empty
                return ""

    # Remove common prefixes
    keywords_text = re.sub(r'^Keywords:\s*', '', keywords_text, flags=re.IGNORECASE)

    # Remove quotes
    keywords_text = keywords_text.replace('"', '').replace("'", '')

    # Take only first line if multiple lines
    keywords_text = keywords_text.split('\n')[0].strip()

    # If still looks like thinking text (very long or starts with "Okay"), return empty
    if len(keywords_text) > 250 or keywords_text.startswith('Okay'):
        return ""

    return keywords_text[:200]


def main():
    papers = []

    # Read CSV
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['keywords'] = clean_keywords(row['keywords'])
            papers.append(row)

    # Write cleaned CSV
    fieldnames = ['id', 'title', 'link', 'keywords', 'original_filename']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)

    print(f"✓ Cleaned {len(papers)} papers")
    print("\nSample cleaned keywords:")
    for paper in papers[:5]:
        print(f"  {paper['id']}: {paper['keywords'][:80]}{'...' if len(paper['keywords']) > 80 else ''}")


if __name__ == "__main__":
    main()
