#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - TRUE PAIRWISE Reviewer Assignment

PAIRWISE LLM MATCHING:
1. For each paper, evaluate EACH eligible reviewer individually
2. One LLM call per paper-reviewer pair for deep scoring
3. Score 0-100 with reasoning
4. Respects Firebase capacities
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

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"

# Firebase Configuration
FIREBASE_DB_URL = "https://strategyscience2026-default-rtdb.firebaseio.com"

# Fallback reviewer expertise data
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


@dataclass
class Reviewer:
    id: str
    name: str
    email: str
    method: str
    keywords: List[str]
    max_papers: int
    
    @classmethod
    def from_firebase(cls, rid: str, data: dict) -> 'Reviewer':
        name = data.get('name', 'Unknown')
        expertise = data.get('expertise', '')
        
        # Parse or fallback
        if expertise:
            method, keywords = parse_expertise(expertise)
        elif name in FALLBACK_REVIEWERS:
            method = FALLBACK_REVIEWERS[name]['method']
            keywords = FALLBACK_REVIEWERS[name]['keywords']
        else:
            method = "Mixed"
            keywords = []
        
        return cls(
            id=rid,
            name=name,
            email=data.get('email', ''),
            method=method,
            keywords=keywords,
            max_papers=int(data.get('maxPapers', 0))
        )


def parse_expertise(expertise: str) -> tuple:
    method = "Mixed"
    keywords = []
    if '|' in expertise:
        parts = expertise.split('|')
        for part in parts:
            part = part.strip()
            if part.lower().startswith('method:'):
                method = part[7:].strip()
            elif part.lower().startswith('keywords:'):
                keywords = [k.strip() for k in part[9:].split(',') if k.strip()]
    else:
        keywords = [k.strip() for k in expertise.split(',') if k.strip()]
    return method, keywords


def query_llm(prompt: str, max_tokens: int = 100) -> str:
    """Query Ollama with prompt."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": max_tokens}
            },
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
    except Exception as e:
        print(f"      ⚠ LLM error: {e}")
    return ""


def score_paper_reviewer_pair(paper: Paper, reviewer: Reviewer) -> tuple:
    """
    Score a single paper-reviewer pair using LLM.
    Returns (score: int 0-100, reason: str)
    """
    prompt = f"""Rate how well this reviewer matches this paper. Score 0-100.

PAPER:
Title: {paper.title}
Abstract: {paper.abstract[:1500] if paper.abstract else 'N/A'}
Keywords: {paper.keywords}
Method: {paper.method or 'Unknown'}

REVIEWER:
Name: {reviewer.name}
Method: {reviewer.method}
Expertise: {', '.join(reviewer.keywords)}

Scoring criteria:
- Topic overlap (keywords match)
- Theory/framework alignment  
- Methodology fit

RESPOND WITH ONLY: SCORE: [number 0-100] | REASON: [one sentence]"""

    response = query_llm(prompt, max_tokens=80)
    
    # Parse score
    score = 0
    reason = ""
    
    if 'SCORE:' in response.upper():
        try:
            # Extract score
            score_match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
            if score_match:
                score = min(100, max(0, int(score_match.group(1))))
            
            # Extract reason
            reason_match = re.search(r'REASON:\s*(.+)', response, re.IGNORECASE)
            if reason_match:
                reason = reason_match.group(1).strip()
        except:
            pass
    
    return score, reason


def load_reviewers_from_firebase() -> Dict[str, Reviewer]:
    print("📡 Loading reviewers from Firebase...")
    try:
        response = requests.get(f"{FIREBASE_DB_URL}/reviewers.json", timeout=30)
        if response.status_code != 200:
            return {}
        data = response.json() or {}
        
        reviewers = {}
        for rid, rdata in data.items():
            reviewer = Reviewer.from_firebase(rid, rdata)
            reviewers[rid] = reviewer
            print(f"   ✓ {reviewer.name}: {reviewer.method} | Keywords: {len(reviewer.keywords)}")
        
        print(f"   ✓ Loaded {len(reviewers)} reviewers")
        return reviewers
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return {}


def load_papers(csv_path: str) -> List[Paper]:
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


def method_matches(paper_method: str, reviewer_method: str) -> bool:
    paper_method = (paper_method or '').lower()
    reviewer_method = (reviewer_method or '').lower()
    
    if 'mixed' in reviewer_method:
        return True
    if paper_method == 'qualitative':
        return 'qualitative' in reviewer_method or 'mixed' in reviewer_method
    if paper_method == 'quantitative':
        return 'quantitative' in reviewer_method or 'mixed' in reviewer_method
    return True  # Conceptual or unknown


def classify_method_simple(paper: Paper) -> str:
    text = f"{paper.title} {paper.abstract} {paper.keywords}".lower()
    
    quant_words = ['regression', 'econometric', 'statistical', 'empirical', 
                   'quantitative', 'panel data', 'survey', 'sample', 'dataset']
    qual_words = ['case study', 'interview', 'ethnograph', 'qualitative', 'grounded theory']
    
    quant_count = sum(1 for w in quant_words if w in text)
    qual_count = sum(1 for w in qual_words if w in text)
    
    if quant_count > 2 and quant_count > qual_count:
        return 'Quantitative'
    elif qual_count > 1:
        return 'Qualitative'
    elif quant_count > 0 and qual_count > 0:
        return 'Mixed'
    return 'Conceptual'


def save_assignments(assignments: Dict[str, List[str]], papers: List[Paper], 
                    reviewers: Dict[str, Reviewer], scores_log: Dict,
                    output_path: str):
    """Save assignments with scores to CSV."""
    paper_assignments = defaultdict(list)
    for rid, paper_ids in assignments.items():
        for pid in paper_ids:
            reviewer = reviewers.get(rid)
            if reviewer:
                paper_assignments[pid].append(reviewer.name)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['paper_id', 'title', 'method', 'reviewer_1', 'reviewer_2', 'score_1', 'score_2'])
        
        for paper in sorted(papers, key=lambda p: p.id):
            assigned = paper_assignments.get(paper.id, [])
            scores = scores_log.get(paper.id, {})
            
            r1 = assigned[0] if len(assigned) > 0 else ''
            r2 = assigned[1] if len(assigned) > 1 else ''
            s1 = scores.get(r1, 0) if r1 else ''
            s2 = scores.get(r2, 0) if r2 else ''
            
            writer.writerow([
                paper.id,
                paper.title[:60],
                paper.method or '',
                r1, r2, s1, s2
            ])


def main():
    print("=" * 70)
    print("Strategy Science 2026 - TRUE PAIRWISE LLM Reviewer Assignment")
    print("=" * 70)
    print(f"Model: {OLLAMA_MODEL} | One LLM call per paper-reviewer pair")
    
    start_time = time.time()
    
    # Load reviewers
    reviewers = load_reviewers_from_firebase()
    if not reviewers:
        print("\n✗ No reviewers found.")
        return
    
    # Load papers
    print(f"\n📄 Loading papers from {INPUT_CSV}...")
    try:
        papers = load_papers(INPUT_CSV)
        if TEST_MODE:
            papers = papers[:TEST_MODE]
        print(f"   ✓ Loaded {len(papers)} papers")
    except FileNotFoundError:
        print(f"   ✗ File not found: {INPUT_CSV}")
        return
    
    # Estimate time
    total_pairs = len(papers) * len(reviewers)
    print(f"\n⏱ Estimated: {total_pairs} LLM calls (~{total_pairs * 2 / 60:.1f} minutes)")
    
    # Classify methods
    print("\n" + "=" * 70)
    print("PHASE 1: Classifying paper methods")
    print("=" * 70)
    for paper in papers:
        paper.method = classify_method_simple(paper)
        print(f"   {paper.id}: {paper.method}")
    
    # Pairwise scoring
    print("\n" + "=" * 70)
    print("PHASE 2: PAIRWISE LLM Scoring (each paper × each reviewer)")
    print("=" * 70)
    
    assignments = defaultdict(list)
    current_load = defaultdict(int)
    scores_log = {}  # {paper_id: {reviewer_name: score}}
    
    for i, paper in enumerate(papers):
        paper_start = time.time()
        elapsed_total = time.time() - start_time
        
        print(f"\n[{i+1}/{len(papers)}] {paper.id}: {paper.title[:45]}...")
        print(f"    Method: {paper.method}")
        
        # Get available reviewers (method match + capacity)
        available = []
        for rid, reviewer in reviewers.items():
            if not method_matches(paper.method, reviewer.method):
                continue
            if reviewer.max_papers > 0 and current_load[rid] >= reviewer.max_papers:
                continue
            available.append((rid, reviewer))
        
        print(f"    Available reviewers: {len(available)}")
        
        if len(available) < 2:
            print(f"    ⚠ Not enough reviewers!")
            continue
        
        # Score each available reviewer
        pair_scores = {}
        for j, (rid, reviewer) in enumerate(available):
            score, reason = score_paper_reviewer_pair(paper, reviewer)
            pair_scores[rid] = score
            print(f"      [{j+1}/{len(available)}] {reviewer.name}: {score}", end="")
            if reason:
                print(f" - {reason[:40]}...")
            else:
                print()
        
        # Store scores
        scores_log[paper.id] = {reviewers[rid].name: s for rid, s in pair_scores.items()}
        
        # Assign top 2
        sorted_scores = sorted(pair_scores.items(), key=lambda x: x[1], reverse=True)
        top_2 = sorted_scores[:2]
        
        print(f"    ✓ Assigned: ", end="")
        for rid, score in top_2:
            assignments[rid].append(paper.id)
            current_load[rid] += 1
            print(f"{reviewers[rid].name}({score}) ", end="")
        print()
        
        paper_time = time.time() - paper_start
        print(f"    ⏱ Paper time: {paper_time:.1f}s | Total: {elapsed_total/60:.1f}min")
        
        # Checkpoint every 5
        if (i + 1) % 5 == 0:
            print(f"    💾 Checkpoint at paper {i+1}")
            save_assignments(assignments, papers, reviewers, scores_log, OUTPUT_CSV)
    
    # Final save
    print("\n" + "=" * 70)
    print("PHASE 3: Saving results")
    print("=" * 70)
    
    save_assignments(assignments, papers, reviewers, scores_log, OUTPUT_CSV)
    
    # Load distribution
    print("\nReviewer load distribution:")
    for rid, reviewer in reviewers.items():
        load = current_load.get(rid, 0)
        cap_str = str(reviewer.max_papers) if reviewer.max_papers > 0 else "∞"
        bar = "█" * min(load, 10) + "░" * max(0, 10 - load)
        print(f"   {reviewer.name:25} [{bar}] {load}/{cap_str}")
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Total time: {total_time/60:.1f} minutes")
    print(f"✓ Papers processed: {len(papers)}")
    print(f"✓ LLM calls made: ~{len(papers) * len(reviewers)}")
    print(f"✓ Output saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
