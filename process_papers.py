#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - Paper Processing Script V2

Enhanced version with:
- Anonymized titles (author names removed)
- Keyword extraction from PDFs
- Theory, method, and topic detection
"""

import os
import re
import csv
import tempfile
import dropbox
from dropbox.exceptions import ApiError

# Try to import pdfplumber for keyword extraction
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: pdfplumber not installed. Keyword extraction disabled.")

# =====================
# CONFIGURATION
# =====================
DROPBOX_ACCESS_TOKEN = "sl.u.AGS9Kxuqm2kQoJJGqjG5wFz4cSBtGDeNo-WngAzC2VfSAPYp4Vnt2H6YfzI-Tp2XLAqQ7lbiVMWubqQUc6qOyICxa5JvMsRnT82P-aGNLw3FPriY1gnH-aLA55Uc_xsIMuC8c8nlxJ7120Vln5jb1fx-bkMi7hCcw1dSXbdgLruKY3qesgCT_20vYxIFL8WOcVo03O5JRpBZqgOJjy-Wriwr_H2bfKk5Gbirh6XggPWpeN9716qYFxUB6vOVslI2fMJKR48aSaOISZJdCm2fGMMlqey4xOSj1Jk6wVuC2KvpulZbh-cPuznQ1kb4seH2syC_cfisBH5Eiebf_Zqulz02iOqv70Aq30iinX7kFgx4T3ajqaTIhKiufWSv34ShxO_pkPym79dRWYY6_ynVG54H6ngLoO06M9_7oTJvhTRPJVddtjdomEq-7Xz1SWciwICvEP7B-hiBgTleJZ6NuFQaSxlBifOOXljRzk9nFrizddA-Ct6hmdWIQuekkyG23WvWmUN_SFb5jKgUj4J3DTmdmli6JnpTFnBQ5BKKi11xq9g9XBuZ3nYttMcu_hw0DSFaLgpWVw2K8QGXzGfVUOFYdOK0kbqBfnvZ-zEtBfR0fCeR7UnRqrDZAp_JcREfonaBQLVr2fPpN7b2i7F8guUibaiBysvSVeGOUlydenbiFdlD1SL7QmLP5HhdRVlEMX5T9uWFmxByp-N5rJ15bCkvkjpXcZTzrqCTA4KL2kiLpqkiO6EC2FqrtwUle4fKlXSRyaU9ucQD_RNQVMlBCbbd2ff-95hASE982dDpcTGQlyUHmfg3RynJ9AKlpe_Vds-wJi9XP7ORE-fr8jsBUj1SDpNEpbVpJALoVLUiJ7X_LL7vx90vctGgF4_p_fUbMta3Zrj_sL3zV67UM6JPQ_apIj8hWZoaw-1PS2Hv7NY-zhRPeV1TmxJzhlWvQ5klLz0EHzoKo8vl1FgpJ9GU7y23Owmwm-pLgF4LceuTfva_DY2ozReIW7rfJJMzUvx2UDlBFmSc1ZCQa2AcooWNtHQ5LkQBfUzlNQth0v141MKOT9O6xqpNrISlQlB3LKxS4keonlknwok2TmYr2bVmu-WNCizCy0rMllBeCBmLnqqTFfsumQmUVMtH6tN0ZTZ51dwALCf1wwS9_QF3h5dWO1A7IkoXHKP5WG3OGb8m6kyxelZQJO7gAxmM1mNhXtlpk3zp8RZw8k_-iLTh7uZHcGVEZrYjIxImv2-MTw8bV5SMcKO98mN7vV55jBJLSmjbFWU"

DROPBOX_FOLDER = "/StrategyScience2026"
OUTPUT_CSV = "papers_import.csv"

# Common theory keywords to look for
THEORY_KEYWORDS = [
    "resource-based view", "dynamic capabilities", "institutional theory",
    "transaction cost", "agency theory", "stakeholder theory", "contingency theory",
    "organizational learning", "knowledge-based view", "upper echelons",
    "behavioral theory", "network theory", "evolutionary theory", "population ecology",
    "structural inertia", "absorptive capacity", "ambidexterity", "exploration",
    "exploitation", "core competence", "competitive advantage"
]

# Common method keywords
METHOD_KEYWORDS = [
    "regression", "panel data", "fixed effects", "random effects", "OLS",
    "instrumental variable", "difference-in-difference", "event study",
    "case study", "qualitative", "quantitative", "survey", "interview",
    "longitudinal", "cross-sectional", "meta-analysis", "experiment",
    "simulation", "grounded theory", "content analysis", "archival"
]

# Topic keywords
TOPIC_KEYWORDS = [
    "innovation", "M&A", "merger", "acquisition", "alliance", "strategy",
    "performance", "technology", "digital", "platform", "ecosystem",
    "diversification", "internationalization", "entrepreneurship", "startup",
    "governance", "leadership", "CEO", "board", "sustainability", "ESG",
    "disruption", "transformation", "change", "adaptation"
]


def extract_anonymous_title(filename: str) -> str:
    """
    Extract just the paper title, removing author names and year.
    
    Input:  "Benner, M. J., & Tushman, M. L. (2003). Exploitation...pdf"
    Output: "Exploitation, exploration, and process management"
    """
    # Remove .pdf extension
    name = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Pattern 1: Author(s) (Year). Title
    # Match: Author, Initials, & Author2 (YYYY). Title
    match = re.search(r'\(\d{4}\)[.\s]*(.+)$', name)
    if match:
        title = match.group(1).strip()
        # Clean up trailing punctuation
        title = re.sub(r'[-–—]\s*$', '', title).strip()
        return title[:100] if len(title) > 100 else title
    
    # Pattern 2: Author, Author, Year, Title (comma separated)
    # Match: Hannan, Freeman, 1984, Structural Inertia...
    match = re.search(r'\d{4}[,\s]+(.+)$', name)
    if match:
        title = match.group(1).strip()
        return title[:100] if len(title) > 100 else title
    
    # Pattern 3: Author Year - Title
    match = re.search(r'\d{4}\s*[-–—]\s*(.+)$', name)
    if match:
        title = match.group(1).strip()
        return title[:100] if len(title) > 100 else title
    
    # Fallback: return cleaned filename (may still have author)
    title = name[:80]
    # Clean up any leading dashes or punctuation
    title = re.sub(r'^[-–—\s]+', '', title)
    return title


def extract_keywords_from_pdf(pdf_path: str) -> dict:
    """
    Extract keywords from PDF by:
    1. Looking for explicit "Keywords:" section
    2. Matching against known theory/method/topic keywords
    """
    result = {
        'keywords': '',
        'theory': '',
        'method': '',
        'topics': ''
    }
    
    if not PDF_SUPPORT:
        return result
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extract text from first 3 pages (abstract + intro usually)
            text = ""
            for i, page in enumerate(pdf.pages[:3]):
                page_text = page.extract_text()
                if page_text:
                    text += page_text.lower() + " "
            
            # Look for explicit keywords section
            kw_match = re.search(r'keywords?[:\s]+([^\n]+)', text, re.IGNORECASE)
            if kw_match:
                result['keywords'] = kw_match.group(1).strip()[:200]
            
            # Find matching theory keywords
            found_theories = []
            for kw in THEORY_KEYWORDS:
                if kw.lower() in text:
                    found_theories.append(kw)
            result['theory'] = '; '.join(found_theories[:3])  # Top 3
            
            # Find matching method keywords
            found_methods = []
            for kw in METHOD_KEYWORDS:
                if kw.lower() in text:
                    found_methods.append(kw)
            result['method'] = '; '.join(found_methods[:3])
            
            # Find matching topic keywords
            found_topics = []
            for kw in TOPIC_KEYWORDS:
                if kw.lower() in text:
                    found_topics.append(kw)
            result['topics'] = '; '.join(found_topics[:3])
            
    except Exception as e:
        print(f"       ⚠ PDF parse error: {e}")
    
    return result


def get_shared_link(dbx: dropbox.Dropbox, path: str) -> str:
    """Get or create a shareable link for a file."""
    try:
        shared_link = dbx.sharing_create_shared_link_with_settings(path)
        return shared_link.url.replace("?dl=0", "?dl=1")
    except ApiError as e:
        if e.error.is_shared_link_already_exists():
            links = dbx.sharing_list_shared_links(path=path, direct_only=True)
            if links.links:
                return links.links[0].url.replace("?dl=0", "?dl=1")
        raise e


def main():
    print("=" * 60)
    print("Strategy Science Conference 2026 - Paper Processor V2")
    print("=" * 60)
    print("Features: Anonymized titles, keyword extraction")
    
    # Initialize Dropbox client
    print("\n📁 Connecting to Dropbox...")
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    
    try:
        account = dbx.users_get_current_account()
        print(f"✓ Connected as: {account.name.display_name}")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # List files
    print(f"\n📄 Scanning folder: {DROPBOX_FOLDER}")
    try:
        result = dbx.files_list_folder(DROPBOX_FOLDER)
        files = [entry for entry in result.entries if entry.name.lower().endswith('.pdf')]
    except ApiError as e:
        print(f"✗ Error: {e}")
        return
    
    print(f"✓ Found {len(files)} PDF files")
    if PDF_SUPPORT:
        print("✓ PDF keyword extraction enabled")
    else:
        print("⚠ PDF keyword extraction disabled (install pdfplumber)")
    print()
    
    # Process each file
    papers = []
    for i, file_entry in enumerate(sorted(files, key=lambda x: x.name)):
        paper_id = f"P{str(i + 1).zfill(3)}"
        filename = file_entry.name
        
        # Anonymized title
        title = extract_anonymous_title(filename)
        print(f"[{paper_id}] {title[:50]}...")
        
        # Get shareable link
        try:
            link = get_shared_link(dbx, file_entry.path_display)
            print(f"       ✓ Link generated")
        except Exception as e:
            print(f"       ✗ Link failed: {e}")
            link = ""
        
        # Extract keywords from PDF
        keywords = {'keywords': '', 'theory': '', 'method': '', 'topics': ''}
        if PDF_SUPPORT and link:
            print(f"       ⏳ Extracting keywords...")
            try:
                # Download PDF to temp file
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    _, response = dbx.files_download(file_entry.path_display)
                    tmp.write(response.content)
                    tmp_path = tmp.name
                
                keywords = extract_keywords_from_pdf(tmp_path)
                os.unlink(tmp_path)  # Clean up
                
                if keywords['theory'] or keywords['method'] or keywords['topics']:
                    print(f"       ✓ Keywords found")
                else:
                    print(f"       ○ No keywords matched")
            except Exception as e:
                print(f"       ⚠ Keyword extraction failed: {e}")
        
        papers.append({
            'id': paper_id,
            'title': title,
            'link': link,
            'keywords': keywords.get('keywords', ''),
            'theory': keywords.get('theory', ''),
            'method': keywords.get('method', ''),
            'topics': keywords.get('topics', ''),
            'original_filename': filename
        })
    
    # Write CSV
    print(f"\n📝 Writing {OUTPUT_CSV}...")
    fieldnames = ['id', 'title', 'link', 'keywords', 'theory', 'method', 'topics', 'original_filename']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)
    
    print(f"✓ Saved {len(papers)} papers to {OUTPUT_CSV}")
    print("\n" + "=" * 60)
    print("Done! Titles are now anonymized (no author names).")
    print("=" * 60)


if __name__ == "__main__":
    main()
