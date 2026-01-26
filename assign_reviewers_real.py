#!/usr/bin/env python3
"""
Strategy Science Conference 2026 - REAL DATA HYBRID ASSIGNMENT
"HYBRID" strategy for speed:
1. Filter candidates by Keyword Similarity (Jaccard)
2. Score only TOP candidates with LLM
3. Global Optimization for final Assignment
"""

import csv
import json
import re
import requests
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
import time
import math
import os

# =====================
# CONFIGURATION
# =====================
INPUT_CSV = "papers_real.csv"
OUTPUT_CSV = "assignments_real.csv"
TEST_MODE = None  # None for all
CANDIDATES_PER_PAPER = 4  # Score top 4 matches with LLM

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"
FIREBASE_DB_URL = "https://strategyscience2026-default-rtdb.firebaseio.com"

# =====================
# DETAILED REVIEWER PROFILES
# =====================
REVIEWER_PROFILES = {
    "Janet Bercovitz": {
        "method": "Quantitative",
        "topics": ["Academic entrepreneurship", "Technology transfer", "University-industry relationships", "Knowledge worker mobility", "Industrial clusters", "Organizational change"],
        "theories": ["Transaction Cost Economics", "Organizational Learning", "Social Learning", "Resource-Based View"],
        "publications": ["Entrepreneurial universities and technology transfer", "Academic entrepreneurs", "Creating a cluster while building a firm", "Complementarity and evolution of contractual provisions"],
        "summary": "Studies academic entrepreneurship, university tech transfer, inter-organizational contracts, and knowledge-based economic development."
    },
    "Janet Lee Elsie Bercovitz": {
        "method": "Quantitative",
        "topics": ["Academic entrepreneurship", "Technology transfer", "University-industry relationships", "Knowledge worker mobility", "Industrial clusters"],
        "theories": ["Transaction Cost Economics", "Organizational Learning", "Resource-Based View"],
        "publications": ["Entrepreneurial universities and technology transfer", "Academic entrepreneurs"],
        "summary": "Studies academic entrepreneurship, university tech transfer, inter-organizational contracts."
    },
    "Danielle Bovenberg": {
        "method": "Qualitative",
        "topics": ["Innovation in high-tech", "Knowledge diffusion", "Scientific support staff", "Craft knowledge", "Nanofabrication", "Core research facilities"],
        "theories": ["Craft Knowledge Theory", "Structural Complexity", "Organizational Theory", "Occupational Sociology"],
        "publications": ["Craft Knowledge and the Advancement of Science", "The Role of Scientific Support Occupations"],
        "summary": "Qualitative researcher studying craft knowledge, technical intermediaries, and knowledge spillovers in technology industries. Uses ethnographic methods."
    },
    "Mukund Chari": {
        "method": "Quantitative",
        "topics": ["Intellectual property rights", "Patent systems", "Patent assertion entities", "Inventor behavior", "Patent quality", "Licensing"],
        "theories": ["Transaction Cost Economics", "Agency Theory", "Professional Identity Theory"],
        "publications": ["The influence of patent assertion entities", "A Comparative Analysis of Patent Assertion Entities", "Quest For Expansive IP Rights"],
        "summary": "Examines IP management, patent intermediation, and how institutional factors influence innovation and inventor behavior."
    },
    "Ashton Hawk": {
        "method": "Quantitative",
        "topics": ["Investment speed", "Time compression diseconomies", "Political capital", "Alliance partner selection", "Entry timing", "Fast-mover advantages"],
        "theories": ["Resource-Based View", "Dynamic Capabilities", "Time Compression Diseconomies"],
        "publications": ["The half-life of political capital", "Time Compression (Dis)Economies", "The right speed and its value", "Fast-Mover Advantages"],
        "summary": "Studies temporal dynamics in strategy, investment speed, and how firms' capabilities affect competitive advantage over time."
    },
    "Sina Sokhan": {
        "method": "Quantitative",
        "topics": ["Innovation process", "Knowledge recombination", "IP rights and innovation", "Pharmaceutical innovation", "Antibiotic development", "Commercialization costs"],
        "theories": ["Knowledge Recombination Theory", "Intellectual Property Theory", "Innovation Economics"],
        "publications": ["Innovation process and knowledge recombination", "Intellectual property rights and innovation", "Pharmaceutical innovation"],
        "summary": "Examines what enables, constrains, and causes innovation to fail. Focus on pharma innovation and IP."
    },
    "MJ Yang": {
        "method": "Quantitative/Mixed",
        "topics": ["CEO strategic decision-making", "Technological uniqueness", "Industrial AI adoption", "Complementarities", "R&D capital", "Organizational design"],
        "theories": ["Complementarity Theory", "Resource-Based View", "Dynamic Capabilities"],
        "publications": ["How Do CEOs Make Strategy?", "The Technological Uniqueness Paradox", "Complementarity of Task Allocation"],
        "summary": "Examines drivers of firm performance gaps, strategy processes, technological positioning, and complementarities."
    },
    "Kenneth Huang": {
        "method": "Quantitative/Mixed",
        "topics": ["IP strategy", "Innovation in China", "Patent trolls/NPEs", "State-owned enterprises", "Government policy and innovation", "Knowledge worker mobility", "Green innovation"],
        "theories": ["Institutional Theory", "Knowledge-Based View", "Resource-Based View", "Innovation Economics"],
        "publications": ["Does Patent Strategy Shape Supply of Public Knowledge?", "Public Governance, Corporate Governance and Firm Innovation", "Escaping Patent Trolls"],
        "summary": "Studies IP strategy, innovation in emerging economies, institutions and government policy shaping innovation."
    },
    "Aldona Kapacinskaite": {
        "method": "Quantitative",
        "topics": ["Trade secrets", "Appropriability", "Platform competition", "Resource redeployment", "Patent licensing", "Digital platforms", "Energy transition"],
        "theories": ["Resource-Based View", "Appropriability Theory", "Platform Theory"],
        "publications": ["Keeping Invention Confidential", "Competing with the platform", "From Wells to Windmills"],
        "summary": "Examines organizational innovation, how appropriability regimes affect trade secret use, technology investments, and platforms."
    },
    "Wesley Koo": {
        "method": "Quantitative/Mixed",
        "topics": ["Platform governance", "Rural-urban divide", "Digital entrepreneurship", "Return migration", "Social ventures", "Algorithmic change"],
        "theories": ["Platform Theory", "Institutional Theory", "Entrepreneurship Theory", "Digital Transformation"],
        "publications": ["Platform governance and the rural–urban divide", "Take me home, country roads", "From margins to mainstream"],
        "summary": "Studies platform governance, digital entrepreneurship in rural contexts, and technology for marginalized populations."
    },
    "Catherine Magelssen": {
        "method": "Quantitative",
        "topics": ["Multinational firm strategy", "Property rights allocation", "Technology innovation", "Tax avoidance and IP", "Subsidiary governance", "Corporate philanthropy"],
        "theories": ["Property Rights Theory", "Resource-Based View", "Transaction Cost Economics"],
        "publications": ["Allocation of property rights", "Institutional Disruptions and Philanthropy", "Contractual governance within firms"],
        "summary": "Examines how multinationals govern internal transactions and allocate IP ownership rights."
    },
    "Anparasan Mahalingam": {
        "method": "Quantitative",
        "topics": ["Digital corporate strategy", "Platform governance", "Platform gatekeeping", "Firm boundaries", "Online lending", "Decision rights allocation"],
        "theories": ["Platform Theory", "Organizational Economics", "Transaction Cost Economics"],
        "publications": ["Corporate Strategies of Digital Organizations", "Platform Gatekeeping", "Decision Right Allocation"],
        "summary": "Studies digitization's implications for corporate strategy, platform decision rights, and market frictions."
    },
    "Francisco Morales": {
        "method": "Quantitative",
        "topics": ["Strategic human capital", "Skilled immigration", "Employee mobility", "International business", "Private equity in emerging markets", "Signaling"],
        "theories": ["Strategic Human Capital Theory", "Signaling Theory", "Uppsala Model"],
        "publications": ["Does Employing Skilled Immigrants Enhance Performance?", "Impact of experience on cross-border investments", "Attracting Knowledge Workers"],
        "summary": "Examines innovation and strategic human capital, skilled immigration effects on competitive performance."
    },
    "Metin Sengul": {
        "method": "Quantitative",
        "topics": ["Organization design", "Multiunit-multimarket firms", "Cognitive drivers of design", "Dual-purpose companies", "Delegation and control", "Capital allocation"],
        "theories": ["Organization Design Theory", "Behavioral Theory of the Firm", "Transaction Cost Economics"],
        "publications": ["Organization design: Current insights", "Ownership as a bundle of rights", "Socio-cognitive explanation of grouping"],
        "summary": "Studies organization design in complex orgs, cognitive processes, and dual-purpose companies."
    },
    "Xiaoli Tang": {
        "method": "Quantitative/Mixed",
        "topics": ["Accountable secrecy", "Transparency and disclosure", "Self-regulation", "Environmental disclosure", "Extractive industries", "Hydraulic fracturing"],
        "theories": ["Institutional Theory", "Stakeholder Theory", "Innovation Theory", "Nonmarket Strategy"],
        "publications": ["Self-regulation, Corruption, and Competitiveness", "Accountable Secrecy", "Self-Regulation in Weak Institutional Environments"],
        "summary": "Examines how corporations navigate conflicting stakeholder demands using 'accountable secrecy'."
    },
    "Andy Wu": {
        "method": "Quantitative/Mixed",
        "topics": ["Entrepreneurship", "Innovation", "Platform ecosystems", "AI and data-driven learning", "Organizational design", "Entrepreneurial learning"],
        "theories": ["Organizational Design Theory", "Platform Theory", "Entrepreneurship Theory"],
        "publications": ["The Gen AI Playbook", "Iterative Coordination and Innovation", "Entrepreneurial Learning and Strategic Foresight"],
        "summary": "Studies how managers compete and adapt to technology, platform ecosystems, AI-driven learning, and knowledge production."
    },
    "Mingtao Xu": {
        "method": "Quantitative",
        "topics": ["AI and Strategy", "Machine learning and organizational learning", "Property rights", "Patent litigation", "Patent monetization", "Entrepreneurial financing"],
        "theories": ["Property Rights Theory", "Organizational Learning", "Organizational Economics"],
        "publications": ["Substituting Human Decision-Making", "How Property Rights Matter to Firm Resource Investment", "Property Rights and Firm Scope"],
        "summary": "Studies how AI changes organizations, how property rights shape firm behavior, and patent litigation."
    },
    "Tony Tong": {
        "method": "Mixed",
        "topics": ["Strategy", "Innovation", "International business", "Real options", "Firm scope", "Property rights"],
        "theories": ["Real Options Theory", "Resource-Based View", "Organizational Economics"],
        "publications": ["Property Rights and Firm Scope", "How Property Rights Matter to Firm Resource Investment", "Review of Real Options Theory"],
        "summary": "Broad expertise in strategy, innovation, and international business."
    }
}

@dataclass
class Paper:
    id: str
    title: str
    abstract: str
    keywords: str
    method: Optional[str] = None
    keyword_set: Set[str] = field(default_factory=set)

    def __post_init__(self):
        self.keyword_set = self._extract_keywords()

    def _extract_keywords(self) -> Set[str]:
        words = set()
        if self.keywords:
            for kw in self.keywords.lower().split(","):
                kw = kw.strip()
                if len(kw) > 2:
                    words.add(kw)
                    for w in kw.split():
                        if len(w) > 3: words.add(w)
        if self.abstract:
            stopwords = {"the", "and", "for", "with", "that", "this", "from", "paper", "study", "results", "using", "data"}
            abstract_words = re.findall(r"[a-z]+", self.abstract.lower())
            for w in abstract_words:
                if len(w) > 4 and w not in stopwords:
                    words.add(w)
        return words

@dataclass
class Reviewer:
    id: str
    name: str
    method: str
    profile: dict
    keyword_set: Set[str] = field(default_factory=set)
    
    @classmethod
    def from_firebase(cls, rid: str, data: dict) -> 'Reviewer':
        name = data.get('name', 'Unknown')
        profile = REVIEWER_PROFILES.get(name)
        
        # Fallback profile search
        if not profile:
             for k, v in REVIEWER_PROFILES.items():
                 if name in k or k in name:
                     profile = v
                     break
        if not profile:
             profile = {"method": "Mixed", "topics": [], "theories": [], "publications": [], "summary": "General"}
             
        # Build keyword set from profile
        kw_set = set()
        for t in profile.get('topics', []):
            for w in t.lower().split():
                if len(w) > 3: kw_set.add(w)
        for t in profile.get('theories', []):
             for w in t.lower().split():
                if len(w) > 3: kw_set.add(w)
        
        return cls(id=rid, name=name, method=profile.get('method', 'Mixed'), profile=profile, keyword_set=kw_set)

def load_reviewers_local() -> Dict[str, Reviewer]:
    reviewers = {}
    print(f"   (Using local profiles for {len(REVIEWER_PROFILES)} reviewers)")
    for name, profile in REVIEWER_PROFILES.items():
        # Generate a deterministic ID based on name hash or just use name as ID for internal logic?
        # The system expects secure IDs (REV-XXX).
        # We can try to fetch from Firebase if possible, OR just generate fresh ones.
        # But we need consistent IDs if we want to import them?
        # Actually, let's just use the Name as the Key for assignments if we can't get IDs.
        # But index.html expects IDs.
        
        # fallback: Generate a consistent ID hash
        # rid = "REV-" + "".join([c for c in name if c.isalnum()]).upper()[:8]
        # Better: we need valid IDs. 
        # Since Firebase is empty, we must assume the User will Reload Reviewers in UI.
        # The CSV import uses NAMES to map to IDs. So the specific ID here doesn't matter for the CSV output!
        # The CSV output has 'reviewer_1', 'reviewer_2' as NAMES.
        
        rid = "REV-" + str(abs(hash(name)) % 100000)
        
        # Build keyword set
        kw_set = set()
        for t in profile.get('topics', []):
            for w in t.lower().split():
                if len(w) > 3: kw_set.add(w)
        for t in profile.get('theories', []):
             for w in t.lower().split():
                if len(w) > 3: kw_set.add(w)
                
        reviewers[rid] = Reviewer(
            id=rid,
            name=name,
            method=profile.get('method', 'Mixed'),
            profile=profile,
            keyword_set=kw_set
        )
    return reviewers

def load_reviewers_from_firebase() -> Dict[str, Reviewer]:
    # fallback to local
    return load_reviewers_local()

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

def query_llm(prompt: str, max_tokens: int = 150) -> str:
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

def calculate_keyword_similarity(paper: Paper, reviewer: Reviewer) -> float:
    if not paper.keyword_set or not reviewer.keyword_set: return 0.0
    overlap = paper.keyword_set & reviewer.keyword_set
    if len(reviewer.keyword_set) == 0: return 0.0
    # Weighted score
    return (len(overlap) / len(reviewer.keyword_set)) + (len(overlap) * 0.05)

def score_paper_reviewer_pair_llm(paper: Paper, reviewer: Reviewer) -> tuple:
    profile = reviewer.profile
    topics = ", ".join(profile.get('topics', [])[:8])
    summary = profile.get('summary', '')
    abstract_text = paper.abstract[:3000] if paper.abstract else 'N/A'
    
    prompt = f"""Match academic paper to reviewer. STRICT SCORING.

PAPER: {paper.title}
Key Terms: {paper.keywords}
Abstract Excerpt: {abstract_text}

REVIEWER: {reviewer.name}
Interests: {topics}
Summary: {summary}

SCORING (0-100):
90+: Perfect expertise match
70-89: Strong overlap
50-69: Some overlap
<50: Weak/No match

Reply format: SCORE: [num] | REASON: ..."""

    response = query_llm(prompt, max_tokens=50)
    score = 40
    reason = "Default"
    
    if 'SCORE:' in response.upper():
        try:
            m = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
            if m: score = int(m.group(1))
            m2 = re.search(r'REASON:\s*(.+)', response, re.IGNORECASE)
            if m2: reason = m2.group(1).strip()
        except: pass
    return score, reason

def classify_method_llm(paper: Paper) -> str:
    text = paper.abstract[:1500] if paper.abstract else paper.title
    prompt = f"""Classify the research method of this academic paper based on its abstract.
    
    Abstract: "{text}"
    
    Choose exactly one category:
    1. Quantitative (Uses statistics, regression, large datasets, experiments, models)
    2. Qualitative (Uses case studies, interviews, ethnography, grounded theory)
    3. Conceptual (Theoretical, no empirical data, reviewing literature, identifying gaps)
    4. Mixed (Explicitly combines BOTH quantitative validation AND qualitative case studies)
    
    Most papers are Quantitative or Conceptual. 'Mixed' is rare. 'Qualitative' is specific.
    
    Reply with JUST the category name (e.g. "Quantitative")."""
    
    response = query_llm(prompt, max_tokens=10)
    response = response.strip().lower()
    
    if 'quantitative' in response: return 'Quantitative'
    if 'qualitative' in response: return 'Qualitative'
    if 'conceptual' in response: return 'Conceptual'
    if 'mixed' in response: return 'Mixed'
    
    # Fallback to simple keyword check if LLM fails
    if any(w in text.lower() for w in ['regression', 'data', 'sample', 'empirical']): return 'Quantitative'
    return 'Conceptual' # Safe default for strategy

def method_matches(paper_method: str, reviewer_method: str) -> bool:
    paper_method = (paper_method or '').lower()
    reviewer_method = (reviewer_method or '').lower()
    
    # Mixed reviewers can do anything
    if 'mixed' in reviewer_method: return True
    
    # Quantitative Reviewers
    if 'quantitative' in reviewer_method:
        return paper_method in ['quantitative', 'mixed'] # Can likely handle mixed if it has quant
        
    # Qualitative Reviewers
    if 'qualitative' in reviewer_method:
        return paper_method in ['qualitative', 'mixed', 'conceptual'] # Qual reviewers often good at Conceptual/Theory
        
    return True # Default safe match

def save_output(assignments, papers, reviewers, scores, path):
    paper_map = {p.id: p for p in papers}
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['paper_id', 'title', 'method', 'reviewer_1', 'reviewer_2', 'score_1', 'score_2'])
        for pid in sorted(paper_map.keys()):
            p = paper_map[pid]
            revs = assignments[pid]
            r1 = reviewers[revs[0]].name if len(revs) > 0 else ''
            r2 = reviewers[revs[1]].name if len(revs) > 1 else ''
            s1 = scores.get(pid, {}).get(revs[0], 0) if len(revs) > 0 else 0
            s2 = scores.get(pid, {}).get(revs[1], 0) if len(revs) > 1 else 0
            writer.writerow([pid, p.title[:60], p.method, r1, r2, s1, s2])

def main():
    print("Strategy Science 2026 - HYBRID ASSIGNMENT (Fast)")
    start = time.time()
    
    reviewers = load_reviewers_from_firebase()
    papers = load_papers(INPUT_CSV)
    if TEST_MODE: papers = papers[:TEST_MODE]
    
    print(f"Loaded {len(papers)} papers, {len(reviewers)} reviewers")
    
    # 1. Method Classification
    print("\nPhase 1: LLM Method Classification...")
    for i, p in enumerate(papers):
        p.method = classify_method_llm(p)
        print(f"   [{i+1}/{len(papers)}] {p.id}: {p.method}")
    
    # 2. Hybrid Scoring
    print("\nPhase 2: Hybrid Scoring (Keyword Filter -> LLM)")
    all_scores = [] # (pid, rid, score)
    scores_log = defaultdict(dict)
    
    for i, p in enumerate(papers):
        print(f"[{i+1}/{len(papers)}] {p.id}: {p.title[:40]}...")
        
        # A. Keyword Candidates
        candidates = []
        for rid, r in reviewers.items():
            if method_matches(p.method, r.method):
                sim = calculate_keyword_similarity(p, r)
                candidates.append((rid, sim))
        
        # Sort by keyword sim, take top N
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:CANDIDATES_PER_PAPER]
        
        print(f"   Candidates: {[reviewers[c[0]].name for c in top_candidates]}")
        
        # B. Score Top Candidates with LLM
        for rid, sim in top_candidates:
            score, reason = score_paper_reviewer_pair_llm(p, reviewers[rid])
            all_scores.append((p.id, rid, score))
            scores_log[p.id][rid] = score
            if score > 70: print(f"    ✨ {reviewers[rid].name}: {score}")
            
    # 3. Assignment
    print("\nPhase 3: Global Assignment")
    assignments = defaultdict(list)
    reviewer_load = defaultdict(int)
    needed = 2
    
    all_scores.sort(key=lambda x: x[2], reverse=True)
    avg_load = math.ceil((len(papers)*2)/len(reviewers))
    
    for pid, rid, score in all_scores:
        if len(assignments[pid]) >= needed: continue
        if reviewer_load[rid] >= avg_load + 1: continue # Cap
        
        assignments[pid].append(rid)
        reviewer_load[rid] += 1
        
    save_output(assignments, papers, reviewers, scores_log, OUTPUT_CSV)
    print(f"\nDone! {(time.time()-start)/60:.1f} min. Saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
