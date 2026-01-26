#!/usr/bin/env python3
"""
Test Anonymization on a single PDF with conservative approach.
"""

import os
import fitz


def test_conservative_anonymization():
    """Test conservative anonymization on a sample file."""
    # Choose a sample file to test with
    test_file = "R_5E6RBB51X4tquOZ.pdf"  # One of the first files
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return

    output_file = "test_conservative_anon.pdf"

    print(f"🔬 Testing conservative anonymization on: {test_file}")

    try:
        doc = fitz.open(test_file)

        # Strategy 1: Redact specific identified terms ONLY
        # (No aggressive wiping - just targeted redaction)

        terms_to_remove = [
            "Kunyuan Qiao",
            "k.qiao@northeastern.edu",
            "Northeastern University",
        ]

        # Process first page only
        page = doc[0]

        # Redact specific terms
        for term in terms_to_remove:
            quads = page.search_for(term)
            for quad in quads:
                page.add_redact_annot(quad)

        # Also redact common footnote patterns
        footnote_patterns = [
            "Correspondence:",
            "Contact:",
            "Email:",
            "Phone:",
            "Address:",
            "University",
            "Department",
            "Acknowledg",
        ]

        text = page.get_text()
        lines = text.split("\n")

        # Find lines with footnote indicators and redact them
        for i, line in enumerate(lines):
            if any(pattern.lower() in line.lower() for pattern in footnote_patterns):
                # Get the line's position
                instances = page.search_for(line)
                for inst in instances:
                    # Redact entire line
                    rect = fitz.Rect(0, inst[0].y0 - 2, page.rect.width, 15)
                    page.add_redact_annot(rect, fill=(1, 1, 1))

        page.apply_redactions()

        # Save
        doc.save(output_file)
        doc.close()

        print(f"✅ Saved test to: {output_file}")

        # Quick verification
        new_doc = fitz.open(output_file)
        new_text = new_doc[0].get_text()

        # Check if removed terms still exist
        terms_remaining = [
            term for term in terms_to_remove if term.lower() in new_text.lower()
        ]

        if terms_remaining:
            print(f"⚠ Warning: Terms still found: {terms_remaining}")
        else:
            print("✅ All test terms successfully removed")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_conservative_anonymization()
