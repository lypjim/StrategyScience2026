#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - Reviewer Assignment Script V2

KEYWORD-BASED MATCHING with Firebase integration:
1. Reads reviewer data (including capacity) from Firebase
2. Uses pairwise keyword similarity scoring (no LLM needed)
3. Filters by method match + capacity availability
4. Assigns 2 reviewers per paper with load balancing
"""

import csv
import json
import re
import requests
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
import time

# =====================
# CONFIGURATION
# =====================
INPUT_CSV = "papers_import.csv"
OUTPUT_CSV = "assignments.csv"
TEST_MODE = None  # Set to a number to limit papers, or None for all

# Firebase Configuration
FIREBASE_DB_URL = "https://strategyscience2026-default-rtdb.firebaseio.com"

# Fallback reviewer expertise data (used when Firebase lacks expertise field)
FALLBACK_REVIEWERS = {
    "Janet Bercovitz": {"method": "Quantitative", "keywords": ["Transaction Cost Economics", "Org. Learning", "Academic Entrepreneurship", "Tech Transfer"]},
    "Janet Lee Elsie Bercovitz": {"method": "Quantitative", "keywords": ["Transaction Cost Economics", "Org. Learning", "Academic Entrepreneurship", "Tech Transfer"]},
    "Danielle Bovenberg": {"method": "Qualitative", "keywords": ["Craft Knowledge", "Org. Theory", "Innovation", "Knowledge Diffusion"]},
    "Mukund Chari": {"method": "Quantitative", "keywords": ["Transaction Cost Economics", "Agency Theory", "Intellectual Property", "Patent Systems"]},
    "Ashton Hawk": {"method": "Quantitative", "keywords": ["Resource-Based View", "Dynamic Capabilities", "Investment Speed", "Political Capital"]},
    "Ashton Lewis Hawk": {"method": "Quantitative", "keywords": ["Resource-Based View", "Dynamic Capabilities", "Investment Speed", "Political Capital"]},
    "Sina Sokhan": {"method": "Quantitative", "keywords": ["Knowledge Recombination", "IP Theory", "Innovation Process", "Pharma Innovation"]},
    "MJ Yang": {"method": "Quant/Mixed", "keywords": ["Complementarity Theory", "RBV", "CEO Strategy", "Tech Uniqueness"]},
    "Kenneth Huang": {"method": "Quant/Mixed", "keywords": ["Institutional Theory", "Knowledge-Based View", "IP Strategy", "Innovation in China"]},
    "Aldona Kapacinskaite": {"method": "Quantitative", "keywords": ["Resource-Based View", "Appropriability Theory", "Trade Secrets", "Platform Competition"]},
    "Wesley Koo": {"method": "Quant/Mixed", "keywords": ["Platform Theory", "Institutional Theory", "Platform Governance", "Digital Entrepreneurship"]},
    "Wesley W. Koo": {"method": "Quant/Mixed", "keywords": ["Platform Theory", "Institutional Theory", "Platform Governance", "Digital Entrepreneurship"]},
    "Catherine Magelssen": {"method": "Quantitative", "keywords": ["Property Rights Theory", "TCE", "Multinational Strategy", "IP Governance"]},
    "Anparasan Mahalingam": {"method": "Quantitative", "keywords": ["Platform Theory", "Org. Economics", "Digital Corporate Strategy", "Platform Governance"]},
    "Francisco Morales": {"method": "Quantitative", "keywords": ["Strategic Human Capital", "Signaling Theory", "Human Capital", "Immigration"]},
    "FJ Morales": {"method": "Quantitative", "keywords": ["Strategic Human Capital", "Signaling Theory", "Human Capital", "Immigration"]},
    "Metin Sengul": {"method": "Quantitative", "keywords": ["Org. Design Theory", "Behavioral Theory", "Org. Design", "Multiunit Firms"]},
    "Xiaoli Tang": {"method": "Quant/Mixed", "keywords": ["Institutional Theory", "Stakeholder Theory", "Accountable Secrecy", "Self-Regulation"]},
    "Andy Wu": {"method": "Quant/Mixed", "keywords": ["Org. Design Theory", "Platform Theory", "Entrepreneurship", "Platform Ecosystems"]},
    "Mingtao Xu": {"method": "Quantitative", "keywords": ["Property Rights Theory", "Org. Learning", "AI & Strategy", "Patent Litigation"]},
    "Tony Tong": {"method": "Mixed", "keywords": ["Strategy", "Innovation", "International Business", "Real Options"]}
}


@dataclass
class Paper:
    id: str
    title: str
    abstract: str
    keywords: str
    method: Optional[str] = None
    keyword_set: Set[str] = field(default_factory=set)
    reviewer_scores: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        # Pre-compute keyword set for matching
        self.keyword_set = self._extract_keywords()

    def _extract_keywords(self) -> Set[str]:
        """Extract normalized keywords from keywords field and abstract."""
        words = set()
        
        # From keywords field
        if self.keywords:
            for kw in self.keywords.lower().split(','):
                kw = kw.strip()
                if len(kw) > 2:
                    words.add(kw)
                    # Also add individual words
                    for w in kw.split():
                        if len(w) > 3:
                            words.add(w)
        
        # From abstract - extract key terms
        if self.abstract:
            # Common academic stopwords to ignore
            stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 
                        'can', 'had', 'her', 'was', 'one', 'our', 'out', 'has',
                        'have', 'been', 'were', 'being', 'their', 'there', 'this',
                        'that', 'with', 'they', 'from', 'which', 'will', 'would',
                        'could', 'should', 'about', 'into', 'through', 'during',
                        'before', 'after', 'above', 'below', 'between', 'under',
                        'also', 'only', 'other', 'such', 'than', 'then', 'these',
                        'those', 'some', 'what', 'when', 'where', 'while', 'more',
                        'most', 'each', 'both', 'find', 'found', 'study', 'paper',
                        'research', 'results', 'using', 'based', 'show', 'shows'}
            
            abstract_words = re.findall(r'[a-z]+', self.abstract.lower())
            for w in abstract_words:
                if len(w) > 4 and w not in stopwords:
                    words.add(w)
        
        return words


@dataclass
class Reviewer:
    id: str
    name: str
    email: str
    method: str
    keywords: List[str]
    keyword_set: Set[str]
    max_papers: int  # 0 means no limit
    
    @classmethod
    def from_firebase(cls, rid: str, data: dict) -> 'Reviewer':
        """Create Reviewer from Firebase data, with fallback to hardcoded keywords."""
        name = data.get('name', 'Unknown')
        
        # Try to parse expertise from Firebase
        expertise = data.get('expertise', '')
        method, keywords = parse_expertise(expertise)
        
        # If no keywords from Firebase, try fallback dict
        if not keywords and name in FALLBACK_REVIEWERS:
            fallback = FALLBACK_REVIEWERS[name]
            method = fallback.get('method', method)
            keywords = fallback.get('keywords', [])
        
        # Create keyword set for matching
        keyword_set = set()
        for kw in keywords:
            kw_lower = kw.lower()
            keyword_set.add(kw_lower)
            for w in kw_lower.split():
                if len(w) > 3:
                    keyword_set.add(w)
        
        return cls(
            id=rid,
            name=name,
            email=data.get('email', ''),
            method=method,
            keywords=keywords,
            keyword_set=keyword_set,
            max_papers=int(data.get('maxPapers', 0))  # 0 = no limit
        )


def parse_expertise(expertise: str) -> tuple:
    """
    Parse expertise string to extract method and keywords.
    Expected format: "Method: Quantitative | Keywords: keyword1, keyword2, keyword3"
    Or just comma-separated keywords.
    """
    method = "Mixed"  # Default
    keywords = []
    
    if not expertise:
        return method, keywords
    
    # Check for structured format
    if '|' in expertise:
        parts = expertise.split('|')
        for part in parts:
            part = part.strip()
            if part.lower().startswith('method:'):
                method = part[7:].strip()
            elif part.lower().startswith('keywords:'):
                kw_str = part[9:].strip()
                keywords = [k.strip() for k in kw_str.split(',') if k.strip()]
    else:
        # Just keywords
        keywords = [k.strip() for k in expertise.split(',') if k.strip()]
    
    return method, keywords


def load_reviewers_from_firebase() -> Dict[str, Reviewer]:
    """Load all reviewers from Firebase."""
    print("📡 Loading reviewers from Firebase...")
    
    try:
        response = requests.get(f"{FIREBASE_DB_URL}/reviewers.json", timeout=30)
        if response.status_code != 200:
            print(f"   ✗ Firebase error: {response.status_code}")
            return {}
        
        data = response.json()
        if not data:
            print("   ⚠ No reviewers found in Firebase")
            return {}
        
        reviewers = {}
        for rid, rdata in data.items():
            reviewer = Reviewer.from_firebase(rid, rdata)
            reviewers[rid] = reviewer
            print(f"   ✓ {reviewer.name}: {reviewer.method} | Max: {reviewer.max_papers or '∞'} | Keywords: {len(reviewer.keywords)}")
        
        print(f"   ✓ Loaded {len(reviewers)} reviewers")
        return reviewers
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return {}


def load_current_assignments_from_firebase() -> Dict[str, List[str]]:
    """Load current assignments from Firebase to respect existing load."""
    print("📡 Loading current assignments from Firebase...")
    
    try:
        response = requests.get(f"{FIREBASE_DB_URL}/assignments.json", timeout=30)
        if response.status_code != 200:
            return {}
        
        data = response.json()
        if not data:
            print("   ✓ No existing assignments")
            return {}
        
        # Data format: {reviewer_id: [paper_id1, paper_id2, ...]}
        assignments = {}
        for rid, papers in data.items():
            if isinstance(papers, list):
                assignments[rid] = papers
            else:
                assignments[rid] = []
        
        total = sum(len(p) for p in assignments.values())
        print(f"   ✓ Found {total} existing assignments")
        return assignments
        
    except Exception as e:
        print(f"   ⚠ Could not load assignments: {e}")
        return {}


def method_matches(paper_method: str, reviewer_method: str) -> bool:
    """Check if reviewer can review paper based on method."""
    paper_method = paper_method.lower()
    reviewer_method = reviewer_method.lower()
    
    # Mixed/Quant-Mixed reviewers can review anything
    if 'mixed' in reviewer_method:
        return True
    
    # Qualitative reviewers for qualitative papers
    if paper_method == 'qualitative':
        return 'qualitative' in reviewer_method or 'mixed' in reviewer_method
    
    # Quantitative papers need quantitative or mixed reviewers
    if paper_method == 'quantitative':
        return 'quantitative' in reviewer_method or 'mixed' in reviewer_method
    
    # Conceptual - anyone can review
    if paper_method == 'conceptual':
        return True
    
    return True  # Default allow


def calculate_keyword_similarity(paper: Paper, reviewer: Reviewer) -> float:
    """
    Calculate keyword similarity score between paper and reviewer.
    Returns a score from 0 to 1.
    """
    if not paper.keyword_set or not reviewer.keyword_set:
        return 0.0
    
    # Count overlapping keywords
    overlap = paper.keyword_set & reviewer.keyword_set
    
    # Jaccard-like similarity with reviewer focus
    # We care more about matching reviewer expertise
    if len(reviewer.keyword_set) == 0:
        return 0.0
    
    # Score = overlap / reviewer keywords (% of expertise matched)
    # Plus bonus for each overlap
    score = len(overlap) / len(reviewer.keyword_set) + len(overlap) * 0.1
    
    return min(score, 1.0)  # Cap at 1.0


def get_available_reviewers(
    paper: Paper,
    reviewers: Dict[str, Reviewer],
    current_load: Dict[str, int]
) -> List[str]:
    """Get reviewers who can review this paper (method match + capacity available)."""
    available = []
    
    for rid, reviewer in reviewers.items():
        # Check method match
        if not method_matches(paper.method or 'Mixed', reviewer.method):
            continue
        
        # Check capacity
        load = current_load.get(rid, 0)
        if reviewer.max_papers > 0 and load >= reviewer.max_papers:
            continue
        
        available.append(rid)
    
    return available


def rank_reviewers_for_paper(
    paper: Paper,
    available_reviewers: List[str],
    reviewers: Dict[str, Reviewer],
    current_load: Dict[str, int]
) -> Dict[str, float]:
    """Rank available reviewers by keyword similarity with load penalty."""
    scores = {}
    
    for rid in available_reviewers:
        reviewer = reviewers[rid]
        
        # Base score from keyword similarity
        base_score = calculate_keyword_similarity(paper, reviewer)
        
        # Load penalty - prefer less loaded reviewers
        load = current_load.get(rid, 0)
        capacity = reviewer.max_papers if reviewer.max_papers > 0 else 10
        load_penalty = (load / capacity) * 0.3  # Up to 30% penalty
        
        final_score = max(0, base_score - load_penalty)
        scores[rid] = final_score
    
    return scores


def load_papers(csv_path: str) -> List[Paper]:
    """Load papers from CSV."""
    papers = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            papers.append(Paper(
                id=row.get('id', ''),
                title=row.get('title', ''),
                abstract=row.get('abstract', ''),
                keywords=row.get('keywords', '')
            ))
    return papers


def classify_method_simple(paper: Paper) -> str:
    """Simple heuristic method classification based on keywords."""
    text = f"{paper.title} {paper.abstract} {paper.keywords}".lower()
    
    quant_words = ['regression', 'econometric', 'statistical', 'empirical', 
                   'quantitative', 'panel data', 'survey', 'sample', 'dataset',
                   'variables', 'coefficient', 'significant', 'hypothesis']
    
    qual_words = ['case study', 'interview', 'ethnograph', 'qualitative',
                  'grounded theory', 'narrative', 'interpretive', 'phenomeno']
    
    quant_count = sum(1 for w in quant_words if w in text)
    qual_count = sum(1 for w in qual_words if w in text)
    
    if quant_count > 2 and quant_count > qual_count:
        return 'Quantitative'
    elif qual_count > 1 and qual_count > quant_count:
        return 'Qualitative'
    elif quant_count > 0 and qual_count > 0:
        return 'Mixed'
    else:
        return 'Conceptual'


def save_assignments(assignments: Dict[str, List[str]], papers: List[Paper], 
                    reviewers: Dict[str, Reviewer], output_path: str):
    """Save assignments to CSV."""
    paper_lookup = {p.id: p for p in papers}
    
    # Invert: paper -> [reviewers]
    paper_assignments = defaultdict(list)
    for rid, paper_ids in assignments.items():
        for pid in paper_ids:
            reviewer = reviewers.get(rid)
            if reviewer:
                paper_assignments[pid].append(reviewer.name)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['paper_id', 'title', 'method', 'reviewer_1', 'reviewer_2'])
        
        for paper in sorted(papers, key=lambda p: p.id):
            assigned = paper_assignments.get(paper.id, [])
            writer.writerow([
                paper.id,
                paper.title[:60] if paper.title else '',
                paper.method if paper.method else '',
                assigned[0] if len(assigned) > 0 else '',
                assigned[1] if len(assigned) > 1 else ''
            ])


def main():
    print("=" * 60)
    print("Strategy Science 2026 - Keyword-Based Reviewer Assignment")
    print("=" * 60)
    print("Using pairwise keyword matching (no LLM needed)")
    
    start_time = time.time()
    
    # Load reviewers from Firebase
    reviewers = load_reviewers_from_firebase()
    if not reviewers:
        print("\n✗ No reviewers found. Add reviewers in the admin portal first.")
        return
    
    # Load current assignments (to respect existing load)
    existing_assignments = load_current_assignments_from_firebase()
    
    # Calculate current load per reviewer
    current_load = defaultdict(int)
    for rid, papers in existing_assignments.items():
        current_load[rid] = len(papers)
    
    # Load papers
    print(f"\n📄 Loading papers from {INPUT_CSV}...")
    try:
        papers = load_papers(INPUT_CSV)
        if TEST_MODE:
            papers = papers[:TEST_MODE]
            print(f"   ✓ Loaded {len(papers)} papers (TEST MODE)")
        else:
            print(f"   ✓ Loaded {len(papers)} papers")
    except FileNotFoundError:
        print(f"   ✗ File not found: {INPUT_CSV}")
        return
    
    # Phase 1: Classify methods
    print("\n" + "=" * 60)
    print("PHASE 1: Classifying research methods")
    print("=" * 60)
    
    method_counts = Counter()
    for paper in papers:
        paper.method = classify_method_simple(paper)
        method_counts[paper.method] += 1
        print(f"   {paper.id}: {paper.method}")
    
    print(f"\n   Method distribution:")
    for method, count in sorted(method_counts.items()):
        print(f"      {method}: {count}")
    
    # Phase 2: Score and assign reviewers
    print("\n" + "=" * 60)
    print("PHASE 2: Matching papers to reviewers (keyword-based)")
    print("=" * 60)
    
    new_assignments = defaultdict(list)
    
    for i, paper in enumerate(papers):
        print(f"\n[{i+1}/{len(papers)}] {paper.id}: {paper.title[:40]}...")
        
        # Get available reviewers
        available = get_available_reviewers(paper, reviewers, current_load)
        print(f"   → {len(available)} available reviewers for {paper.method} paper")
        
        if len(available) < 2:
            print(f"   ⚠ Not enough available reviewers!")
            continue
        
        # Score reviewers
        scores = rank_reviewers_for_paper(paper, available, reviewers, current_load)
        
        # Get top 2
        sorted_reviewers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_2 = sorted_reviewers[:2]
        
        for rid, score in top_2[:5]:  # Show top 5 for reference
            reviewer = reviewers[rid]
            print(f"   → {reviewer.name}: {score:.3f}")
        
        # Assign top 2
        for rid, score in top_2:
            new_assignments[rid].append(paper.id)
            current_load[rid] += 1
        
        # Batch checkpoint every 5
        if (i + 1) % 5 == 0:
            print(f"   💾 Checkpoint at paper {i+1}")
    
    # Phase 3: Summary and save
    print("\n" + "=" * 60)
    print("PHASE 3: Saving results")
    print("=" * 60)
    
    # Show load distribution
    print("\nReviewer load distribution:")
    for rid, reviewer in reviewers.items():
        load = current_load.get(rid, 0)
        cap = reviewer.max_papers if reviewer.max_papers > 0 else 10
        bar = "█" * min(load, 10) + "░" * max(0, 10 - load)
        cap_str = str(reviewer.max_papers) if reviewer.max_papers > 0 else "∞"
        print(f"   {reviewer.name:25} [{bar}] {load}/{cap_str}")
    
    # Save
    print(f"\n📝 Saving to {OUTPUT_CSV}...")
    save_assignments(new_assignments, papers, reviewers, OUTPUT_CSV)
    
    # Final summary
    total_time = time.time() - start_time
    assigned_papers = set()
    for papers_list in new_assignments.values():
        assigned_papers.update(papers_list)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Total time: {total_time:.1f} seconds")
    print(f"✓ Papers processed: {len(papers)}")
    print(f"✓ Papers assigned: {len(assigned_papers)}")
    print(f"✓ Output saved to: {OUTPUT_CSV}")
    print("\nNext: Import assignments.csv into your review system")


if __name__ == "__main__":
    main()
