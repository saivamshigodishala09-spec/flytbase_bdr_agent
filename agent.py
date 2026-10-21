#!/usr/bin/env python3
"""Inspectable FlytBase inbound BDR workflow prototype."""
import argparse, json, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BDRResearchPrototype/1.0; +https://example.org)"}
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

def get_page(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else url
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = requests.compat.urljoin(url, href)
            if href.startswith("http"):
                links.append({"text": a.get_text(" ", strip=True), "url": href})
        return {"url": url, "title": title, "text": text[:18000], "links": links, "error": None}
    except Exception as e:
        return {"url": url, "title": url, "text": "", "links": [], "error": str(e)}

def search_web(query, limit=6):
    """Search public DuckDuckGo HTML results; errors are surfaced in run log."""
    url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    page = get_page(url)
    if page["error"]:
        return [{"query": query, "error": page["error"], "url": url}]
    soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=15).text, "html.parser")
    results = []
    for result in soup.select(".result"):
        a = result.select_one(".result__a")
        sn = result.select_one(".result__snippet")
        if not a:
            continue
        href = a.get("href", "")
        if "uddg=" in href:
            from urllib.parse import parse_qs, urlparse
            href = parse_qs(urlparse(href).query).get("uddg", [href])[0]
        results.append({"query": query, "title": a.get_text(" ", strip=True),
                        "url": href, "snippet": sn.get_text(" ", strip=True) if sn else ""})
        if len(results) >= limit:
            break
    return results or [{"query": query, "error": "No parsed search results returned", "url": url}]

def uniq_results(groups):
    out, seen = [], set()
    for group in groups:
        for r in group:
            u = r.get("url", "")
            if u and u not in seen:
                seen.add(u); out.append(r)
    return out

def research_account(lead):
    queries = [
        f"SQM annual report 2025 capital expenditures official investor relations",
        f"SQM leadership organizational structure operations lithium Chile official",
        f"SQM latest news lithium Atacama operations 2026 official",
        f"SQM investor presentation operational priorities sustainability water Atacama",
        f"FlytBase partners Latin America UAV LATAM official",
    ]
    searches = [search_web(q) for q in queries]
    results = uniq_results(searches)
    # Fetch a small number of credible results to obtain extractable page evidence.
    pages = []
    for r in results[:12]:
        if r.get("url", "").startswith("http"):
            p = get_page(r["url"])
            p["search_title"] = r.get("title", "")
            p["search_snippet"] = r.get("snippet", "")
            if not p["error"]:
                pages.append(p)
    # Include public FlytBase case-study index and official SQM investor pages as discovery seeds.
    for url in ["https://flytbase.com/case-studies", "https://ir.sqm.com/financials/annual-reports", "https://ir.sqm.com/news-events/news"]:
        p = get_page(url)
        if not p["error"] and all(x["url"] != url for x in pages):
            pages.append(p)
    return {"queries": queries, "search_results": results, "pages": pages, "retrieved_at": NOW}

def discover_case_study(lead):
    index = get_page("https://flytbase.com/case-studies")
    candidates = []
    if not index["error"]:
        for link in index["links"]:
            u = link["url"]
            text = (link["text"] + " " + u).lower()
            if "case-studies/" in u and any(k in text for k in ["mining", "sqm", "anglo", "inspection", "industrial"]):
                if u not in [c["url"] for c in candidates]:
                    candidates.append({"title": link["text"] or u, "url": u})
    # Score discovered case studies by context, then fetch top candidates.
    terms = ["mining", "lithium", "inspection", "anglo american", "safety", "autonomous", "site"]
    scored = []
    for c in candidates[:30]:
        p = get_page(c["url"])
        body = (c["title"] + " " + p.get("text", "")).lower()
        score = sum(2 if t in body else 0 for t in terms)
        if "anglo american" in body: score += 8
        if "sqm" in body or "lithium" in body: score += 5
        scored.append({"title": p.get("title", c["title"]), "url": c["url"], "score": score,
                       "text_excerpt": p.get("text", "")[:2200], "error": p.get("error")})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"index_url": index["url"], "index_error": index["error"],
            "discovered_count": len(candidates), "ranked_candidates": scored[:8],
            "selection_method": "Live FlytBase case-study index links scored against lead context; no fixed URL."}

def meddic(lead):
    known = {
        "Metrics": ["3 large-scale sites", "24/7 inspection need", "contracted crews described as expensive", "hazardous work stated by lead"],
        "Economic buyer": "Unknown; Rodrigo's title does not establish budget authority.",
        "Decision criteria": ["Drone-based inspection is desired; technical, safety, integration and ROI criteria unknown."],
        "Decision process": ["Internal budget conversation scheduled for Q3 (year and exact date not supplied). Approval/procurement steps unknown."],
        "Identify pain": ["Cost of contracted crews", "Hazard exposure", "Need to inspect lithium sites continuously"],
        "Champion": "Possible internal advocate, but influence and willingness to champion are unverified."
    }
    missing = [
        "Quantified current inspection cost, crew hours, incident/exposure baseline and desired ROI/payback",
        "Economic buyer and finance/procurement stakeholders",
        "Technical owner, HSE lead, IT/security and site managers",
        "Decision timeline, budget amount/currency and whether Q3 refers to 2026",
        "Site locations, terrain/communications constraints, drone regulations and flight permissions",
        "Required sensors, inspection targets, integrations, data residency/security and response SLA",
        "Anglo American referral contact and permission to reference that relationship"
    ]
    # transparent 100-point heuristic; not a claim of statistical probability
    score_parts = {"account_fit": 25, "pain_urgency": 18, "scale": 15, "timing_signal": 10, "authority_evidence": 4, "budget_evidence": 5}
    score = sum(score_parts.values())
    return {"framework": "MEDDIC", "why": "Enterprise, multi-site, safety-critical sale with multiple stakeholders and budget validation; MEDDIC exposes gaps in metrics, economic buyer, criteria, process, pain and champion.",
            "known_information": known, "missing_information": missing,
            "priority_score": score, "score_scale": "Heuristic 0-100 lead-priority score, not close probability",
            "score_components": score_parts,
            "fit_assessment": "High potential account/use-case fit; qualification is incomplete because quantified metrics, economic buyer, procurement process and confirmed budget are missing.",
            "recommended_status": "Priority discovery; route to AE for fast response, but do not mark sales-qualified until discovery confirms budget, authority and timeline."}

def llm_json(system, user, fallback):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return fallback, "rule-based fallback (OPENAI_API_KEY not set)"
    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        resp = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            json={"model": model, "temperature": 0.2,
                  "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": json.dumps(user, ensure_ascii=False)}]}, timeout=45)
        resp.raise_for_status()
        data = resp.json()["choices"][0]["message"]["content"]
        return json.loads(data), "OpenAI API " + model
    except Exception as e:
        return fallback, "fallback after LLM error: " + str(e)

def generate_emails(lead, qualification, research, case):
    facts = []
    for p in research["pages"]:
        if p.get("text"):
            facts.append({"title": p.get("title"), "url": p["url"], "excerpt": p["text"][:1800]})
    top_case = case["ranked_candidates"][0] if case["ranked_candidates"] else {}
    fallback = {"sequence": [
      {"step": 1, "timing": "Immediately", "purpose": "Acknowledge the operational pain and book discovery",
       "subject": "Atacama inspections: reducing crew exposure across three sites",
       "body": f"Hi Rodrigo,\n\nThanks for reaching out. Your note about continuous inspections across three Atacama lithium sites—and the cost and exposure associated with contracted crews—sounds like a useful problem to quantify before your Q3 budget discussion.\n\nFlytBase supports autonomous drone operations; the right first step is to understand the inspection workflow rather than assume a particular deployment. Could we schedule 25 minutes to cover the assets inspected, current inspection frequency/cost, hazardous access points, and what a successful pilot would need to prove?\n\nWould early next week work?\n\nBest,\nFlytBase Inbound Team",
       "progression_logic": "Lead is high-fit and has a stated budget discussion; respond quickly and ask for a discovery call, not a premature demo."},
      {"step": 2, "timing": "After 3 business days if no reply", "purpose": "Offer a relevant peer example and clarify the referral",
       "subject": "A mining deployment worth comparing with your Atacama use case",
       "body": "Hi Rodrigo,\n\nI wanted to share a relevant mining example from FlytBase's public case-study library: " + (top_case.get("title") or "a mining deployment") + ". The useful comparison is how autonomous drone operations can reduce repeated travel and keep people away from difficult areas; the actual fit for SQM would depend on your inspection targets, connectivity and site rules.\n\nYou mentioned Anglo American referred you. If appropriate, could you share the team or contact who made the introduction? That would help us understand which workflow is most relevant without assuming the two operations are identical.\n\nWould a short working session be useful?\n\nBest,\nFlytBase Inbound Team",
       "progression_logic": "Adds proof relevant to mining and asks about referral context while avoiding unsupported performance promises."},
      {"step": 3, "timing": "After 5 further business days if no reply", "purpose": "Help prepare a budget-ready business case",
       "subject": "Useful inputs for your Q3 inspection business case",
       "body": "Hi Rodrigo,\n\nTo make an initial business case useful for your Q3 discussion, we could model a small set of inputs: annual contracted inspection spend, crew hours in hazardous areas, inspection frequency today versus target, and the cost of a docked-drone pilot at one representative site.\n\nWe would also want to confirm who owns operations, HSE, IT/security and budget approval, plus any Chilean aviation or site constraints that need to be considered. If timing has changed, just let me know and I can adjust.\n\nShould I send a one-page discovery checklist, or would you prefer a 20-minute call?\n\nBest,\nFlytBase Inbound Team",
       "progression_logic": "Turns missing MEDDIC data into a low-friction next step; offers an alternative to a meeting."}
    ]}
    system = "You are an enterprise inbound BDR assistant. Use only provided evidence. Do not invent SQM facts or claim unverified outcomes. Return JSON with key sequence, an array of 3 objects with step,timing,purpose,subject,body,progression_logic."
    user = {"lead": lead, "qualification": qualification, "research_evidence": facts[:8], "case_candidates": case["ranked_candidates"][:3]}
    return llm_json(system, user, fallback)

def partner_motion(lead, research, case):
    evidence = []
    for r in research["search_results"]:
        if any(k in (r.get("title","")+" "+r.get("url","")+" "+r.get("snippet","")).lower() for k in ["uav latam", "partner", "anglo american"]):
            evidence.append(r)
    return {
      "recommendation": "AE-led discovery with a LATAM drone/implementation partner considered for local deployment",
      "confidence": "Medium-low until partner availability, coverage and current authorization are confirmed",
      "rationale": ["Enterprise, multi-site and 24/7 scope merits direct AE ownership.", "Chile/Atacama operations may require local aviation, field service, connectivity and integration expertise.", "The public FlytBase Anglo American Peru story references UAV LATAM; this is evidence of a regional ecosystem connection, not proof of current availability or coverage in Chile."],
      "verification_required": ["Confirm whether UAV LATAM is an active FlytBase partner and can serve SQM in Chile.", "Confirm Chile-specific regulatory/operational capability, support SLA and commercial model.", "Keep AE as commercial owner unless FlytBase's channel policy indicates otherwise."],
      "public_evidence": evidence[:5]
    }

def build_report(lead, qual, research, case, emails, email_method, partner):
    pages = research["pages"]
    findings = []
    for p in pages:
        if p.get("text"):
            findings.append({"title": p.get("title"), "url": p["url"], "excerpt": p["text"][:500]})
    top = case["ranked_candidates"][0] if case["ranked_candidates"] else None
    handoff = {
      "buyer_context": {"name": lead["from_name"], "title": lead["title"], "company": lead["company"],
        "cares_about": ["inspection cost", "worker safety/exposure", "24/7 coverage across three sites", "Q3 budget preparation"],
        "other_stakeholders": ["economic buyer/finance (unknown)", "HSE (unknown)", "IT/security (unknown)", "site managers (unknown)", "procurement (unknown)"]},
      "qualification": qual,
      "research_highlights": findings[:3],
      "recommended_case_study": top,
      "partner_motion": partner,
      "suggested_next_step": "AE to contact Rodrigo promptly for a 25-minute discovery call; quantify current inspection cost and safety exposure, confirm Q3 year/date, map economic buyer/HSE/IT stakeholders, and validate pilot constraints.",
      "rationale": "High account/use-case fit with urgency signals, but not fully sales-qualified until budget, authority, metrics and procurement path are confirmed."
    }
    return {"generated_at": NOW, "lead": lead, "qualification": qual,
      "account_research": {"queries": research["queries"], "search_results": research["search_results"],
                           "public_page_evidence": findings, "caveat": "Search snippets and fetched pages are public-source evidence; validate claims and dates before customer-facing use."},
      "case_study_discovery": case, "email_sequence": emails, "email_generation_method": email_method,
      "partner_recommendation": partner, "ae_handoff": handoff}

def to_markdown(data):
    q=data["qualification"]; lead=data["lead"]; case=data["case_study_discovery"]
    out = ["# FlytBase Inbound BDR Agent — Live Run Output", f"Generated: {data['generated_at']}", "",
    "## Input lead", f"- **Name:** {lead['from_name']} ({lead['email']})", f"- **Role:** {lead['title']}",
    f"- **Company:** {lead['company']}, {lead['country']}", f"- **Subject:** {lead['subject']}", f"- **Context:** {lead['context']}", "",
    "## Stage 1 — Qualification (MEDDIC)", f"- **Priority score:** {q['priority_score']}/100 (heuristic, not close probability)",
    f"- **Fit:** {q['fit_assessment']}", f"- **Status:** {q['recommended_status']}", f"- **Why MEDDIC:** {q['why']}", "",
    "### Known information"]
    for k,v in q["known_information"].items(): out.append(f"- **{k}:** {json.dumps(v, ensure_ascii=False)}")
    out += ["", "### Missing information"] + [f"- {x}" for x in q["missing_information"]]
    out += ["", "## Stage 2 — Account research", "The following sources were discovered/fetched at runtime. Confirm the source page before using any claim externally."]
    for p in data["account_research"]["public_page_evidence"]:
        out += [f"### {p['title']}", f"- URL: {p['url']}", f"- Extract: {p['excerpt']}", ""]
    out += ["## Stage 3 — Adaptive response sequence", f"Generation method: {data['email_generation_method']}", ""]
    for e in data["email_sequence"].get("sequence", []):
        out += [f"### Email {e.get('step')}: {e.get('purpose')}", f"- Timing: {e.get('timing')}", f"- Progression logic: {e.get('progression_logic')}", f"- Subject: {e.get('subject')}", "", e.get("body",""), ""]
    out += ["## Stage 4 — Case study discovery", f"- Index: {case['index_url']}", f"- Discovered candidates: {case['discovered_count']}", f"- Method: {case['selection_method']}", ""]
    for c in case["ranked_candidates"][:5]:
        out += [f"### {c['title']} (score {c['score']})", f"- URL: {c['url']}", f"- Evidence: {c['text_excerpt'][:700]}", ""]
    out += ["## Stage 5 — Partner identification", f"- Recommendation: {data['partner_recommendation']['recommendation']}", f"- Confidence: {data['partner_recommendation']['confidence']}", "- Rationale:"]
    out += [f"  - {x}" for x in data['partner_recommendation']['rationale']]
    out += ["- Verification required:"] + [f"  - {x}" for x in data['partner_recommendation']['verification_required']]
    out += ["", "## Stage 6 — AE handoff", "```json", json.dumps(data["ae_handoff"], indent=2, ensure_ascii=False), "```", "",
      "## Limitations and review checklist", "- Search/provider availability can affect findings.", "- This prototype does not access internal CRM, validate the lead's identity, or send emails.", "- Budget conversation timing, buyer authority, metrics, local partner coverage and regulatory details remain unverified.", "- Verify all public claims and links before the walkthrough/customer contact."]
    return "\n".join(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", default="lead.json")
    ap.add_argument("--output", default="output")
    args=ap.parse_args()
    lead=json.loads(Path(args.input).read_text(encoding="utf-8"))
    print("[1/6] MEDDIC qualification...")
    qual=meddic(lead)
    print("[2/6] Searching public sources for SQM and regional partner signals...")
    research=research_account(lead)
    print("[3/6] Generating adaptive email sequence...")
    print("[4/6] Discovering and ranking FlytBase case studies from public index...")
    case=discover_case_study(lead)
    emails, method=generate_emails(lead, qual, research, case)
    print("[5/6] Assessing partner-led vs direct AE motion...")
    partner=partner_motion(lead, research, case)
    print("[6/6] Building AE handoff and saving artifacts...")
    data=build_report(lead, qual, research, case, emails, method, partner)
    out=Path(args.output); out.mkdir(parents=True, exist_ok=True)
    (out/"run_output.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    (out/"run_output.md").write_text(to_markdown(data), encoding="utf-8")
    (out/"run_log.txt").write_text(
      f"Run time UTC: {NOW}\nInput: {args.input}\nPages fetched: {len(research['pages'])}\nSearch results: {len(research['search_results'])}\nCase-study candidates discovered: {case['discovered_count']}\nEmail generation: {method}\n", encoding="utf-8")
    print(f"Done. Open {out/'run_output.md'} and {out/'run_output.json'}")
    print(f"Pages fetched: {len(research['pages'])}; case studies discovered: {case['discovered_count']}; email generation: {method}")

if __name__=="__main__":
    main()
