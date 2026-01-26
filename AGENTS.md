# Project: Strategy Science Conference Review System

## 1. Project Overview
This project manages the paper review process for the Strategy Science Conference. It consists of Python scripts to:
1.  **Extract Data**: Read PDFs from Dropbox, extract title/abstract/keywords using local LLMs (Ollama/Qwen).
2.  **Assign Reviewers**: Match papers to reviewers based on keyword similarity and method (Qual/Quant) using Firebase for reviewer data.

## 2. Environment & Dependencies
**Runtime**: Python 3.9+
**Key Libraries**:
- `requests` (API calls to Ollama & Firebase)
- `dropbox` (File management)
- `pdfplumber` (PDF text extraction)

**Installation**:
No `requirements.txt` present. Install dependencies manually:
```bash
pip install requests dropbox pdfplumber
```

**External Services**:
- **Ollama**: Must be running locally on port 11434 (`ollama serve`). Model: `qwen2.5:7b` (configurable).
- **Firebase**: Realtime Database for reviewer expertise and assignments.
- **Dropbox**: Source of PDF files.

## 3. Build & Run Commands
There is no build step. Scripts are executed directly.

**Paper Processing (PDF -> CSV)**:
```bash
python3 process_papers.py
```
*   Scans Dropbox folder.
*   Extracts metadata via LLM.
*   Outputs to `papers_import.csv`.

**Reviewer Assignment (CSV + Firebase -> CSV)**:
```bash
python3 assign_reviewers_v2.py
```
*   Reads `papers_import.csv`.
*   Fetches reviewers from Firebase.
*   Outputs `assignments.csv`.

**Testing**:
Tests are ad-hoc scripts named `test_*.py`.
```bash
python3 test_extraction.py
python3 test_pdf.py
```
*   **Note**: Avoid hardcoding absolute paths in tests (e.g., `/Users/...`). Use relative paths or environment variables.

## 4. Code Style & Standards

### Formatting & Syntax
- **Type Hints**: MANDATORY for all function signatures. Use `typing` (`List`, `Dict`, `Optional`, `Set`) and `dataclasses`.
- **Docstrings**: Required for all modules and functions. Use triple double-quotes.
- **Imports**: Group standard lib, third-party, and local imports.
- **Naming**:
    - Variables/Functions: `snake_case`
    - Classes: `PascalCase`
    - Constants: `UPPER_CASE`

### Error Handling & Logging
- **Console Output**: Use "Rich" style text output with separators and emojis for readability.
    - `print("=" * 60)` for section headers.
    - Use emojis: `✓` (success), `✗` (failure), `⚠` (warning), `📡` (network), `⏳` (processing).
- **Exceptions**: Catch specific exceptions (e.g., `dropbox.exceptions.ApiError`) rather than bare `except:`.
- **Fallbacks**: Always provide fallbacks for external dependencies (e.g., PDF extraction failure, LLM unavailability).

### Architecture Patterns
- **Data Classes**: Use `@dataclass` for structured data (Reviewer, Paper) instead of raw dictionaries.
- **Configuration**: Keep config variables (`DROPBOX_TOKEN`, `OLLAMA_URL`) at the top of the file.
- **Modularity**: Separation of concerns—`process_papers` for extraction, `assign_reviewers` for logic.

## 5. Development Workflow
1.  **Analyze**: Understand the data flow (PDF -> Text -> LLM -> CSV).
2.  **Local Dev**: Ensure Ollama is running before testing extraction logic.
3.  **Verification**: Run `test_extraction.py` to verify PDF parsing before full batch processing.
4.  **No Commits**: Do not commit changes unless explicitly requested.

## 6. Known Issues / Context
- `test_extraction.py` currently contains hardcoded paths. When refactoring, switch to relative paths.
- LLM extraction can be slow; `process_papers.py` includes progress estimation.
- Firebase integration is read-heavy; be careful with write permissions/rules.
