#!/usr/bin/env python3
"""
Validate anonymization approach by creating a sample test PDF.
"""

import fitz


def create_test_pdf():
    """Create a test PDF with known content to validate our approach."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # A4 page

    # Add a title at the top
    page.insert_text(
        fitz.Point(50, 50),
        "Strategy Science 2026 Paper Submission",
        fontsize=16,
        fontname="helvetica",
    )

    # Add author information section
    author_section_y = 150
    page.insert_text(
        fitz.Point(50, author_section_y),
        """
Author Information Section
=============================
Name: John Doe
Email: john.doe@university.edu
Institution: Example University
Department: Management

Correspondence to:
John Doe
Department of Management
Example University
123 University Street
City, State 12345

Acknowledgments
This research was supported by Grant #12345.
We thank the reviewers for their valuable feedback.
""",
        fontsize=10,
        fontname="helvetica",
    )

    # Add abstract
    abstract_y = author_section_y + 80
    page.insert_text(
        fitz.Point(50, abstract_y),
        """
Abstract
This paper examines the relationship between organizational strategy and firm performance in dynamic markets. We develop a theoretical model that demonstrates how firms can leverage dynamic capabilities to achieve sustainable competitive advantage. Our analysis of 500 firms across 10 industries provides empirical evidence supporting our theoretical framework. The findings suggest that dynamic capabilities are more important than static resources in rapidly changing environments.

Keywords: strategy, dynamic capabilities, competitive advantage, organizational theory, empirical analysis
""",
        fontsize=10,
        fontname="helvetica",
    )

    # Add some footnotes
    footnote_y = abstract_y + 200
    page.insert_text(
        fitz.Point(50, footnote_y),
        """
Footnotes
1. Data available from: Compustat database
2. Author contact: john.doe@university.edu
3. Funding: National Science Foundation #NSF-2023-4567
""",
        fontsize=9,
        fontname="helvetica",
    )

    doc.save("test_validation.pdf")
    doc.close()
    print("✅ Created test_validation.pdf")


def test_our_approach():
    """Test our conservative approach on the validation PDF."""
    print("🧪 Testing conservative approach on validation PDF...")

    try:
        doc = fitz.open("test_validation.pdf")
        page = doc[0]

        # Conservative approach: Only remove specific terms
        terms_to_redact = ["John Doe", "john.doe@university.edu", "Example University"]

        for term in terms_to_redact:
            quads = page.search_for(term)
            for quad in quads:
                page.add_redact_annot(quad)

        # Remove footnote section entirely
        footnote_instances = page.search_for("Footnotes")
        for quad in footnote_instances:
            # Get the rectangle for the entire footnote section
            if footnote_instances:
                rect = fitz.Rect(0, footnote_instances[0].y0 - 10, page.rect.width, 200)
                page.add_redact_annot(rect, fill=(1, 1, 1))

        page.apply_redactions()

        doc.save("test_validation_result.pdf")
        doc.close()

        # Verify
        result_doc = fitz.open("test_validation_result.pdf")
        result_text = result_doc[0].get_text()

        # Check if abstract is preserved
        abstract_preserved = "This paper examines the relationship" in result_text
        author_removed = "John Doe" not in result_text
        footnote_removed = "Footnotes" not in result_text

        print(f"✅ Abstract preserved: {abstract_preserved}")
        print(f"✅ Author info removed: {author_removed}")
        print(f"✅ Footnote section removed: {footnote_removed}")

        if abstract_preserved and author_removed and footnote_removed:
            print("✅ Conservative approach works correctly!")
        else:
            print("⚠ Conservative approach needs adjustment")

        result_doc.close()

    except Exception as e:
        print(f"❌ Error during validation: {e}")


def main():
    create_test_pdf()
    test_our_approach()


if __name__ == "__main__":
    main()
