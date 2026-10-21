# FlytBase Inbound BDR Agent (Python)

A small, inspectable end-to-end workflow for the FlytBase BDR assignment. It takes the provided lead JSON, researches public pages, ranks FlytBase case studies from the live case-study index, discovers the Anglo American connection from the retrieved page text, and generates qualification, email sequence, partner-motion recommendation, and AE handoff outputs.

## Important
- This is a working prototype, not a production deployment.
- Research results depend on public-site availability at runtime. Every finding is emitted with its source URL and retrieval date.
- Do not present an unverified claim as fact. The system flags missing information and distinguishes lead-provided statements from public research.
- The assignment asks for system access, actual live-run output, and an 8–12 minute walkthrough. Run this script yourself and record the live run; do not submit only this README or a manually copied report.

## Setup (Windows PowerShell)
```powershell
cd flytbase_bdr_agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY="your_api_key_here"
python agent.py --input lead.json --output output
```

If PowerShell blocks activation, use:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:OPENAI_API_KEY="your_api_key_here"
.\.venv\Scripts\python.exe agent.py --input lead.json --output output
```

The workflow can still run without an OpenAI key using its transparent rule-based fallback; however, the generated prose will be less adaptive. For best results, set `OPENAI_API_KEY`.

## Architecture
1. Load one lead JSON (the only business input).
2. Search public web results for SQM annual report/news/org structure and FlytBase partner information.
3. Fetch FlytBase's public case-study index and score discovered case studies using lead context and the discovered referral entity.
4. Create a qualification record using MEDDIC; separate knowns from unknowns.
5. Generate a tailored email sequence and AE handoff using evidence gathered by the workflow.
6. Save structured JSON, readable Markdown, and a run log with source URLs.

## Evidence safeguards
- Public findings include source URL, title, snippet and retrieval timestamp.
- Search failures are recorded rather than silently replaced with invented facts.
- The case-study match is ranked from retrieved page titles/text, not a fixed case-study URL.
- Partner recommendation is conditional: direct AE ownership with LATAM drone/implementation partner involvement only if current partner evidence supports it.
