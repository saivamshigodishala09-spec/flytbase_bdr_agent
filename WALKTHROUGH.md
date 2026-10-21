# 8–12 minute walkthrough plan

Do a real run on screen. Do not claim a successful run until the script completes.

1. (0:00–1:00) Explain input: one lead JSON copied from the assignment. No manually authored research is injected.
2. (1:00–2:30) Show architecture in `agent.py`: research/search functions, MEDDIC scoring, dynamic case-study discovery, email generation, handoff.
3. (2:30–5:30) Run `python agent.py --input lead.json --output output`; show terminal stages and open `output/run_output.md`.
4. (5:30–7:00) Show source URLs and why the chosen case study ranked highest. Explain that it is discovered from FlytBase's live case-study index, not hard-coded.
5. (7:00–8:30) Explain MEDDIC gaps: metrics, economic buyer, decision criteria/process, pain, champion.
6. (8:30–9:30) Explain partner recommendation as conditional, not a claim that a partner is confirmed available in Chile.
7. (9:30–10:30) Design decision: keep evidence URLs and missing-data flags visible to avoid hallucinated claims. Limitation: public web extraction can fail or miss JavaScript-rendered content; improve with official APIs, retries, source scoring, and human approval.
8. (10:30–11:00) Show run log and artifacts. Be candid about what ran and what did not.

## Before recording
- Install requirements and run once.
- Check every URL in output; remove/flag unsupported claims.
- If search results are empty, do not fake them. Explain the failure and rerun/check network.
- If no API key is available, the system still produces a rule-based email fallback; disclose that.
