#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - TRUE PAIRWISE Reviewer Assignment V3

IMPROVED PAIRWISE LLM MATCHING:
- Abstract limit increased to ~600 words (4000 chars)
- Added "Notable Publications" to reviewer profiles for better context
- Stricter scoring prompt
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

# =====================
# DETAILED REVIEWER PROFILES (from committee_research_summary.md)
# =====================
REVIEWER_PROFILES = {
    "Janet Bercovitz": {
        "method": "Quantitative",
        "topics": ["Academic entrepreneurship", "Technology transfer", "University-industry relationships", "Knowledge worker mobility", "Industrial clusters", "Organizational change"],
        "theories": ["Transaction Cost Economics", "Organizational Learning", "Social Learning", "Resource-Based View"],
        "publications": [
            "Entrepreneurial universities and technology transfer",
            "Academic entrepreneurs: Organizational change at the individual level",
            "Creating a cluster while building a firm",
            "Complementarity and evolution of contractual provisions"
        ],
        "summary": "Studies academic entrepreneurship, university tech transfer, inter-organizational contracts, and knowledge-based economic development."
    },
    "Janet Lee Elsie Bercovitz": {
        "method": "Quantitative",
        "topics": ["Academic entrepreneurship", "Technology transfer", "University-industry relationships", "Knowledge worker mobility", "Industrial clusters", "Organizational change"],
        "theories": ["Transaction Cost Economics", "Organizational Learning", "Social Learning", "Resource-Based View"],
        "publications": [
            "Entrepreneurial universities and technology transfer",
            "Academic entrepreneurs: Organizational change at the individual level",
            "Creating a cluster while building a firm",
            "Complementarity and evolution of contractual provisions"
        ],
        "summary": "Studies academic entrepreneurship, university tech transfer, inter-organizational contracts, and knowledge-based economic development."
    },
    "Danielle Bovenberg": {
        "method": "Qualitative",
        "topics": ["Innovation in high-tech", "Knowledge diffusion", "Scientific support staff", "Craft knowledge", "Nanofabrication", "Core research facilities"],
        "theories": ["Craft Knowledge Theory", "Structural Complexity", "Organizational Theory", "Occupational Sociology"],
        "publications": [
            "Craft Knowledge and the Advancement of Science",
            "The Role of Scientific Support Occupations in Shared Research Facilities"
        ],
        "summary": "Qualitative researcher studying craft knowledge, technical intermediaries, and knowledge spillovers in technology industries. Uses ethnographic methods."
    },
    "Mukund Chari": {
        "method": "Quantitative",
        "topics": ["Intellectual property rights", "Patent systems", "Patent assertion entities", "Inventor behavior", "Patent quality", "Licensing"],
        "theories": ["Transaction Cost Economics", "Agency Theory", "Professional Identity Theory"],
        "publications": [
            "The influence of patent assertion entities on inventor behavior",
            "A Comparative Analysis of Patent Assertion Entities",
            "The Quest For Expansive Intellectual Property Rights"
        ],
        "summary": "Examines IP management, patent intermediation, and how institutional factors influence innovation and inventor behavior."
    },
    "Ashton Hawk": {
        "method": "Quantitative",
        "topics": ["Investment speed", "Time compression diseconomies", "Political capital", "Alliance partner selection", "Entry timing", "Fast-mover advantages"],
        "theories": ["Resource-Based View", "Dynamic Capabilities", "Time Compression Diseconomies", "Political Capital Theory"],
        "publications": [
            "The half-life of political capital",
            "Time Compression (Dis)Economies: An empirical analysis",
            "The right speed and its value",
            "Fast-Mover Advantages: Speed Capabilities"
        ],
        "summary": "Studies temporal dynamics in strategy, investment speed, and how firms' capabilities affect competitive advantage over time."
    },
    "Ashton Lewis Hawk": {
        "method": "Quantitative",
        "topics": ["Investment speed", "Time compression diseconomies", "Political capital", "Alliance partner selection", "Entry timing", "Fast-mover advantages"],
        "theories": ["Resource-Based View", "Dynamic Capabilities", "Time Compression Diseconomies", "Political Capital Theory"],
        "publications": [
            "The half-life of political capital",
            "Time Compression (Dis)Economies: An empirical analysis",
            "The right speed and its value",
            "Fast-Mover Advantages: Speed Capabilities"
        ],
        "summary": "Studies temporal dynamics in strategy, investment speed, and how firms' capabilities affect competitive advantage over time."
    },
    "Sina Sokhan": {
        "method": "Quantitative",
        "topics": ["Innovation process", "Knowledge recombination", "IP rights and innovation", "Pharmaceutical innovation", "Antibiotic development", "Commercialization costs"],
        "theories": ["Knowledge Recombination Theory", "Intellectual Property Theory", "Innovation Economics"],
        "publications": [
            "Innovation process and knowledge recombination",
            "Intellectual property rights and innovation",
            "Pharmaceutical innovation and antibiotic development"
        ],
        "summary": "Examines what enables, constrains, and causes innovation to fail. Focus on pharma innovation and how IP rights facilitate or impede knowledge recombination."
    },
    "MJ Yang": {
        "method": "Quantitative/Mixed",
        "topics": ["CEO strategic decision-making", "Technological uniqueness", "Industrial AI adoption", "Complementarities", "R&D capital", "Organizational design"],
        "theories": ["Complementarity Theory", "Resource-Based View", "Dynamic Capabilities", "Organizational Economics"],
        "publications": [
            "How Do CEOs Make Strategy?",
            "The Technological Uniqueness Paradox",
            "Complementarity of Task Allocation and Performance Pay",
            "Micro-Level Misallocation and Selection"
        ],
        "summary": "Examines drivers of firm performance gaps, strategy processes, technological positioning, and complementarities between organizational design and strategy."
    },
    "Kenneth Huang": {
        "method": "Quantitative/Mixed",
        "topics": ["IP strategy", "Innovation in China", "Patent trolls/NPEs", "State-owned enterprises", "Government policy and innovation", "Knowledge worker mobility", "Green innovation"],
        "theories": ["Institutional Theory", "Knowledge-Based View", "Resource-Based View", "Innovation Economics"],
        "publications": [
            "Does Patent Strategy Shape the Long-run Supply of Public Knowledge?",
            "Public Governance, Corporate Governance and Firm Innovation: SOEs",
            "Escaping the Patent Trolls: NPE Litigation and Firm Innovation",
            "Using Supervised Machine Learning for Large-scale Classification"
        ],
        "summary": "Studies IP strategy, innovation in emerging economies (especially China), institutions and government policy shaping innovation, uses machine learning methods."
    },
    "Aldona Kapacinskaite": {
        "method": "Quantitative",
        "topics": ["Trade secrets", "Appropriability", "Platform competition", "Resource redeployment", "Patent licensing", "Digital platforms", "Energy transition"],
        "theories": ["Resource-Based View", "Appropriability Theory", "Platform Theory", "Competitive Strategy"],
        "publications": [
            "Keeping Invention Confidential",
            "Competing with the platform: Complementor positioning",
            "From Wells to Windmills: Resource Redeployment"
        ],
        "summary": "Examines organizational innovation, how appropriability regimes affect trade secret use, technology investments, and product innovation across energy and digital platforms."
    },
    "Wesley Koo": {
        "method": "Quantitative/Mixed",
        "topics": ["Platform governance", "Rural-urban divide", "Digital entrepreneurship", "Return migration", "Social ventures", "Algorithmic change"],
        "theories": ["Platform Theory", "Institutional Theory", "Entrepreneurship Theory", "Digital Transformation"],
        "publications": [
            "Platform governance and the rural–urban divide",
            "Take me home, country roads: Return migration",
            "From margins to mainstream: The narrative dilemma",
            "Innovation on wings: Nonstop flights and firm innovation"
        ],
        "summary": "Studies platform governance, digital entrepreneurship in rural contexts, and how technology affects marginalized populations."
    },
    "Wesley W. Koo": {
        "method": "Quantitative/Mixed",
        "topics": ["Platform governance", "Rural-urban divide", "Digital entrepreneurship", "Return migration", "Social ventures", "Algorithmic change"],
        "theories": ["Platform Theory", "Institutional Theory", "Entrepreneurship Theory", "Digital Transformation"],
        "publications": [
            "Platform governance and the rural–urban divide",
            "Take me home, country roads: Return migration",
            "From margins to mainstream: The narrative dilemma",
            "Innovation on wings: Nonstop flights and firm innovation"
        ],
        "summary": "Studies platform governance, digital entrepreneurship in rural contexts, and how technology affects marginalized populations."
    },
    "Catherine Magelssen": {
        "method": "Quantitative",
        "topics": ["Multinational firm strategy", "Property rights allocation", "Technology innovation", "Tax avoidance and IP", "Subsidiary governance", "Corporate philanthropy"],
        "theories": ["Property Rights Theory", "Resource-Based View", "Transaction Cost Economics", "Internalization Theory"],
        "publications": [
            "Allocation of property rights and technological innovation within firms",
            "Institutional Disruptions and the Philanthropy of Multinational Firms",
            "The contractual governance of transactions within firms",
            "Outsourcing and insourcing of organizational activities"
        ],
        "summary": "Examines how multinationals govern internal transactions and allocate IP ownership rights, using confidential intra-firm data."
    },
    "Anparasan Mahalingam": {
        "method": "Quantitative",
        "topics": ["Digital corporate strategy", "Platform governance", "Platform gatekeeping", "Firm boundaries", "Online lending", "Decision rights allocation"],
        "theories": ["Platform Theory", "Organizational Economics", "Transaction Cost Economics", "Market Design"],
        "publications": [
            "Corporate Strategies of Digital Organizations",
            "How Platform Gatekeeping Affects Complementors' Strategy",
            "Decision Right Allocation and Platform Market Effectiveness"
        ],
        "summary": "Studies digitization's implications for corporate strategy, platform gatekeeping, decision rights, and market frictions in digital organizations."
    },
    "Francisco Morales": {
        "method": "Quantitative",
        "topics": ["Strategic human capital", "Skilled immigration", "Employee mobility", "International business", "Private equity in emerging markets", "Signaling"],
        "theories": ["Strategic Human Capital Theory", "Signaling Theory", "Uppsala Model", "Social Network Theory"],
        "publications": [
            "Does Employing Skilled Immigrants Enhance Competitive Performance?",
            "The impact of experience on the agglomeration of cross-border investments",
            "Attracting Knowledge Workers to High-tech Ventures: A Signaling Perspective"
        ],
        "summary": "Examines innovation and strategic human capital, how firms benefit from managing talent globally, skilled immigration effects on competitive performance."
    },
    "FJ Morales": {
        "method": "Quantitative",
        "topics": ["Strategic human capital", "Skilled immigration", "Employee mobility", "International business", "Private equity in emerging markets", "Signaling"],
        "theories": ["Strategic Human Capital Theory", "Signaling Theory", "Uppsala Model", "Social Network Theory"],
        "publications": [
            "Does Employing Skilled Immigrants Enhance Competitive Performance?",
            "The impact of experience on the agglomeration of cross-border investments",
            "Attracting Knowledge Workers to High-tech Ventures: A Signaling Perspective"
        ],
        "summary": "Examines innovation and strategic human capital, how firms benefit from managing talent globally, skilled immigration effects on competitive performance."
    },
    "Metin Sengul": {
        "method": "Quantitative",
        "topics": ["Organization design", "Multiunit-multimarket firms", "Cognitive drivers of design", "Dual-purpose companies", "Delegation and control", "Capital allocation"],
        "theories": ["Organization Design Theory", "Behavioral Theory of the Firm", "Cognitive Theories", "Transaction Cost Economics"],
        "publications": [
            "Organization design: Current insights and future research directions",
            "Ownership as a bundle of rights",
            "A socio-cognitive explanation of organizational grouping decisions",
            "The allocation of capital within firms"
        ],
        "summary": "Studies organization design in complex orgs, how design varies with competitive context and cognitive processes, dual-purpose companies balancing financial and social objectives."
    },
    "Xiaoli Tang": {
        "method": "Quantitative/Mixed",
        "topics": ["Accountable secrecy", "Transparency and disclosure", "Self-regulation", "Environmental disclosure", "Extractive industries", "Hydraulic fracturing"],
        "theories": ["Institutional Theory", "Stakeholder Theory", "Innovation Theory", "Nonmarket Strategy"],
        "publications": [
            "Self-regulation, Corruption, and Competitiveness in Extractive Industries",
            "Accountable Secrecy: Public Scrutiny, Market Power, and Safer Chemistry",
            "Self-Regulation in Weak Institutional Environments",
            "Seeing Through the Fog: Cognitive Capabilities and M&As"
        ],
        "summary": "Examines how corporations navigate conflicting stakeholder demands using 'accountable secrecy' - designing disclosure rules that balance safety with protecting know-how."
    },
    "Andy Wu": {
        "method": "Quantitative/Mixed",
        "topics": ["Entrepreneurship", "Innovation", "Platform ecosystems", "AI and data-driven learning", "Organizational design", "Entrepreneurial learning"],
        "theories": ["Organizational Design Theory", "Platform Theory", "Entrepreneurship Theory", "Behavioral Theory"],
        "publications": [
            "The Gen AI Playbook for Organizations",
            "Iterative Coordination and Innovation",
            "Entrepreneurial Learning and Strategic Foresight",
            "Artificial Intelligence, Data-Driven Learning, and the Decentralized Structure",
            "Platform Diffusion at Temporary Gatherings"
        ],
        "summary": "Studies how managers compete and adapt to technology, platform ecosystems, AI-driven learning, iterative coordination, and knowledge production teams."
    },
    "Mingtao Xu": {
        "method": "Quantitative",
        "topics": ["AI and Strategy", "Machine learning and organizational learning", "Property rights", "Patent litigation", "Patent monetization", "Entrepreneurial financing", "GPT-enabled startups"],
        "theories": ["Property Rights Theory", "Organizational Learning", "Organizational Economics", "Resource-Based View"],
        "publications": [
            "Substituting Human Decision-Making with Machine Learning",
            "How Property Rights Matter to Firm Resource Investment",
            "Property Rights and Firm Scope",
            "Why DeepSeek Shouldn't Have Been a Surprise"
        ],
        "summary": "Studies how AI changes organizations, how property rights shape firm behavior, and patent litigation implications. Three streams: AI & Strategy, Property Rights, Patent Litigation."
    },
    "Tony Tong": {
        "method": "Mixed",
        "topics": ["Strategy", "Innovation", "International business", "Real options", "Firm scope", "Property rights"],
        "theories": ["Real Options Theory", "Resource-Based View", "Organizational Economics"],
        "publications": [
            "Property Rights and Firm Scope",
            "How Property Rights Matter to Firm Resource Investment",
            "Review of Real Options Theory"
        ],
        "summary": "Broad expertise in strategy, innovation, and international business. Co-authored on property rights, firm scope, and patent litigation."
    }
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
    profile: dict  # Full profile from REVIEWER_PROFILES
    max_papers: int
    
    @classmethod
    def from_firebase(cls, rid: str, data: dict) -> 'Reviewer':
        name = data.get('name', 'Unknown')
        
        # Get detailed profile
        profile = REVIEWER_PROFILES.get(name, {
            "method": "Mixed",
            "topics": [],
            "theories": [],
            "publications": [],
            "summary": "General expertise"
        })
        
        return cls(
            id=rid,
            name=name,
            email=data.get('email', ''),
            method=profile.get('method', 'Mixed'),
            profile=profile,
            max_papers=int(data.get('maxPapers', 0))
        )


def query_llm(prompt: str, max_tokens: int = 150) -> str:
    """Query Ollama with prompt."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": max_tokens}
            },
            timeout=90
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
    except Exception as e:
        print(f"      ⚠ LLM error: {e}")
    return ""


def score_paper_reviewer_pair(paper: Paper, reviewer: Reviewer) -> tuple:
    """
    Score a single paper-reviewer pair using LLM with detailed profiles.
    Returns (score: int 0-100, reason: str)
    """
    profile = reviewer.profile
    topics = ", ".join(profile.get('topics', [])[:8])
    theories = ", ".join(profile.get('theories', [])[:4])
    publications = "\"" + "\", \"".join(profile.get('publications', [])[:3]) + "\""
    summary = profile.get('summary', '')
    
    # Increase abstract limit to 4000 chars (approx 600 words)
    abstract_text = paper.abstract[:4000] if paper.abstract else 'N/A'
    
    prompt = f"""You are matching a paper to a reviewer for an academic conference. Be STRICT and DIFFERENTIATED with scores.

PAPER:
Title: {paper.title}
Keywords: {paper.keywords}
Abstract excerpt: {abstract_text}

REVIEWER: {reviewer.name}
Method: {reviewer.method}
Research Topics: {topics}
Theoretical Frameworks: {theories}
Notable Publications: {publications}
Research Focus: {summary}

SCORING GUIDE (be strict!):
- 90-100: PERFECT match - Paper's topic IS the reviewer's specialty area
- 75-89: STRONG match - Significant overlap in topics AND theories
- 60-74: MODERATE match - Some topic overlap OR theory alignment
- 40-59: WEAK match - Tangential connection only
- 20-39: POOR match - Little relevant expertise
- 0-19: NO match - Completely different field

Evaluate:
1. Does the paper's TOPIC directly match reviewer's research areas and publications?
2. Does the paper use THEORIES the reviewer has published on?
3. Is the METHODOLOGY compatible?

RESPOND EXACTLY: SCORE: [number] | REASON: [one specific sentence explaining why]"""

    response = query_llm(prompt, max_tokens=150)
    
    # Parse score
    score = 50  # Default moderate
    reason = ""
    
    if 'SCORE:' in response.upper():
        try:
            score_match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
            if score_match:
                score = min(100, max(0, int(score_match.group(1))))
            
            reason_match = re.search(r'REASON:\s*(.+)', response, re.IGNORECASE)
            if reason_match:
                reason = reason_match.group(1).strip()[:100]
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
            topics_count = len(reviewer.profile.get('topics', []))
            pubs_count = len(reviewer.profile.get('publications', []))
            print(f"   ✓ {reviewer.name}: {reviewer.method} | Topics: {topics_count} | Pubs: {pubs_count}")
        
            reviewers[rid] = reviewer
        
        print(f"   ✓ Loaded {len(reviewers)} reviewers with detailed profiles")
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
    return True


def classify_method_simple(paper: Paper) -> str:
    text = f"{paper.title} {paper.abstract} {paper.keywords}".lower()
    
    quant_words = ['regression', 'econometric', 'statistical', 'empirical', 
                   'quantitative', 'panel data', 'survey', 'sample', 'dataset']
    qual_words = ['case study', 'interview', 'ethnograph', 'qualitative', 'grounded theory']
    
    quant_count = sum(1 for w in quant_words if w in text)
    qual_count = sum(1 for w in qual_words if w in text)
    
    if quant_count > 2:
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
    print("Strategy Science 2026 - PAIRWISE LLM Assignment V3")
    print("=" * 70)
    print("Using DETAILED profiles + PUBLICATIONS + LONG ABSTRACTS")
    print(f"Model: {OLLAMA_MODEL}")
    
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
    
    total_pairs = len(papers) * len(reviewers)
    print(f"\n⏱ Estimated: {total_pairs} LLM calls (~{total_pairs * 3 / 60:.0f} minutes)")
    
    # Classify methods
    print("\n" + "=" * 70)
    print("PHASE 1: Classifying paper methods")
    print("=" * 70)
    for paper in papers:
        paper.method = classify_method_simple(paper)
        print(f"   {paper.id}: {paper.method}")
    
    # Pairwise scoring
    print("\n" + "=" * 70)
    print("PHASE 2: PAIRWISE LLM Scoring (detailed profiles)")
    print("=" * 70)
    
    assignments = defaultdict(list)
    current_load = defaultdict(int)
    scores_log = {}
    
    for i, paper in enumerate(papers):
        paper_start = time.time()
        elapsed_total = time.time() - start_time
        
        print(f"\n[{i+1}/{len(papers)}] {paper.id}: {paper.title[:45]}...")
        # Show actual abstract length being used
        abstract_len = len(paper.abstract) if paper.abstract else 0
        used_len = min(abstract_len, 4000)
        print(f"    Abstract: {used_len} chars (Total: {abstract_len})")
        
        # Get available reviewers
        available = []
        for rid, reviewer in reviewers.items():
            if not method_matches(paper.method, reviewer.method):
                continue
            if reviewer.max_papers > 0 and current_load[rid] >= reviewer.max_papers:
                continue
            available.append((rid, reviewer))
        
        print(f"    Available: {len(available)} reviewers")
        
        if len(available) < 2:
            print(f"    ⚠ Not enough reviewers!")
            continue
        
        # Score each reviewer
        pair_scores = {}
        for j, (rid, reviewer) in enumerate(available):
            score, reason = score_paper_reviewer_pair(paper, reviewer)
            pair_scores[rid] = score
            
            # Color code scores
            if score >= 80:
                indicator = "🟢"
            elif score >= 60:
                indicator = "🟡"
            else:
                indicator = "🔴"
            
            print(f"      [{j+1}/{len(available)}] {indicator} {reviewer.name}: {score}", end="")
            if reason:
                print(f" - {reason[:45]}...")
            else:
                print()
        
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
        papers_remaining = len(papers) - i - 1
        est_remaining = paper_time * papers_remaining / 60
        print(f"    ⏱ {paper_time:.0f}s | Est. remaining: {est_remaining:.0f}min")
        
        # Checkpoint
        if (i + 1) % 5 == 0:
            save_assignments(assignments, papers, reviewers, scores_log, OUTPUT_CSV)
            print(f"    💾 Saved checkpoint")
    
    # Final save
    print("\n" + "=" * 70)
    print("PHASE 3: Final Results")
    print("=" * 70)
    
    save_assignments(assignments, papers, reviewers, scores_log, OUTPUT_CSV)
    
    # Load distribution
    print("\nReviewer load distribution:")
    for rid, reviewer in sorted(reviewers.items(), key=lambda x: current_load.get(x[0], 0), reverse=True):
        load = current_load.get(rid, 0)
        if load > 0:
            bar = "█" * min(load, 10) + "░" * max(0, 10 - load)
            print(f"   {reviewer.name:25} [{bar}] {load}")
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Total time: {total_time/60:.1f} minutes")
    print(f"✓ Papers: {len(papers)} | LLM calls: ~{len(papers) * len(reviewers)}")
    print(f"✓ Output: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
