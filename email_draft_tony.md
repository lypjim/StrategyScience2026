
Subject: Strategy Science: Review System Admin Portal & Assignment Workflow (Draft)

Hi Tony,

I have developed the initial version of the Review Management System to assist with the Strategy Science 2026 conference review process.

This email outlines the current system capabilities, the automated assignment workflow, and a few items I could use your input on.

## 1. Web-Based Admin Portal

I have built a secure web interface for managing the entire process.
**URL:** [Hosted Link - TBD] (Currently running locally)

**Key Features:**

* **Papers Tab:** View all submitted papers. Supports CSV import/export.
* **Reviewers Tab:** Manage committee members. I have pre-populated this with the 17 members from your provided list, including their methods (Quant/Qual/Mixed) and expertise keywords.
* **Assignments Tab:**
  * **Auto-assignment:** Run the matching algorithm (see below) and import results.
  * **Manual Adjustment:** Drag-and-drop or click to reassign papers.
  * **Conflict Detection:** Automatically flags potential conflicts (e.g., if a reviewer is assigned >5 papers).
  * **Workload Visualization:** Bar charts showing how many papers each reviewer has.
  * **Link Generation:** unique review links for each reviewer (e.g., `?reviewer=Tony+Tong`).
* **Results Tab:**
  * **Decision Support:** Aggregates scores (Yes=4, Maybe Yes=3, Maybe No=2, No=1).
  * **Ranking:** Autocalculates average scores.
  * **Conflict Flagging:** Highlights papers with high variance (e.g., one "Yes" and one "No").
  * **Acceptance:** "Accept Top X" feature to bulk-accept top-ranked papers.

## 2. Reviewer Interface

Each reviewer gets a simple, personal link. No login required.

* They see *only* their assigned papers.
* They can download the PDF (via secure link).
* **Scoring:** Simple 4-point scale: **Yes**, **Maybe Yes**, **Maybe No**, **No**.
* **Comments:** Optional text box for confidential comments to the chair.

## 3. Automated Assignment Workflow (Python)

I have created a sophisticated Python pipeline to handle the heavy lifting of matching papers to reviewers.

**Step 1: Paper Processing**

* **Input:** Folder of PDF files.
* **Method:** Uses `Qwen2.5-7B` (Large Language Model) to read each PDF.
* **Extraction:** Automatically extracts Title, **Full Abstract**, and Keywords.
* **Accuracy:** I improved the script to capture long abstracts (~500+ words) to ensure no critical info is lost.

**Step 2: Intelligent Matching (True Pairwise)**
To ensure high-quality matches, I moved away from simple keyword matching to a **Semantic Understanding** model:

* **Deep Analysis:** The AI evaluates *every* Paper-Reviewer pair individually.
* **Rich Profiles:** It uses the detailed research profiles (methods, specific theories, topics, and notable publications) you provided.
* **Scoring:** It assigns a compatibility score (0-100) based on:
  * **Topic Match:** Does the paper fit their specific research stream?
  * **Theoretical Fit:** Does it use theories they know/use?
  * **Method Match:** (e.g., Qualitative papers go to Qualitative experts).
* **Load Balancing:** Optimizes assignments to respect maximum capacity (e.g., max 5 papers/reviewer).

## 4. Next Steps & Requests

1. **Reviewer Data Validation:** I have entered the 17 committee members. Please let me know if any email addresses or capacities need updating.
2. **Test Papers:** If you have any sample/past anonymized PDFs, I can run them through the system to demonstrate the matching quality.
3. **Deployment:** I can host this on a private server password-protected for your use.

Let me know if you would like a demo or any changes to the workflow.

Best,
[Your Name]
