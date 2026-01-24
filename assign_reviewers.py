#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - Reviewer Assignment Script

Reads papers from papers_import.csv, uses LLM to:
1. Extract research method from each paper
2. Match papers to reviewers based on method + topic fit
3. Assign 2 reviewers per paper with load balancing

Requires: Ollama running with llama3.1:8b (or qwen2.5:7b)
"""

import csv
import requests
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

# =====================
# CONFIGURATION
# =====================
INPUT_CSV = "papers_import.csv"
OUTPUT_CSV = "assignments.csv"
TEST_MODE = 5  # Set to None to process all papers, or a number to limit

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:14b"  # Updated to Qwen3 14B with 128K context

# =====================
# REVIEWER DATA
# =====================
# Method categories for hard filtering
METHOD_QUANTITATIVE = ["Quantitative", "Quant/Mixed"]
METHOD_QUALITATIVE = ["Qualitative"]
METHOD_MIXED = ["Mixed", "Quant/Mixed"]  # Can review any method

REVIEWERS = {
    "Janet Bercovitz": {
        "method": "Quantitative",
        "keywords": ["Transaction Cost Economics", "Org. Learning", "Academic Entrepreneurship", "Tech Transfer"]
    },
    "Danielle Bovenberg": {
        "method": "Qualitative",
        "keywords": ["Craft Knowledge", "Org. Theory", "Innovation", "Knowledge Diffusion"]
    },
    "Mukund Chari": {
        "method": "Quantitative",
        "keywords": ["Transaction Cost Economics", "Agency Theory", "Intellectual Property", "Patent Systems"]
    },
    "Ashton Hawk": {
        "method": "Quantitative",
        "keywords": ["Resource-Based View", "Dynamic Capabilities", "Investment Speed", "Political Capital"]
    },
    "Sina Sokhan": {
        "method": "Quantitative",
        "keywords": ["Knowledge Recombination", "IP Theory", "Innovation Process", "Pharma Innovation"]
    },
    "MJ Yang": {
        "method": "Quant/Mixed",
        "keywords": ["Complementarity Theory", "RBV", "CEO Strategy", "Tech Uniqueness"]
    },
    "Kenneth Huang": {
        "method": "Quant/Mixed",
        "keywords": ["Institutional Theory", "Knowledge-Based View", "IP Strategy", "Innovation in China"]
    },
    "Aldona Kapacinskaite": {
        "method": "Quantitative",
        "keywords": ["Resource-Based View", "Appropriability Theory", "Trade Secrets", "Platform Competition"]
    },
    "Wesley Koo": {
        "method": "Quant/Mixed",
        "keywords": ["Platform Theory", "Institutional Theory", "Platform Governance", "Digital Entrepreneurship"]
    },
    "Catherine Magelssen": {
        "method": "Quantitative",
        "keywords": ["Property Rights Theory", "TCE", "Multinational Strategy", "IP Governance"]
    },
    "Anparasan Mahalingam": {
        "method": "Quantitative",
        "keywords": ["Platform Theory", "Org. Economics", "Digital Corporate Strategy", "Platform Governance"]
    },
    "Francisco Morales": {
        "method": "Quantitative",
        "keywords": ["Strategic Human Capital", "Signaling Theory", "Human Capital", "Immigration"]
    },
    "Metin Sengul": {
        "method": "Quantitative",
        "keywords": ["Org. Design Theory", "Behavioral Theory", "Org. Design", "Multiunit Firms"]
    },
    "Xiaoli Tang": {
        "method": "Quant/Mixed",
        "keywords": ["Institutional Theory", "Stakeholder Theory", "Accountable Secrecy", "Self-Regulation"]
    },
    "Andy Wu": {
        "method": "Quant/Mixed",
        "keywords": ["Org. Design Theory", "Platform Theory", "Entrepreneurship", "Platform Ecosystems"]
    },
    "Mingtao Xu": {
        "method": "Quantitative",
        "keywords": ["Property Rights Theory", "Org. Learning", "AI & Strategy", "Patent Litigation"]
    },
    "Tony Tong": {
        "method": "Mixed",
        "keywords": ["Strategy", "Innovation", "International Business", "Real Options"]
    }
}


@dataclass
class Paper:
    id: str
    title: str
    abstract: str
    keywords: str
    method: Optional[str] = None
    reviewer_scores: dict = None

    def __post_init__(self):
        if self.reviewer_scores is None:
            self.reviewer_scores = {}


def query_llm(prompt: str, max_tokens: int = 500) -> str:
    """Query Ollama with prompt, return response."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": max_tokens
                }
            },
            timeout=120
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
    except Exception as e:
        print(f"    ⚠ LLM error: {e}")
    return ""


def extract_method(paper: Paper) -> str:
    """Use LLM to determine paper's research method."""
    prompt = f"""Analyze this academic paper and determine its PRIMARY research method.

Title: {paper.title}
Abstract: {paper.abstract[:3500] if paper.abstract else 'Not available'}
Keywords: {paper.keywords}

Classify as ONE of:
- QUANTITATIVE: Uses statistical analysis, econometrics, large-N studies, regression, surveys with numerical analysis
- QUALITATIVE: Uses case studies, interviews, ethnography, grounded theory, interpretive methods
- MIXED: Combines both quantitative and qualitative methods
- CONCEPTUAL: Theoretical/conceptual paper without empirical data

Respond with ONLY one word: QUANTITATIVE, QUALITATIVE, MIXED, or CONCEPTUAL"""

    response = query_llm(prompt, max_tokens=20)

    # Parse response
    response_upper = response.upper().strip()
    if "QUANTITATIVE" in response_upper:
        return "Quantitative"
    elif "QUALITATIVE" in response_upper:
        return "Qualitative"
    elif "MIXED" in response_upper:
        return "Mixed"
    elif "CONCEPTUAL" in response_upper:
        return "Conceptual"
    else:
        print(f"    ⚠ Unknown method response: {response}, defaulting to Mixed")
        return "Mixed"


def get_eligible_reviewers(paper_method: str) -> list:
    """Get reviewers who can review papers of this method type."""
    eligible = []

    for name, info in REVIEWERS.items():
        reviewer_method = info["method"]

        # Hard filter logic:
        # - Quantitative papers -> Quantitative or Quant/Mixed reviewers
        # - Qualitative papers -> Qualitative or Mixed reviewers
        # - Mixed/Conceptual papers -> Anyone

        if paper_method == "Quantitative":
            if reviewer_method in ["Quantitative", "Quant/Mixed", "Mixed"]:
                eligible.append(name)
        elif paper_method == "Qualitative":
            if reviewer_method in ["Qualitative", "Mixed"]:
                eligible.append(name)
        else:  # Mixed or Conceptual
            eligible.append(name)

    return eligible


def rank_reviewers_for_paper(paper: Paper, eligible_reviewers: list) -> dict:
    """Use LLM to rank eligible reviewers for this paper."""

    # Build reviewer descriptions
    reviewer_descriptions = []
    for name in eligible_reviewers:
        info = REVIEWERS[name]
        reviewer_descriptions.append(
            f"- {name}: {info['method']} researcher. Expertise: {', '.join(info['keywords'])}"
        )

    prompt = f"""You are matching an academic paper to potential reviewers.

PAPER:
Title: {paper.title}
Abstract: {paper.abstract[:3500] if paper.abstract else 'Not available'}
Keywords: {paper.keywords}
Method: {paper.method}

ELIGIBLE REVIEWERS:
{chr(10).join(reviewer_descriptions)}

Rank the TOP 5 best-matched reviewers for this paper based on:
1. Topic/keyword overlap with the paper
2. Theoretical framework alignment
3. Methodological fit

Respond in this EXACT format (one per line):
1. [Reviewer Name] - [brief reason]
2. [Reviewer Name] - [brief reason]
3. [Reviewer Name] - [brief reason]
4. [Reviewer Name] - [brief reason]
5. [Reviewer Name] - [brief reason]"""

    response = query_llm(prompt, max_tokens=400)

    # Parse rankings
    scores = {}
    lines = response.strip().split('\n')

    for i, line in enumerate(lines[:5]):
        # Extract reviewer name from line like "1. Janet Bercovitz - reason"
        for reviewer in eligible_reviewers:
            if reviewer.lower() in line.lower():
                # Score: 5 for rank 1, 4 for rank 2, etc.
                scores[reviewer] = 5 - i
                break

    # Give score of 0 to unranked eligible reviewers
    for reviewer in eligible_reviewers:
        if reviewer not in scores:
            scores[reviewer] = 0

    return scores


def calculate_capacity(num_papers: int, num_reviewers: int) -> int:
    """Calculate default capacity per reviewer."""
    # Each paper needs 2 reviewers
    total_assignments = num_papers * 2
    # Distribute evenly, round up, add small buffer
    base_capacity = (total_assignments // num_reviewers) + 1
    return max(base_capacity, 5)  # Minimum 5 papers


def assign_reviewers(papers: list, default_capacity: int) -> dict:
    """
    Assign 2 reviewers to each paper using greedy algorithm with load balancing.

    Key features to prevent one person reviewing all papers:
    1. Hard capacity cap per reviewer
    2. Load penalty: as reviewer gets more papers, their effective score decreases
    3. Harder papers (fewer eligible reviewers) assigned first

    Returns: {paper_id: [reviewer1, reviewer2]}
    """
    assignments = {}
    reviewer_load = defaultdict(int)
    reviewer_capacity = {name: default_capacity for name in REVIEWERS}

    # Sort papers by number of eligible reviewers (harder papers first)
    # This ensures specialists get assigned to papers that need them
    papers_sorted = sorted(papers, key=lambda p: len(get_eligible_reviewers(p.method)))

    for paper in papers_sorted:
        assigned = []

        # Calculate effective score with load penalty
        # Higher load = lower effective score, encouraging even distribution
        def effective_score(reviewer, base_score):
            load = reviewer_load[reviewer]
            capacity = reviewer_capacity[reviewer]
            # Penalty increases as load approaches capacity
            load_penalty = (load / capacity) * 2  # Max penalty of 2 points
            return base_score - load_penalty

        # Get reviewers sorted by EFFECTIVE score (base score minus load penalty)
        scored_reviewers = sorted(
            paper.reviewer_scores.items(),
            key=lambda x: effective_score(x[0], x[1]),
            reverse=True
        )

        for reviewer, base_score in scored_reviewers:
            if len(assigned) >= 2:
                break

            # Hard capacity cap - never exceed
            if reviewer_load[reviewer] < reviewer_capacity[reviewer]:
                assigned.append(reviewer)
                reviewer_load[reviewer] += 1

        # Fallback: if couldn't assign 2, try any eligible reviewer with lowest load
        if len(assigned) < 2:
            eligible = get_eligible_reviewers(paper.method)
            # Sort by load (prefer less loaded reviewers)
            eligible_sorted = sorted(eligible, key=lambda r: reviewer_load[r])
            for reviewer in eligible_sorted:
                if len(assigned) >= 2:
                    break
                if reviewer not in assigned and reviewer_load[reviewer] < reviewer_capacity[reviewer]:
                    assigned.append(reviewer)
                    reviewer_load[reviewer] += 1

        assignments[paper.id] = assigned

        if len(assigned) < 2:
            print(f"    ⚠ Could only assign {len(assigned)} reviewer(s) to {paper.id}")

    return assignments, reviewer_load


def load_papers(csv_path: str) -> list:
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


def save_assignments(assignments: dict, papers: list, output_path: str):
    """Save assignments to CSV."""
    # Create lookup for paper info
    paper_lookup = {p.id: p for p in papers}

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['paper_id', 'title', 'method', 'reviewer_1', 'reviewer_2'])

        for paper_id, reviewers in sorted(assignments.items()):
            paper = paper_lookup.get(paper_id)
            writer.writerow([
                paper_id,
                paper.title[:60] if paper else '',
                paper.method if paper else '',
                reviewers[0] if len(reviewers) > 0 else '',
                reviewers[1] if len(reviewers) > 1 else ''
            ])


def check_ollama() -> bool:
    """Check if Ollama is running with required model."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = [m.get('name', '') for m in response.json().get('models', [])]
            if any(OLLAMA_MODEL.split(':')[0] in m for m in models):
                return True
            print(f"⚠ Model {OLLAMA_MODEL} not found. Available: {models}")
    except:
        print("⚠ Ollama not running at localhost:11434")
    return False


def main():
    print("=" * 60)
    print("Strategy Science Conference 2026 - Reviewer Assignment")
    print("=" * 60)

    # Check Ollama
    print("\n🤖 Checking Ollama...")
    if not check_ollama():
        print(f"Please start Ollama and pull {OLLAMA_MODEL}")
        print(f"  ollama pull {OLLAMA_MODEL}")
        return
    print(f"✓ Ollama ready with {OLLAMA_MODEL}")

    # Load papers
    print(f"\n📄 Loading papers from {INPUT_CSV}...")
    try:
        papers = load_papers(INPUT_CSV)
        total_papers = len(papers)

        # Apply test mode limit
        if TEST_MODE:
            papers = papers[:TEST_MODE]
            print(f"✓ Loaded {total_papers} papers (TEST MODE: using first {len(papers)})")
        else:
            print(f"✓ Loaded {len(papers)} papers")
    except FileNotFoundError:
        print(f"✗ File not found: {INPUT_CSV}")
        print("  Run process_papers.py first to generate this file.")
        return

    # Calculate capacity
    num_reviewers = len(REVIEWERS)
    default_capacity = calculate_capacity(len(papers), num_reviewers)
    print(f"\n👥 Reviewers: {num_reviewers}")
    print(f"📊 Default capacity per reviewer: {default_capacity} papers")

    # Phase 1: Extract methods
    print("\n" + "=" * 60)
    print("PHASE 1: Extracting research methods")
    print("=" * 60)

    method_counts = defaultdict(int)
    for i, paper in enumerate(papers):
        print(f"[{i+1}/{len(papers)}] {paper.id}: {paper.title[:40]}...")
        paper.method = extract_method(paper)
        method_counts[paper.method] += 1
        print(f"    → Method: {paper.method}")

    print(f"\nMethod distribution:")
    for method, count in sorted(method_counts.items()):
        print(f"  {method}: {count} papers")

    # Phase 2: Rank reviewers for each paper
    print("\n" + "=" * 60)
    print("PHASE 2: Matching papers to reviewers")
    print("=" * 60)

    for i, paper in enumerate(papers):
        print(f"[{i+1}/{len(papers)}] {paper.id}: Finding best reviewers...")
        eligible = get_eligible_reviewers(paper.method)
        print(f"    → {len(eligible)} eligible reviewers for {paper.method} paper")

        paper.reviewer_scores = rank_reviewers_for_paper(paper, eligible)

        # Show top 3
        top3 = sorted(paper.reviewer_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        for name, score in top3:
            print(f"    → {name}: {score}")

    # Phase 3: Assignment with load balancing
    print("\n" + "=" * 60)
    print("PHASE 3: Assigning reviewers with load balancing")
    print("=" * 60)

    assignments, reviewer_load = assign_reviewers(papers, default_capacity)

    # Show load distribution
    print(f"\nReviewer load distribution:")
    for reviewer, load in sorted(reviewer_load.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * load + "░" * (default_capacity - load)
        print(f"  {reviewer:25} [{bar}] {load}/{default_capacity}")

    # Save results
    print(f"\n📝 Saving to {OUTPUT_CSV}...")
    save_assignments(assignments, papers, OUTPUT_CSV)

    # Summary
    assigned_count = sum(1 for r in assignments.values() if len(r) == 2)
    partial_count = sum(1 for r in assignments.values() if len(r) == 1)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Fully assigned (2 reviewers): {assigned_count} papers")
    if partial_count:
        print(f"⚠ Partially assigned (1 reviewer): {partial_count} papers")
    print(f"✓ Output saved to: {OUTPUT_CSV}")
    print("\nNext: Import assignments.csv into your review system")


if __name__ == "__main__":
    main()
