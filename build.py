"""Static site generator for the TPM Bootcamp Flow Atlas.

This script is the single source of truth for course content. It renders
Jinja2 templates in templates/ into plain static HTML files (index.html,
week1.html .. week4.html) at the project root. Those output files are what
gets opened in a browser or deployed to GitHub Pages -- do not hand-edit
them directly, edit this file or the templates instead, then re-run:

    python build.py
"""
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
TEMPLATES_DIR = ROOT / "templates"

# ---------------------------------------------------------------------------
# GLOSSARY: every piece of jargon used across the site, in plain English, so
# a reader who never attended the Boot Camp can still follow along. Split into
# two audiences: "core" (product/TPM process vocabulary) and "technical"
# (architecture/engineering vocabulary). `match` lists the literal text
# variant(s) that glossarize() looks for in day/milestone copy -- the longest
# variant wins first so e.g. "Context Diagram" is claimed before bare
# "Context".
# ---------------------------------------------------------------------------
GLOSSARY = [
    # --- Core TPM Glossary ---------------------------------------------------
    {"id": "rccf", "term": "RCCF", "category": "core",
     "definition": "A checklist for asking an AI a genuinely useful question: Role (who should it "
                   "act as), Context (the situation), Constraints (what the answer must respect), "
                   "Format (how the answer should look)."},
    {"id": "working-backwards", "term": "Working Backwards", "category": "core",
     "definition": "A planning method where you write the finished product's press release and FAQ "
                   "before you build anything, so you're forced to prove real customer value first."},
    {"id": "pr-faq", "term": "PR/FAQ", "category": "core",
     "definition": "A one-page press release plus a list of Frequently Asked Questions for a product "
                   "that doesn't exist yet -- the actual document the Working Backwards method produces."},
    {"id": "persona", "term": "Persona", "category": "core",
     "definition": "A description of a real type of user, built from actual behavior and evidence "
                   "(not a guess), used to keep decisions grounded in a real person's needs."},
    {"id": "jtbd", "term": "JTBD (Jobs To Be Done)", "category": "core", "match": ["JTBD"],
     "definition": "A way of describing what a customer is really trying to accomplish (e.g. "
                   "\u2018reassign a job in under 30 seconds\u2019), instead of a demographic label."},
    {"id": "pain-point", "term": "Pain Point", "category": "core", "match": ["Pain Point", "Pain-Point"],
     "definition": "A specific moment where a real user gets stuck, frustrated, or blocked while doing "
                   "their job -- written as a verb + circumstance + consequence, not a vague complaint."},
    {"id": "five-whys", "term": "5 Whys", "category": "core",
     "definition": "A technique of asking \u2018why\u2019 five times in a row on a problem to dig past the "
                   "surface symptom and find its true root cause."},
    {"id": "problem-statement", "term": "Problem Statement", "category": "core",
     "definition": "A short, evidence-backed paragraph naming who has the problem, what it is, and how "
                   "we know it's real -- the starting line for any new feature."},
    {"id": "evidence-brief", "term": "Evidence Brief", "category": "core",
     "definition": "A short document that backs up a problem statement with real data points (numbers, "
                   "quotes, examples) instead of opinions."},
    {"id": "north-star-metric", "term": "North Star Metric", "category": "core",
     "match": ["North Star Metric", "North Star"],
     "definition": "The single number a whole team rallies around, chosen because moving it up means "
                   "customers are truly better off -- not just a number that looks good in a report."},
    {"id": "kpi", "term": "KPI (Key Performance Indicator)", "category": "core", "match": ["KPI"],
     "definition": "A specific, trackable number used to check whether a team is on track toward a "
                   "bigger goal."},
    {"id": "metrics-pyramid", "term": "Metrics Pyramid", "category": "core",
     "definition": "A way of organizing measurements into three layers: the North Star at the top, "
                   "KPIs in the middle, and small day-to-day operational signals at the bottom."},
    {"id": "vanity-metric", "term": "Vanity Metric", "category": "core",
     "definition": "A number that goes up and looks impressive but doesn't actually prove customers "
                   "are better off (e.g. total signups, when most people never come back)."},
    {"id": "counter-metric", "term": "Counter-Metric", "category": "core", "match": ["Counter-Metric", "Counter Metric"],
     "definition": "A second number tracked alongside the North Star specifically to catch it being "
                   "\u2018gamed\u2019 -- e.g. if speed goes up but accuracy secretly drops, this catches it."},
    {"id": "heuristic", "term": "Heuristic", "category": "core", "match": ["Heuristics", "Heuristic"],
     "definition": "One of 10 well-known rules of thumb for judging whether software is easy or hard "
                   "to use (e.g. \u2018the system should always keep users informed\u2019)."},
    {"id": "accessibility", "term": "Accessibility (a11y)", "category": "core", "match": ["Accessibility"],
     "definition": "Designing a product so people with different abilities (vision, hearing, motor, "
                   "cognitive) can still use it fully -- not an optional extra feature."},
    {"id": "design-principle", "term": "Design Principle", "category": "core",
     "match": ["Design Principles", "Design Principle"],
     "definition": "A short, memorable rule a team commits to that guides every future design decision "
                   "(e.g. \u2018build guardrails, not cleanup workflows\u2019)."},
    {"id": "journey-map", "term": "Customer Journey Map", "category": "core",
     "match": ["Customer Journey Map", "Journey Map", "Customer Journeys", "Customer Journey"],
     "definition": "A visual timeline of every stage a customer goes through while using a product, "
                   "showing where they feel confident, confused, or frustrated at each step."},
    {"id": "friction-point", "term": "Friction Point", "category": "core",
     "match": ["Friction Point", "Friction Hotspot", "Frictions"],
     "definition": "A specific spot in a customer journey where something slows the customer down or "
                   "causes them to hesitate, doubt, or give up."},
    {"id": "prd", "term": "PRD (Product Requirements Document)", "category": "core", "match": ["PRD"],
     "definition": "The official written plan for a feature: what problem it solves, what it must do, "
                   "how you'll know it works, and what could go wrong -- the handoff to engineering."},
    {"id": "acceptance-criteria", "term": "Acceptance Criteria (AC)", "category": "core",
     "match": ["Acceptance Criteria"],
     "definition": "A specific, testable checklist condition that must be true for a feature to be "
                   "\u2018done\u2019 -- clear enough that anyone could check pass/fail without guessing."},
    {"id": "nfr", "term": "NFR (Non-Functional Requirement)", "category": "core", "match": ["NFRs", "NFR"],
     "definition": "A requirement about how well something must work (how fast, how secure, how "
                   "reliable) rather than what it does -- e.g. a page must load in under 2 seconds."},
    {"id": "dependency", "term": "Dependency", "category": "core", "match": ["Dependencies", "Dependency"],
     "definition": "Something a feature needs from another team, system, or decision before it can "
                   "ship -- each one should have a named owner and a due date."},
    {"id": "risk", "term": "Risk (in a PRD)", "category": "core", "match": ["Risks and Open Questions", "Risks & Open Questions"],
     "definition": "A specific thing that could go wrong with a feature, written down on purpose along "
                   "with a plan for what to do if it happens."},
    {"id": "solution-sketch", "term": "Solution Sketch", "category": "core",
     "definition": "A short, plain-language walkthrough of how a feature will work step-by-step from "
                   "the user's point of view -- the visible flow, not low-level code."},
    {"id": "context-prd", "term": "Context (PRD section)", "category": "core", "match": ["Context"],
     "definition": "The background section of a document that explains the business situation and the "
                   "problem being solved, so a reader with no prior history can understand why it matters."},
    {"id": "goals-non-goals", "term": "Goals & Non-Goals", "category": "core",
     "match": ["Goals & Non-Goals", "Goals and Non-Goals", "Non-Goals"],
     "definition": "An explicit list of what a feature IS trying to do (goals) and, just as "
                   "importantly, what it deliberately is NOT trying to do -- this stops scope from "
                   "silently growing."},
    {"id": "scope", "term": "Scope", "category": "core",
     "definition": "The exact boundary of what is and isn't included in a piece of work."},
    {"id": "stakeholder", "term": "Stakeholder", "category": "core", "match": ["Stakeholders", "Stakeholder"],
     "definition": "Any person or team who has a real interest in a decision and whose input or "
                   "sign-off is needed before moving forward."},
    {"id": "sign-off", "term": "Sign-Off", "category": "core", "match": ["Sign-Off", "Sign-off"],
     "definition": "A stakeholder's explicit, named approval on a specific decision or document -- not "
                   "just a passive 'no objection.'"},
    {"id": "capstone", "term": "Capstone", "category": "core",
     "definition": "The final, cumulative project at the end of the Boot Camp where every skill "
                   "learned across all 8 weeks gets applied together on one real feature."},
    # --- Technical Glossary ---------------------------------------------------
    {"id": "monolith", "term": "Monolith", "category": "technical",
     "definition": "One single, large application where all the features live together in one shared "
                   "codebase and get deployed together as one unit."},
    {"id": "microservices", "term": "Microservices", "category": "technical", "match": ["Microservices", "Microservice"],
     "definition": "An architecture style where a product is split into many small, independent "
                   "services (e.g. a separate Billing Service and Notification Service) that can each "
                   "be built and deployed on their own."},
    {"id": "integration-map", "term": "Integration Map", "category": "technical",
     "definition": "A diagram showing every system a feature talks to and the exact \u2018contract\u2019 "
                   "(data format and rules) each connection uses."},
    {"id": "stride", "term": "STRIDE", "category": "technical",
     "definition": "A checklist of 6 threat categories used to find security weaknesses: Spoofing, "
                   "Tampering, Repudiation, Information disclosure, Denial of service, Elevation of "
                   "privilege."},
    {"id": "threat-model", "term": "Threat Model", "category": "technical",
     "definition": "A structured exercise of walking through a system on purpose to find where an "
                   "attacker could cause harm, before it's built."},
    {"id": "compliance", "term": "Compliance", "category": "technical", "match": ["Compliance"],
     "definition": "A set of external rules or standards (like SOC 2, or a privacy law) a product must "
                   "follow, often requiring proof like an audit trail."},
    {"id": "c4-diagram", "term": "C4 Diagram", "category": "technical", "match": ["C4-style diagrams", "C4"],
     "definition": "A standard way of drawing software architecture at 4 zoom levels: Context, "
                   "Container, Component, and Code -- TPMs typically only draw the first two."},
    {"id": "context-diagram", "term": "Context Diagram (C4 Level 1)", "category": "technical",
     "match": ["Context diagram", "Context Diagram", "Context + Container"],
     "definition": "The most zoomed-out architecture diagram: the system as one box, the people who "
                   "use it, and the other systems it talks to."},
    {"id": "container-diagram", "term": "Container Diagram (C4 Level 2)", "category": "technical",
     "match": ["Container diagram", "Container Diagram", "Containers"],
     "definition": "A more zoomed-in architecture diagram showing every independently deployable piece "
                   "inside the system (web app, API, database, queue) and how they talk to each other."},
    {"id": "trust-boundary", "term": "Trust Boundary", "category": "technical",
     "definition": "A line on a diagram marking where data moves from something your team fully "
                   "controls into something owned by someone else -- the exact spot security reviews "
                   "focus on."},
    {"id": "slo", "term": "SLO (Service Level Objective)", "category": "technical", "match": ["SLOs", "SLO"],
     "definition": "A specific, measurable target for how well a system should perform, e.g. \u201895% "
                   "of requests finish in under 2 seconds.\u2019"},
    {"id": "latency", "term": "Latency", "category": "technical",
     "definition": "How long it takes a system to respond after a request is made -- usually measured "
                   "in milliseconds or seconds."},
    {"id": "availability", "term": "Availability", "category": "technical",
     "definition": "The percentage of time a system is actually up and working, out of all the time "
                   "it's supposed to be working (e.g. 99.5% availability)."},
    {"id": "availability-zone", "term": "Availability Zone (AZ)", "category": "technical",
     "match": ["Availability Zone", "multi-AZ"],
     "definition": "An isolated data center within a cloud region; spreading a system across multiple "
                   "AZs protects against one data center failing."},
    {"id": "error-budget", "term": "Error Budget", "category": "technical",
     "definition": "The small amount of allowed failure built into an availability target (e.g. 99.5% "
                   "availability leaves about 3.6 hours/month) -- a practical tool for deciding when to "
                   "ship features versus focus on reliability."},
    {"id": "rate-limit", "term": "Rate Limit", "category": "technical",
     "match": ["Rate-Limit", "Rate Limit", "rate-limiting"],
     "definition": "A rule that caps how many requests a single user or system can make in a given "
                   "time period, to protect the system from being overwhelmed."},
    {"id": "idempotency", "term": "Idempotency", "category": "technical", "match": ["Idempotency", "Idempotent"],
     "definition": "A safety property where doing the exact same request twice (e.g. a network retry) "
                   "produces the same result as doing it once, instead of duplicating the action."},
    {"id": "trade-off", "term": "Trade-Off", "category": "technical", "match": ["Trade-Offs", "Trade-Off"],
     "definition": "An explicit choice between two good options where picking one means accepting a "
                   "specific downside on purpose, instead of pretending there's a perfect option."},
    {"id": "tcd", "term": "TCD (Technical Considerations Document)", "category": "technical", "match": ["TCD"],
     "definition": "The technical follow-up document to the PRD covering architecture, security, "
                   "diagrams, performance targets, and trade-offs -- the final handoff to engineering."},
    {"id": "tmd", "term": "TMD (Technical Modeling Document)", "category": "technical", "match": ["TMD"],
     "definition": "The document that turns an approved architecture into a literal buildable system: "
                   "the database design, the cloud infrastructure layout, and the API contract."},
    {"id": "entity-model", "term": "Entity Model", "category": "technical",
     "definition": "A design of the data itself: what \u2018things\u2019 (entities) the system stores, what "
                   "fields each one has, and how they relate to each other."},
    {"id": "access-pattern", "term": "Access Pattern", "category": "technical",
     "definition": "A specific, named way the application will read or write data (e.g. \u2018list all "
                   "open tickets for a shop, sorted by priority\u2019) -- named before tables are designed."},
    {"id": "normalization", "term": "Normalization", "category": "technical",
     "definition": "A database design principle of avoiding storing the same piece of data in more "
                   "than one place, to prevent it from going out of sync."},
    {"id": "database-index", "term": "Index (database)", "category": "technical", "match": ["indexes", "index"],
     "definition": "A special lookup structure added to a database table that makes a specific kind of "
                   "search much faster, at the cost of extra storage and slightly slower writes."},
    {"id": "primary-key", "term": "Primary Key", "category": "technical",
     "definition": "A field (or set of fields) that uniquely identifies one row in a database table."},
    {"id": "foreign-key", "term": "Foreign Key", "category": "technical",
     "definition": "A field in one table that points to the Primary Key of another table, creating a "
                   "relationship between the two."},
    {"id": "managed-service", "term": "Managed Service", "category": "technical",
     "match": ["Managed Service", "Managed vs Self", "managed-vs-self-managed"],
     "definition": "A cloud component (like a database) the cloud provider operates and maintains for "
                   "you, versus \u2018self-managed\u2019 where your own team patches, scales, and fixes it."},
    {"id": "multi-tenancy", "term": "Multi-Tenancy", "category": "technical",
     "match": ["Multi-Tenancy", "multi-tenancy", "Tenancy"],
     "definition": "An architecture where multiple customers (\u2018tenants\u2019) share the same underlying "
                   "application and infrastructure, with their data kept logically separated."},
    {"id": "network-boundary", "term": "Network Boundary", "category": "technical",
     "definition": "The decision of where a system is reachable from -- e.g. open to the public "
                   "internet versus restricted to a private internal network."},
    {"id": "rest-api", "term": "REST API", "category": "technical", "match": ["REST API", "REST"],
     "definition": "A common web API style where each \u2018thing\u2019 in the system (like a Customer or "
                   "an Order) is a resource with its own URL, acted on with standard HTTP methods."},
    {"id": "soap-api", "term": "SOAP API", "category": "technical", "match": ["SOAP"],
     "definition": "An older, more rigid web API style using strict XML messages and formal contracts "
                   "-- still the right default in some regulated or legacy enterprise environments."},
    {"id": "api-resource", "term": "Resource (API)", "category": "technical", "match": ["REST resources", "resource candidate"],
     "definition": "A \u2018thing\u2019 exposed by an API that clients can read or change, always "
                   "represented by a noun (e.g. /tickets), never a verb."},
    {"id": "endpoint", "term": "Endpoint", "category": "technical",
     "definition": "One specific, callable URL + method combination in an API, e.g. \u2018POST "
                   "/v1/assignments.\u2019"},
    {"id": "http-method", "term": "HTTP Method", "category": "technical",
     "definition": "The verb part of an API call that says what action to take on a resource: GET "
                   "(read), POST (create), PATCH (partially update), DELETE (remove)."},
    {"id": "status-code", "term": "Status Code", "category": "technical",
     "definition": "A standardized 3-digit number an API returns to say what happened, e.g. 200 "
                   "(success), 404 (not found), 429 (too many requests)."},
    {"id": "api-versioning", "term": "API Versioning", "category": "technical", "match": ["versioning"],
     "definition": "A strategy (like putting /v1/ in the URL) for changing an API over time without "
                   "breaking the clients already using the old version."},
    {"id": "rom-cost", "term": "ROM Cost (Rough Order of Magnitude)", "category": "technical",
     "match": ["ROM cost", "rough-order-of-magnitude"],
     "definition": "An early, deliberately approximate cost estimate (e.g. within 25-50% accuracy) "
                   "used to sanity-check a decision before an exact number is possible."},
]

_TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")


def _build_glossary_pattern():
    variants = []
    for entry in GLOSSARY:
        for match_text in entry.get("match", [entry["term"]]):
            variants.append((match_text, entry["id"]))
    variants.sort(key=lambda pair: len(pair[0]), reverse=True)
    lookup = {text.lower(): entry_id for text, entry_id in variants}
    alternation = "|".join(re.escape(text) for text, _ in variants)
    pattern = re.compile(r"\b(" + alternation + r")('s|s)?\b", re.IGNORECASE)
    return pattern, lookup


_GLOSSARY_PATTERN, _GLOSSARY_LOOKUP = _build_glossary_pattern()
_glossary_by_id = {entry["id"]: entry for entry in GLOSSARY}


def _glossarize_plain(text):
    def _replace(match):
        matched_text = match.group(1)
        suffix = match.group(2) or ""
        entry_id = _GLOSSARY_LOOKUP.get(matched_text.lower())
        if not entry_id:
            return match.group(0)
        return (
            f'<span class="gloss-term" tabindex="0" role="button" aria-haspopup="dialog" '
            f'aria-expanded="false" data-gloss-id="{entry_id}">{matched_text}{suffix}</span>'
        )

    return _GLOSSARY_PATTERN.sub(_replace, text)


def glossarize(html_or_text):
    """Wrap every known glossary term in clickable markup, skipping HTML tag markup itself."""
    parts = _TAG_SPLIT_RE.split(html_or_text)
    for i, part in enumerate(parts):
        if not part.startswith("<"):
            parts[i] = _glossarize_plain(part)
    return "".join(parts)


# ---------------------------------------------------------------------------
# COURSE_LIFECYCLE: the 16-day single source of truth.
# Each entry is grounded in the real scanned course files (see
# data/course_source_digest.json) -- what/why/connects text should always be
# traceable back to that source material, never generic filler.
# ---------------------------------------------------------------------------
COURSE_LIFECYCLE = [
    {
        "week_id": "week1", "day": "Day 1", "anchor": "d1",
        "title": "AI Fundamentals & Prompting",
        "what": "Learn the RCCF prompting pattern (Role, Context, Constraints, Format) and the "
                "\u2018Three Hats\u2019 framing to ask AI more precise questions, then run reliability "
                "checks against the answers.",
        "why": "TPMs increasingly draft artifacts with AI assistance, so the course starts here "
               "because sloppy prompts produce predictable failure modes: vague scope, hallucinated "
               "facts, inconsistent format, unchecked bias. Getting prompting right on Day 1 protects "
               "the accuracy of every later artifact -- personas, problem statements, PRDs -- that "
               "will be drafted with AI help.",
        "connects": "The prompting discipline learned here is reused immediately in Day 2's PR/FAQ "
                    "drafting, and again in Week 2 Day 4's competitive research, where a 'bright "
                    "line' rule (facts from real sources only, no hallucination) depends on the same "
                    "reliability checks.",
        "artifacts": ["Prompt Pattern Library", "RCCF templates"],
    },
    {
        "week_id": "week1", "day": "Day 2", "anchor": "d2",
        "title": "Working Backwards",
        "what": "Draft a PR/FAQ (Press Release / FAQ) narrative and the Five Customer Questions "
                "before any solution is designed, then run a peer critique protocol on the draft.",
        "why": "Working Backwards forces the team to define customer value and success criteria in "
               "plain language before committing engineering time. It sits right after prompting "
               "because it is the first checkpoint against building features nobody asked for -- "
               "writing the 'press release' first exposes weak value propositions immediately.",
        "connects": "The customer value claims made in the PR/FAQ become the raw hypotheses that "
                    "Day 3's persona work and Day 4's pain-point work must validate with real "
                    "behavioral evidence.",
        "artifacts": ["PR/FAQ draft", "Five Customer Questions", "Peer Critique Protocol notes"],
        "diagram": (
            '<figure class="mini-diagram"><div class="flow-strip">'
            '<span class="fs-box">Heading</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Sub-heading</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Summary</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Problem</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Solution</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box fs-accent">Customer Quote</span>'
            '</div><figcaption>The 6-part PR/FAQ structure &mdash; written before any design or '
            'engineering work starts.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week1", "day": "Day 3", "anchor": "d3",
        "title": "Personas & JTBD",
        "what": "Build personas from behavioral evidence (what people actually do) instead of "
                "demographics, validate them with a Validation Canvas, and frame the underlying "
                "Job to Be Done.",
        "why": "A persona built on job titles or age ranges doesn't predict behavior; a persona "
               "built on 'what job is this person trying to get done, in what circumstance' does. "
               "This keeps every later prioritization decision traceable to a real, validated user "
               "-- not an assumed one.",
        "connects": "The validated persona and JTBD statement become the 'who' and 'why' that "
                    "Day 4's pain-point framing digs into, and later the 'who' cited in every PRD "
                    "problem statement in Week 3.",
        "artifacts": ["Persona Validation Canvas", "JTBD statements"],
    },
    {
        "week_id": "week1", "day": "Day 4", "anchor": "d4",
        "title": "Pain-Point Framing",
        "what": "Extract pain points from observed behavior (not just stated complaints), use "
                "5 Whys to reach root-cause pain, group raw pains into themes via affinity mapping, "
                "and score each pain on Severity \u00d7 Frequency \u00d7 Addressability.",
        "why": "The course's own Day 4 objectives are explicit: separate root-cause pain from "
               "symptoms, and distinguish pains you must fix from pains you must live with. Without "
               "this scoring step, teams chase the loudest complaint instead of the pain that "
               "actually threatens the business -- this is the mechanical filter that decides what's "
               "worth solving.",
        "connects": "The highest Severity \u00d7 Frequency \u00d7 Addressability pains become the "
                    "evidence base for Day 5's six-line problem statement, and the same pains "
                    "resurface in Week 2 Day 3's heuristic audit as concrete UX failures.",
        "artifacts": ["5 Whys worksheets", "Pain theme affinity map", "Severity x Frequency x Addressability scoring sheet"],
        "diagram": (
            '<figure class="mini-diagram"><div class="whys-chain">'
            '<div class="wc-box">Symptom: users abandon the task partway through</div>'
            '<span class="wc-arrow">&darr; Why?</span>'
            '<div class="wc-box">The next step was never made clear</div>'
            '<span class="wc-arrow">&darr; Why?</span>'
            '<div class="wc-box">The system gave no feedback after the action</div>'
            '<span class="wc-arrow">&darr; Why?</span>'
            '<div class="wc-box">No pattern confirms state changes back to the user</div>'
            '<span class="wc-arrow">&darr; Why?</span>'
            '<div class="wc-box wc-root">Root cause: missing status feedback breaks trust in the action</div>'
            '</div><div class="factor-row"><span class="factor-chip">Severity</span>'
            '<span class="factor-op">&times;</span><span class="factor-chip">Frequency</span>'
            '<span class="factor-op">&times;</span><span class="factor-chip">Addressability</span></div>'
            '<figcaption>5 Whys drives a symptom down to its root cause; the scoring formula decides '
            'what is actually worth solving.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week1", "day": "Day 5", "anchor": "d5",
        "title": "Problem Framing + Evidence",
        "what": "Compress validated pain into a six-line Problem Statement template and back it "
                "with an Evidence Brief that states data confidence and business impact, then "
                "present it in a readout.",
        "why": "A problem statement without evidence is an opinion. This day forces a hard stop "
               "before Week 2: no team moves into metrics work until the problem is written down "
               "in one crisp paragraph with a confidence rating attached, so leadership can "
               "challenge it before resources are committed.",
        "connects": "This six-line problem statement is the exact document Week 2 Day 1 opens with "
                    "when building the Metrics Pyramid -- the metric must prove this specific "
                    "problem is shrinking.",
        "artifacts": ["Six-line Problem Statement", "Evidence Brief", "Readout deck"],
    },
    {
        "week_id": "week2", "day": "Day 1", "anchor": "d1",
        "title": "Metrics Pyramid + KPIs",
        "what": "Build a three-tier Metrics Pyramid (North Star \u2192 KPI \u2192 Operational Signals), "
                "run a Vanity Metric detection pass, then write the Believable Causal Chain -- a "
                "three-sentence story of how a signal ripples up to the North Star -- and stress-test "
                "it in a pair Tier Sheet Defense round against the Three Standard Challenges: Causal "
                "Chain ('show me the ripple'), Gameability ('how would a team cheat this'), and "
                "Instrumentation ('can you measure this in production today').",
        "why": "Teams default to whatever metric is easiest to pull from a dashboard, which is "
               "usually a vanity metric. This day trains the discipline of tracing every "
               "operational signal upward until it ladders into something that would actually "
               "make the CEO and the front-line dispatcher agree the business is winning -- and the "
               "stress test catches hand-waved chains before they get defended in front of engineering.",
        "connects": "The KPI ladder built here is the scaffolding Day 2 uses to select the single "
                    "North Star metric at the top of the pyramid.",
        "artifacts": ["Metrics Tier Sheet", "Vanity Metric checklist", "Believable Causal Chain narrative", "Tier Sheet Defense notes"],
        "diagram": (
            '<figure class="mini-diagram"><div class="pyramid-diagram">'
            '<div class="pyramid-tier tier-1">North Star</div>'
            '<div class="pyramid-tier tier-2">KPIs</div>'
            '<div class="pyramid-tier tier-3">Operational Signals</div>'
            '</div><figcaption>Every operational signal must ladder upward through a Believable Causal '
            'Chain to the one North Star at the top.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week2", "day": "Day 2", "anchor": "d2",
        "title": "North Star Metric",
        "what": "Select one North Star Metric using a template that avoids three pitfalls -- vanity "
                "metrics, leading-indicator metrics, and gameable metrics -- and pair it with a "
                "counter-metric guardrail.",
        "why": "A North Star without a counter-metric can be 'won' by cheating the system (for "
               "example, faster onboarding achieved by skipping training). Every candidate North "
               "Star is pressure-tested with the 'CEO + Dispatcher test': would both a CEO and a "
               "front-line dispatcher agree this number means the business is truly winning?",
        "connects": "Once locked, this North Star statement becomes the fixed reference point that "
                    "every UX finding and design principle in Day 3, and every feature "
                    "prioritization decision after it, must trace back to.",
        "artifacts": ["North Star template", "Counter-metric definition"],
    },
    {
        "week_id": "week2", "day": "Day 3", "anchor": "d3",
        "title": "Product Design & UX (Heuristics + Accessibility + Principles)",
        "what": "Run a Heuristic Hunt against Nielsen's 10 usability heuristics -- (1) visibility of "
                "system status, (2) match between system and the real world, (3) user control and "
                "freedom, (4) consistency and standards, (5) error prevention, (6) recognition rather "
                "than recall, (7) flexibility and efficiency of use, (8) aesthetic and minimalist "
                "design, (9) helping users recognize/diagnose/recover from errors, and (10) help and "
                "documentation -- plus 3 TPM-specific lenses (time-to-first-value, failure-mode "
                "dignity, power-user respect), complete an 8-check Accessibility Floor audit, score "
                "findings 1-5 by severity, and distill the worst findings into 3 durable Design "
                "Principles.",
        "why": "Subjective complaints like 'the form feels clunky' can't be prioritized by "
               "engineering. Converting them into named heuristics with severity scores makes UX "
               "debt as concrete and fundable as a bug ticket, and the accessibility floor makes "
               "sure the fix serves every dispatcher, not just the majority.",
        "connects": "The 3 Design Principles produced here become the explicit filter Day 4's "
                    "competitive research and Day 5's journey mapping must be evaluated against, "
                    "and later the acceptance criteria in Week 3 PRDs must satisfy them.",
        "artifacts": ["Heuristic Audit (13 heuristics)", "Accessibility Floor Audit (8 checks)", "3 Design Principles"],
        "diagram": (
            '<figure class="mini-diagram"><div class="heuristic-grid">'
            '<span class="heuristic-chip"><span class="hc-num">1</span>Visibility of Status</span>'
            '<span class="heuristic-chip"><span class="hc-num">2</span>Match Real World</span>'
            '<span class="heuristic-chip"><span class="hc-num">3</span>User Control</span>'
            '<span class="heuristic-chip"><span class="hc-num">4</span>Consistency</span>'
            '<span class="heuristic-chip"><span class="hc-num">5</span>Error Prevention</span>'
            '<span class="heuristic-chip"><span class="hc-num">6</span>Recognition &gt; Recall</span>'
            '<span class="heuristic-chip"><span class="hc-num">7</span>Flexibility</span>'
            '<span class="heuristic-chip"><span class="hc-num">8</span>Minimalist Design</span>'
            '<span class="heuristic-chip"><span class="hc-num">9</span>Error Recovery</span>'
            '<span class="heuristic-chip"><span class="hc-num">10</span>Help &amp; Docs</span>'
            '</div><figcaption>Nielsen\'s 10 usability heuristics &mdash; the scoring grid behind every '
            'Heuristic Hunt finding.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week2", "day": "Day 4", "anchor": "d4",
        "title": "AI for Strategy & Research",
        "what": "Use a Validated Synthesis Prompt to synthesize multi-source research (interview "
                "transcripts, support tickets, analyst reports, competitor tours) while watching for "
                "4 named failure modes -- theme inflation (lumping distinct complaints under one "
                "vague category), citation invention (citing a source that doesn't exist), "
                "premature confidence (a plausible summary with no acknowledged gaps), and source "
                "bias (over-weighting the loudest source) -- then stay on the safe side of a strict "
                "'bright line' rule (structure source material, never ask AI to invent market facts) "
                "to build a Competitive Snapshot with a Provenance Log tracing every claim to its source.",
        "why": "AI-assisted competitive research fails in predictable ways -- summarizing "
               "training-data guesses as fact, blending sources, dropping caveats, inventing "
               "numbers. This day installs a discipline (cross-validating every citation, provenance "
               "logging, the bright-line rule) that makes the research defensible in front of "
               "engineering and leadership, not just plausible-sounding.",
        "connects": "The Competitive Snapshot becomes ammunition for Day 5's journey mapping (where "
                    "do competitors already solve a friction point we haven't?) and for the PRD's "
                    "'Required Inputs' in Week 3, which explicitly calls for constraints informed by "
                    "this research.",
        "artifacts": ["Validated Synthesis Prompt", "Competitive Snapshot matrix", "Provenance Log"],
    },
    {
        "week_id": "week2", "day": "Day 5", "anchor": "d5",
        "title": "Customer Journey Mapping",
        "what": "Map the end-to-end customer journey stage by stage and locate friction hotspots, "
                "evaluating each stage through the lens of the 3 Design Principles from Day 3.",
        "why": "A heuristic audit finds isolated UX bugs; a journey map finds where those bugs "
               "compound across a real end-to-end flow (for example, a validation gap on screen 2 "
               "causes a support escalation three steps later). This connects isolated findings "
               "into a single narrative of where the product currently fails the North Star.",
        "connects": "Friction hotspots identified here become the 'weird paths' that Week 3's "
                    "Acceptance Criteria must explicitly cover, so the PRD doesn't just describe "
                    "the happy path.",
        "artifacts": ["Customer Journey Map", "Friction hotspot list"],
        "diagram": (
            '<figure class="mini-diagram"><div class="journey-diagram">'
            '<div class="journey-stage"><span class="js-dot"></span><h5>Pre-shift</h5>'
            '<p>Arrive, review the day\'s dispatch</p></div>'
            '<div class="journey-stage"><span class="js-dot"></span><h5>On-shift</h5>'
            '<p>Execute assigned jobs</p></div>'
            '<div class="journey-stage friction"><span class="js-dot"></span><h5>Mid-shift Change</h5>'
            '<p>The canonical disruption &mdash; an exception hits</p></div>'
            '<div class="journey-stage"><span class="js-dot"></span><h5>After-shift</h5>'
            '<p>Reconcile and close out</p></div>'
            '</div><div class="journey-legend">'
            '<span><span class="dot" style="background:var(--accent)"></span>stage</span>'
            '<span><span class="dot" style="background:var(--warn)"></span>friction star</span>'
            '</div><figcaption>One persona, one scope, 5-8 stages &mdash; friction stars cluster at 2-3 '
            'stages, not every stage.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week3", "day": "Day 1", "anchor": "d1",
        "title": "PRD Sections 1\u20135 (Problem \u2192 Solution Sketch)",
        "what": "Draft the first half of a Product Requirements Document: the problem/outcome "
                "statement, a solution sketch (user-visible flow, not implementation detail), and "
                "a first pass at acceptance criteria.",
        "why": "The PRD is the first artifact engineering actually builds from, so this translates "
               "five weeks of discovery, metrics, and design work into a single build-ready "
               "document -- if any prior step was skipped, it becomes visible here as a section "
               "leadership can't fill in.",
        "connects": "This draft is deliberately incomplete -- it hands off directly to Day 2's "
                    "acceptance-criteria hardening pass, because a solution sketch without testable "
                    "AC is not yet buildable.",
        "artifacts": ["PRD draft (Sections 1-5)", "Solution sketch"],
    },
    {
        "week_id": "week3", "day": "Day 2", "anchor": "d2",
        "title": "Acceptance Criteria",
        "what": "Write testable Acceptance Criteria that explicitly cover 'weird paths' (edge "
                "cases, error states, offline conditions) in addition to the happy path.",
        "why": "An AC that only describes the happy path guarantees engineers will ask clarifying "
               "questions mid-sprint or ship a feature that breaks on the first edge case a real "
               "dispatcher hits. This is isolated as its own day because it is the single "
               "highest-leverage place a TPM prevents rework.",
        "connects": "The weird-path list drafted here is cross-checked against Day 3's NFR "
                    "categories (what happens under bad network, high load, or invalid input) so "
                    "reliability requirements aren't an afterthought.",
        "artifacts": ["Acceptance Criteria set", "Weird-path checklist"],
    },
    {
        "week_id": "week3", "day": "Day 3", "anchor": "d3",
        "title": "NFRs + Dependencies",
        "what": "Define Non-Functional Requirements across 5 categories (Performance, Reliability, "
                "Security, Usability, Maintainability) in Requirement / Defense / Verification "
                "form, and log dependencies with a named owner and due-by date.",
        "why": "An NFR that just says 'must be fast' can't be verified. Writing it as Requirement "
               "(the target), Defense (how the design meets it), Verification (how you'll prove it) "
               "forces the same rigor non-functional quality gets that functional features already "
               "have -- this is exactly how the course source material explains the Performance "
               "category.",
        "connects": "Named dependency owners and dates feed directly into Day 4's Risk section, "
                    "since an unowned dependency is the most common hidden risk in a PRD.",
        "artifacts": ["NFR sheet (Requirement/Defense/Verification)", "Dependency log with owners"],
    },
    {
        "week_id": "week3", "day": "Day 4", "anchor": "d4",
        "title": "PRD Mini-Capstone (Risk + Draft Assembly)",
        "what": "Assemble the full PRD draft -- problem statement through NFRs -- and add a Risks "
                "section with mitigations and explicitly flagged open decisions.",
        "why": "This is the first day the PRD is judged as a whole artifact rather than section by "
               "section, which surfaces gaps that don't show up when sections are written in "
               "isolation (for example, an AC that contradicts an NFR). Naming open decisions "
               "explicitly, instead of quietly picking one, keeps leadership able to weigh in "
               "before build starts.",
        "connects": "This assembled draft is the exact input to Day 5's peer review pass, where a "
                    "second set of eyes scores it against the same rigor bar before it is called "
                    "engineer-ready.",
        "artifacts": ["Assembled PRD draft", "Risk register with mitigations", "Open decisions list"],
    },
    {
        "week_id": "week3", "day": "Day 5", "anchor": "d5",
        "title": "PRD Review (Capstone)",
        "what": "Run a structured peer review of the completed PRD against a scoring rubric, then "
                "revise it into a final, engineer-ready version.",
        "why": "A PRD that only its author has read still carries that author's blind spots. Every "
               "PRD produced in the course is pressure-tested by a peer using the same rubric an "
               "engineering lead would use, closing the loop that started with Working Backwards "
               "in Week 1.",
        "connects": "The revised, scored PRD is the exact document Week 4 Day 1 opens with -- "
                    "architecture decisions are made against this PRD's constraints, not a rough "
                    "draft.",
        "artifacts": ["PRD review scorecard", "Final engineer-ready PRD"],
    },
    {
        "week_id": "week4", "day": "Day 1", "anchor": "d1",
        "title": "Monolith vs Microservices (Architecture Decisioning)",
        "what": "Run a monolith-vs-microservices triage using named constraints (team size, "
                "deployment cadence, failure isolation needs) taken from the PRD, then produce an "
                "integration map with explicit contracts between systems.",
        "why": "The course materials are explicit that the TPM's role here is not to make the "
               "architecture decision for engineering, but to name the constraints that should "
               "drive it -- confusing those two roles is the most common way TPMs either overstep "
               "or under-deliver at this stage.",
        "connects": "This is the course's final handoff: the integration map and named constraints "
                    "are what engineering uses to actually scope and build the product that began "
                    "as a single observed pain point back in Week 1 Day 4.",
        "artifacts": ["Mono-vs-Micro Triage Pack", "Integration/contract map"],
        "diagram": (
            '<figure class="mini-diagram"><div class="arch-compare">'
            '<div class="arch-mono-block">MONOLITH<span class="arch-sub">One deployable, shared codebase</span></div>'
            '<span class="ac-vs">VS</span>'
            '<div class="arch-micro-grid">'
            '<span class="arch-micro-block">User Service</span>'
            '<span class="arch-micro-block">Billing Service</span>'
            '<span class="arch-micro-block">Notification Service</span>'
            '<span class="arch-micro-block">Reporting Service</span>'
            '</div></div><figcaption>The triage weighs team size, deployment cadence, and failure '
            'isolation &mdash; not hype &mdash; to choose a side.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week4", "day": "Day 2", "anchor": "d2",
        "title": "System Security & Compliance (STRIDE Threat Model)",
        "what": "Run a STRIDE threat-model pass -- Spoofing, Tampering, Repudiation, Information "
                "disclosure, Denial of service, Elevation of privilege -- across every integration "
                "boundary in Day 1's map, cull to the top 5 threats with a named owner each, check "
                "which compliance frame applies (SOC 2, a privacy regime, or an industry-specific "
                "rule), and rewrite the PRD's first-draft Security & Compliance NFRs at the "
                "architecture level.",
        "why": "The course is explicit that a TPM is not the security expert -- the job is to drive "
               "the right conversation with security and hand over a starting threat model the "
               "security team can validate, not build from scratch. Skipping this step means the "
               "PRD's Week 3 first-draft NFRs, written before the architecture existed, ship "
               "unchanged against a real attack surface nobody ever walked.",
        "connects": "The top-5 threats and revised NFRs become TCD Section 3 -- a sibling to the "
                    "PRD's Section 7, not a replacement -- and the named owners and open questions "
                    "feed straight into the 1-page security brief that gets handed to an actual "
                    "security partner before build starts.",
        "artifacts": ["STRIDE threat model (top-5 threats)", "Revised Security & Compliance NFRs (TCD \u00a73)", "Security stakeholder brief"],
        "diagram": (
            '<figure class="mini-diagram"><div class="stride-grid">'
            '<span class="heuristic-chip"><span class="hc-num">S</span>Spoofing</span>'
            '<span class="heuristic-chip"><span class="hc-num">T</span>Tampering</span>'
            '<span class="heuristic-chip"><span class="hc-num">R</span>Repudiation</span>'
            '<span class="heuristic-chip"><span class="hc-num">I</span>Info. Disclosure</span>'
            '<span class="heuristic-chip"><span class="hc-num">D</span>Denial of Service</span>'
            '<span class="heuristic-chip"><span class="hc-num">E</span>Elevation of Privilege</span>'
            '</div><figcaption>STRIDE &mdash; walked at every arrow (data in motion) and box (data at '
            'rest) in the integration map.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week4", "day": "Day 3", "anchor": "d3",
        "title": "Mapping System Components (C4 Diagrams)",
        "what": "Draw two C4-style diagrams for the feature - a Context diagram (Level 1: the system, "
                "its people, and external neighbors) and a Container diagram (Level 2: every "
                "independently deployable unit and how they talk) - then stress-test both against "
                "three lenses: failure, trust boundary, and evolvability.",
        "why": "Prose descriptions of architecture hide gaps that a real diagram exposes immediately. "
               "The course is explicit that Component- and Code-level diagrams are engineering's job, "
               "not the TPM's - the TPM's job is Context + Container, drawn well enough that an "
               "outsider or a security reviewer can follow it in under 90 seconds.",
        "connects": "The Container diagram becomes the direct input to Day 4's per-hop latency "
                    "budgeting, and the trust-boundary markings feed straight into Day 2's STRIDE "
                    "threat model as the concrete boundaries an attacker could actually cross.",
        "artifacts": ["C4 Context diagram", "C4 Container diagram", "Trust-boundary markup", "Three-Lens stress test (failure / trust boundary / evolvability)"],
        "diagram": (
            '<figure class="mini-diagram"><div class="flow-strip">'
            '<span class="fs-box">People / Roles</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box fs-accent">System (Context)</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Containers / Modules</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">External Systems</span>'
            '</div><figcaption>Two diagrams, not one: Context (who and what talks to the system) and '
            'Container (what deploys independently inside it) &mdash; Component and Code levels stay '
            'with engineering.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week4", "day": "Day 4", "anchor": "d4",
        "title": "Latency, Availability & Rate Limits (SLOs)",
        "what": "Set three SLOs - latency (p<N> \u2264 Xms), availability (N% over a window, with an "
                "error budget), and a rate-limit policy - then walk the Day 3 Container diagram hop "
                "by hop to check whether the real architecture can actually hit the latency target.",
        "why": "An SLO without a percentile, a window, and a defense is a guess dressed up as a "
               "number. The error budget turns an abstract percentage into a decision tool - inside "
               "budget, ship features; near or past it, prioritize reliability - so a team can tell "
               "objectively when to slow down instead of arguing about vibes.",
        "connects": "The latency-budget walk's dominant-hop finding becomes Day 5's evidence for a "
                    "durability-vs-latency trade-off, and all three SLOs carry forward unchanged into "
                    "Week 5's data-layer and cloud-topology decisions as the numbers every later "
                    "choice must protect.",
        "artifacts": ["Latency / Availability / Rate-limit SLO sheet", "Latency-budget walk (hop-by-hop)", "AI sanity-check provenance note"],
        "diagram": (
            '<figure class="mini-diagram"><div class="flow-strip">'
            '<span class="fs-box">Latency SLO</span><span class="fs-arrow">+</span>'
            '<span class="fs-box">Availability SLO</span><span class="fs-arrow">+</span>'
            '<span class="fs-box fs-accent">Rate-Limit Policy</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Latency-Budget Walk</span>'
            '</div><figcaption>Three SLOs, then a hop-by-hop walk of the Day 3 Container diagram to '
            'check the architecture can actually hit the number.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week4", "day": "Day 5", "anchor": "d5",
        "title": "Technical Trade-Offs & TCD Assembly (Ship Day)",
        "what": "Write the top 5 technical trade-offs in a strict Option A vs Option B \u2192 Choice \u2192 "
                "Accepted cost \u2192 Revisit trigger format spanning at least 3 tension categories, "
                "build a stakeholder sign-off matrix with a named real person per constraint, then "
                "integrate and cross-review all 6 TCD sections before shipping.",
        "why": "A trade-off that only describes the choice made ('we picked a monolith') isn't a "
               "trade-off - naming the accepted cost and the revisit trigger is what separates senior "
               "architectural thinking from a feature list, and a constraint with no named owner is a "
               "constraint nobody actually implements.",
        "connects": "This is the final Week 4 handoff - the shipped Technical Considerations Document "
                    "(TCD, 6 sections) becomes the spine Week 5 builds on: its component map drives the "
                    "data model, its SLOs set the performance baseline, and its threat model drives "
                    "encryption and key-management decisions.",
        "artifacts": ["Top-5 Trade-Offs (TCD Section 5)", "Stakeholder Sign-Off Matrix (TCD Section 6)", "Integration + cross-review checklist", "Shipped TCD status: Approved / Approved with gaps"],
        "diagram": (
            '<figure class="mini-diagram"><div class="flow-strip">'
            '<span class="fs-box">Option A</span><span class="fs-arrow">vs</span>'
            '<span class="fs-box">Option B</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box fs-accent">Choice + Accepted Cost</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Revisit Trigger</span>'
            '</div><figcaption>The exact trade-off pattern, repeated 5 times, then locked to a named '
            'stakeholder before the TCD ships.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week5", "day": "Day 1", "anchor": "d1",
        "title": "Database Structures & Data Logic",
        "what": "Apply 'Access Pattern First' discipline: list every read and write the feature needs "
                "before drawing any table, then design an entity model (fields, primary/foreign keys, "
                "indexes tied to a numbered access pattern, cardinalities, invariants), pressure-test "
                "it against 3 canonical storage trade-offs, and run an AI-assisted schema critique.",
        "why": "A schema designed before its queries are known is a schema that discovers slow queries "
               "in production. Naming the access pattern first, and requiring every field and index to "
               "trace back to a numbered pattern, is what keeps a TPM's data model defensible to an "
               "engineer instead of just plausible-looking.",
        "connects": "This produces TMD (Technical Modeling Document) Section 1 - the data model - "
                    "which Day 2 takes as-is to decide where each entity's storage physically runs in "
                    "the cloud, and which Day 3 uses directly to design the REST resources and URL "
                    "paths on top of it.",
        "artifacts": ["Access Pattern Sheet (reads + writes, numbered)", "Entity Model (fields/keys/indexes/invariants)", "3 Storage Trade-Offs (normalization, consistency, schema flexibility)", "AI schema critique + adopt/defer/reject log"],
        "diagram": (
            '<figure class="mini-diagram"><div class="flow-strip">'
            '<span class="fs-box fs-accent">List Every Read + Write</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Entity Model</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Storage Trade-Offs</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">AI Schema Critique</span>'
            '</div><figcaption>"Access Pattern First" &mdash; no table gets designed until every query '
            'it must serve is named and numbered.</figcaption></figure>'
        ),
    },
    {
        "week_id": "week5", "day": "Day 2", "anchor": "d2",
        "title": "Cloud Architecture & Infrastructure",
        "what": "Make five topology decisions for the feature's real component map: region + "
                "multi-AZ stance, managed-vs-self-managed per component (default managed unless a "
                "specific reason not to), multi-tenancy stance (pooled by default), network boundary "
                "(public HTTPS by default), and a rough-order-of-magnitude (ROM) monthly cost table, "
                "closing with a required AI sanity check for hidden risks.",
        "why": "Every topology choice has both a cost dimension and a risk dimension that's easy to "
               "hand-wave past. The day forces each choice to be defended against a real SLO, a real "
               "compliance fact, or real customer evidence instead of 'we want full control,' which "
               "the course names directly as an anti-pattern smell.",
        "connects": "This produces TMD Section 2 - cloud topology - built directly on top of Day 1's "
                    "entity model and the Week 4 Container diagram, and it hands Day 3 a concrete, "
                    "priced infrastructure picture to design the REST API contract against.",
        "artifacts": ["Region + AZ stance with trade-off", "Managed-vs-self table (every component)", "Multi-tenancy + network boundary stance", "ROM cost table", "AI sanity-check risk list"],
        "diagram": (
            '<figure class="mini-diagram"><div class="flow-strip">'
            '<span class="fs-box">Region + AZ</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Managed vs Self</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Tenancy + Network</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box fs-accent">ROM Cost + AI Sanity Check</span>'
            '</div><figcaption>Five topology decisions, each defended by a real SLO, compliance fact, '
            'or customer-evidence line &mdash; never by "we want full control."</figcaption></figure>'
        ),
    },
    {
        "week_id": "week5", "day": "Day 3", "anchor": "d3",
        "title": "REST & SOAP API Fundamentals",
        "what": "Model the feature's data entities as REST resources (deciding which ones are exposed "
                "as endpoints at all), design their URL paths and HTTP methods with correct status "
                "codes for happy/sad/weird paths, then fully document one endpoint end-to-end "
                "including idempotency, versioning, and error-body shape - closing with when SOAP is "
                "still the right default instead of REST.",
        "why": "Turning a data model into an API is where sloppy resource thinking becomes a "
               "permanent, hard-to-change public contract. The day trains catching two opposite "
               "mistakes: verbs disguised as resources, and every entity blindly exposed as an "
               "endpoint even when it's really internal plumbing (like an outbox table) that a client "
               "should never touch directly.",
        "connects": "This produces TMD Section 3 - the REST API contract - built directly on Day 1's "
                    "entity model and Day 2's cloud topology, and it's the last technical-modeling "
                    "layer before Week 5's remaining days stitch data, cloud, and API together into "
                    "full request sequence diagrams.",
        "artifacts": ["Resource list (with exclusions reasoned)", "URL path design", "Methods + status-code table", "One endpoint documented in full (idempotency, versioning, errors)"],
        "diagram": (
            '<figure class="mini-diagram"><div class="flow-strip">'
            '<span class="fs-box">Resources</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">URL Paths</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box">Methods + Status Codes</span><span class="fs-arrow">&rarr;</span>'
            '<span class="fs-box fs-accent">One Endpoint, Full Detail</span>'
            '</div><figcaption>Every entity is checked as a resource candidate first &mdash; internal '
            'plumbing (like an outbox table) deliberately stays off the API.</figcaption></figure>'
        ),
    },
]

WEEKS_META = [
    {
        "id": "week1", "number": 1, "label": "Week 1", "theme": "Understand The User",
        "blurb": "Discovery basics: prompting discipline, Working Backwards, validated personas, "
                 "root-cause pain framing, and evidence-backed problem statements.",
    },
    {
        "id": "week2", "number": 2, "label": "Week 2", "theme": "Define The Strategy",
        "blurb": "Turn pain into measurable direction: metrics pyramid, North Star, UX heuristic + "
                 "accessibility audits, AI-assisted competitive research, and journey mapping.",
    },
    {
        "id": "week3", "number": 3, "label": "Week 3", "theme": "Build The PRD",
        "blurb": "Turn strategy into build-ready requirements: PRD sections, testable acceptance "
                 "criteria, NFRs, dependencies, risk, and peer review.",
    },
    {
        "id": "week4", "number": 4, "label": "Week 4", "theme": "Decide The Architecture",
        "blurb": "Choose architecture using named constraints, STRIDE-threat-model it, draw C4 "
                 "Context + Container diagrams, set 3 SLOs with a latency-budget walk, then "
                 "negotiate the top trade-offs with a named stakeholder sign-off -- shipping a "
                 "6-section Technical Considerations Document (TCD), the final handoff to "
                 "engineering.",
    },
    {
        "id": "week5", "number": 5, "label": "Week 5", "theme": "Model The Technical Details",
        "blurb": "Turn the shipped TCD into a literal buildable system: an access-pattern-first "
                 "data model, a priced cloud topology, and a REST API contract -- the Technical "
                 "Modeling Document (TMD).",
    },
]


# ---------------------------------------------------------------------------
# MILESTONES: the key outcomes/artifacts every TPM produces across the
# lifecycle -- generic to the discipline, not tied to any one case study.
# Grounded in the course's own generic lab/template handouts.
# ---------------------------------------------------------------------------
MILESTONES = [
    {
        "id": "prfaq", "stage": "Week 1 \u00b7 Day 2", "title": "PR/FAQ (Working Backwards)", "week": 1,
        "definition": "A one-page press release plus FAQ for a product that does not exist yet, "
                      "written before any design or engineering work starts.",
        "why": "It forces the team to prove customer value in plain language before a single "
               "engineer is staffed. If the press release is weak, the product idea is weak -- and "
               "that is cheap to discover on paper, expensive to discover in production.",
        "inside": [
            "Six-part PR: heading, sub-heading, summary, problem, solution, customer quote",
            "The Five Customer Questions: who, what problem, one benefit, what evidence, what the moment of use looks like",
            "Internal FAQ: riskiest assumption, build estimate, what breaks under partial adoption",
        ],
        "sample": (
            '<h4>Heading</h4><p>FieldPulse Mobile Adds Offline Dispatch Assist, Cutting New-Dispatcher Escalations</p>'
            '<h4>Sub-heading</h4><p>New dispatchers can now complete a full shift of job assignments without a '
            'senior dispatcher&rsquo;s help, even with no signal.</p>'
            '<h4>Summary</h4><p>FieldPulse Mobile ships an offline-ready dispatch assistant that validates job '
            'assignments in real time and queues changes for sync, so a new dispatcher&rsquo;s first shift no '
            'longer depends on a senior teammate being available.</p>'
            '<h4>Problem</h4><p>New dispatchers escalate to a senior teammate multiple times per shift because '
            'the app allows invalid job assignments to be saved silently, and offline signal drops erase '
            'unsaved work.</p>'
            '<h4>Solution</h4><p>Inline validation blocks invalid saves before they happen, and an offline queue '
            'holds every change until connectivity returns, syncing automatically with no lost work.</p>'
            '<div class="sample-quote">&ldquo;My first solo shift, I didn&rsquo;t have to call anyone. The app '
            'told me exactly what was wrong before I hit save.&rdquo; &mdash; sample customer quote</div>'
            '<h4>Internal FAQ</h4>'
            '<p><strong>Riskiest assumption:</strong> dispatchers will trust an offline queue enough to keep '
            'working instead of waiting for signal.</p>'
            '<p><strong>Build estimate:</strong> 3 sprints for validation rules, 2 sprints for the offline queue '
            'and sync.</p>'
            '<p><strong>What breaks under partial adoption:</strong> if only some job types get validation '
            'rules, dispatchers will assume every field is validated &mdash; rollout has to cover every job '
            'type at once.</p>'
        ),
    },
    {
        "id": "persona", "stage": "Week 1 \u00b7 Day 3", "title": "Validated Persona & JTBD", "week": 1,
        "definition": "A persona built from observed behavior plus a Job-to-Be-Done statement, "
                      "checked against a Validation Canvas instead of assumed from a title or age range.",
        "why": "A persona built on demographics does not predict behavior. A validated 'who' and "
               "'why' keeps every later prioritization call traceable to a real user, not an "
               "assumption the team fell in love with.",
        "inside": [
            "Persona Validation Canvas",
            "Job-to-Be-Done statement (verb + circumstance, not a job title)",
            "Behavioral evidence citations backing every trait",
        ],
        "sample": (
            '<h4>Persona</h4><p><strong>Dana &mdash; New Dispatcher, first two weeks on the job.</strong> Hired '
            'for reliability, not software experience. Uses the mobile app one-handed while walking the floor.</p>'
            '<h4>Job to Be Done</h4><p>&ldquo;When I get a new list of jobs at the start of my shift, I want to '
            'assign each one correctly on the first try, so that I don&rsquo;t have to interrupt a senior '
            'dispatcher to double-check my work.&rdquo;</p>'
            '<h4>Behavioral evidence</h4><ul>'
            '<li>Re-opened the same job assignment 4 times in one shift before asking for help (observed shadow '
            'session)</li>'
            '<li>Waited an average of 6 minutes for a senior dispatcher to confirm a save before moving to the '
            'next job (support ticket logs)</li></ul>'
            '<h4>Validation Canvas check</h4><p>Confirmed against 5 shadow sessions and 12 support tickets '
            '&mdash; not assumed from job title or tenure alone.</p>'
        ),
    },
    {
        "id": "problem-statement", "stage": "Week 1 \u00b7 Day 5", "title": "Problem Statement + Evidence Brief", "week": 1,
        "definition": "A six-line problem statement backed by an Evidence Brief that states data "
                      "confidence and business impact.",
        "why": "A problem statement without evidence is an opinion. This is the hard stop before "
               "metrics work starts -- leadership can challenge the problem before any resource is "
               "committed to solving it.",
        "inside": [
            "Six-line Problem Statement template",
            "Evidence Brief with a stated confidence rating",
            "Readout deck built for leadership challenge, not just approval",
        ],
        "sample": (
            '<h4>Six-line Problem Statement</h4>'
            '<p>1. Who: new dispatchers in their first two weeks.</p>'
            '<p>2. What: they cannot complete a full shift of job assignments without senior help.</p>'
            '<p>3. Where/when: during job assignment, most often in the first 3 shifts.</p>'
            '<p>4. Impact: senior dispatchers lose roughly 30 minutes per shift to escalations.</p>'
            '<p>5. Root cause (hypothesis): no inline validation or offline recovery on the assignment form.</p>'
            '<p>6. Opportunity: reduce escalations without adding a training program.</p>'
            '<h4>Evidence Brief</h4>'
            '<p><strong>Confidence:</strong> high &mdash; corroborated by 12 support tickets and 5 shadow '
            'sessions.</p>'
            '<p><strong>Business impact:</strong> roughly 2.5 senior-dispatcher hours per week recovered for '
            'every 5 new hires onboarded.</p>'
        ),
    },
    {
        "id": "metrics-northstar", "stage": "Week 2 \u00b7 Days 1-2", "title": "Metrics Pyramid & North Star Metric", "week": 2,
        "definition": "A three-tier metrics ladder (Operational Signals \u2192 KPIs \u2192 North Star) "
                      "plus one North Star Metric, pressure-tested against three pitfalls and "
                      "stress-tested with the Three Standard Challenges.",
        "why": "Teams default to whatever metric is easiest to pull from a dashboard -- usually a "
               "vanity metric. The pyramid forces every signal to ladder into something a CEO and a "
               "front-line worker would both agree means the business is winning.",
        "inside": [
            "Metrics Tier Sheet (North Star / KPI / Operational Signals)",
            "Believable Causal Chain -- a three-sentence story from signal to North Star",
            "Three Standard Challenges: Causal Chain, Gameability, Instrumentation",
            "North Star template with a counter-metric guardrail",
        ],
        "sample": (
            '<h4>Metrics Tier Sheet</h4>'
            '<div class="table-wrap"><table><thead><tr><th scope="col">Tier</th><th scope="col">Metric</th></tr>'
            '</thead><tbody>'
            '<tr><td>North Star</td><td>% of new dispatchers completing a full shift independently</td></tr>'
            '<tr><td>KPI</td><td>Escalations per new-dispatcher shift</td></tr>'
            '<tr><td>Operational Signal</td><td>Invalid-save attempts blocked by validation</td></tr>'
            '</tbody></table></div>'
            '<h4>Believable Causal Chain</h4><p>Blocking an invalid save (signal) reduces confused re-attempts, '
            'which reduces escalations (KPI), which increases the share of shifts completed independently '
            '(North Star).</p>'
            '<h4>North Star Statement</h4><p>&ldquo;We are winning when new dispatchers complete their first '
            'full day independently, with zero senior intervention, at &ge;85% accuracy.&rdquo; '
            '<strong>Counter-metric:</strong> job-assignment error rate must not rise as escalations fall.</p>'
        ),
    },
    {
        "id": "design-principles", "stage": "Week 2 \u00b7 Day 3", "title": "Heuristic Audit & Design Principles", "week": 2,
        "definition": "A severity-scored UX audit against Nielsen's 10 usability heuristics plus 3 "
                      "TPM-specific lenses, distilled into 3 durable design principles.",
        "why": "Subjective complaints like 'the form feels clunky' cannot be prioritized by "
               "engineering. Naming the exact heuristic and severity turns UX debt into a fundable "
               "ticket, and a design principle tells the team what to choose when two options compete.",
        "inside": [
            "Nielsen's 10 heuristics, scored pass / partial / fail",
            "3 TPM lenses: time-to-first-value, failure-mode dignity, power-user respect",
            "8-point Accessibility Floor checklist",
            "1-5 severity scoring guide",
            "3-Principle Card: one line + one decision it forces, per principle",
        ],
        "sample": (
            '<h4>Sample Finding</h4>'
            '<div class="table-wrap"><table><thead><tr><th scope="col">Heuristic</th><th scope="col">Finding</th>'
            '<th scope="col">Severity</th></tr></thead><tbody>'
            '<tr><td>Error Prevention</td><td>Form saves an incomplete job assignment with no warning</td>'
            '<td>5 (Critical)</td></tr></tbody></table></div>'
            '<h4>Design Principle Derived</h4><p><strong>&ldquo;Stop invalid data before Save, not after.&rdquo;'
            '</strong> One-line rule: valid data only, never save invalid data hoping someone fixes it later. '
            'Decision it forces: every required field is validated before the Save button is enabled.</p>'
        ),
    },
    {
        "id": "journey-map", "stage": "Week 2 \u00b7 Day 5", "title": "Customer Journey Map", "week": 2,
        "definition": "A stage-by-stage map of the end-to-end customer journey that locates friction "
                      "hotspots and evaluates each stage against the design principles.",
        "why": "A heuristic audit finds isolated UX bugs. A journey map finds where those bugs "
               "compound across a real flow -- for example, a validation gap on one screen causing a "
               "support escalation three steps later. It turns isolated findings into one narrative "
               "of where the product currently fails the North Star.",
        "inside": [
            "Journey Map Canvas (stage, action, emotion, friction)",
            "Friction hotspot list tied back to Week 1 pain points",
            "Feature-prioritization frame (top 3 concepts, each tied to a friction point and a metric)",
        ],
        "sample": (
            '<h4>Sample Journey Map Canvas</h4>'
            '<div class="table-wrap"><table><thead><tr><th scope="col">Stage</th><th scope="col">Action</th>'
            '<th scope="col">Emotion</th><th scope="col">Friction?</th></tr></thead><tbody>'
            '<tr><td>Pre-shift</td><td>Review dispatch list</td><td>Neutral</td><td>&mdash;</td></tr>'
            '<tr><td>On-shift</td><td>Assign first job</td><td>Confident</td><td>&mdash;</td></tr>'
            '<tr><td>Mid-shift change</td><td>Reassign after a cancellation</td><td>Frustrated</td>'
            '<td>&#9733; Save silently fails</td></tr>'
            '<tr><td>After-shift</td><td>Reconcile completed jobs</td><td>Relieved</td><td>&mdash;</td></tr>'
            '</tbody></table></div>'
            '<h4>Top Friction &rarr; Feature Concept</h4><p>Silent save failure during reassignment &rarr; '
            'inline validation plus a confirmation toast, tied to the escalations-per-shift KPI.</p>'
        ),
    },
    {
        "id": "prd", "stage": "Week 3 \u00b7 Days 1-5", "title": "Product Requirements Document (PRD)", "week": 3,
        "definition": "An 11-section PRD skeleton -- drafted section by section across the week and "
                      "peer-reviewed before it is called engineer-ready.",
        "why": "The PRD is the first artifact engineering actually builds from. It is where five "
               "weeks of discovery, metrics, and design work either translate into a buildable "
               "document, or where a skipped step becomes visible as a section nobody can fill in.",
        "inside": [
            "\u00a71-2 Context + Problem, grounded in Week 1 interviews and the Week 2 journey map",
            "\u00a73-4 Goals & non-goals + Scope (in / out)",
            "\u00a75 Solution sketch -- user-visible flow, no implementation detail",
            "\u00a76 Acceptance Criteria -- happy / sad / weird paths in Given/When/Then form",
            "\u00a77 NFRs across 5 categories: Performance, Reliability, Security, Usability, Maintainability",
            "\u00a78 Metrics & validation, \u00a79 Risks & open questions, \u00a710 Dependencies, \u00a711 Out-of-scope follow-ups",
            "Peer review scorecard before the draft is called engineer-ready",
        ],
        "sample": (
            '<h4>&sect;1-2 Context + Problem (excerpt)</h4><p>New dispatchers cannot complete a full shift '
            'independently because the assignment form allows invalid saves and loses work when offline.</p>'
            '<h4>&sect;5 Solution Sketch (excerpt)</h4><p>On Save, validate required fields inline; on '
            'connectivity loss, queue the change locally and sync automatically once signal returns.</p>'
            '<h4>&sect;6 Acceptance Criteria (excerpt)</h4>'
            '<p>Given a dispatcher submits an assignment missing a required field, when they tap Save, then the '
            'form blocks the save and highlights the missing field.</p>'
            '<p>Given a dispatcher is offline, when they save an assignment, then the change is queued and a '
            '&ldquo;Pending Sync&rdquo; badge is shown.</p>'
            '<h4>&sect;7 NFR sample (Reliability)</h4>'
            '<p><strong>Requirement:</strong> no queued change is lost across an app restart. '
            '<strong>Defense:</strong> the queue persists to local storage. '
            '<strong>Verification:</strong> kill-and-relaunch test with 10 queued changes.</p>'
            '<p class="mini-note">This is a short excerpt &mdash; the full PRD runs all 11 sections end to '
            'end.</p>'
        ),
    },
    {
        "id": "architecture-decision", "stage": "Week 4 \u00b7 Day 1", "title": "Architecture Decision & Integration Map", "week": 4,
        "definition": "A monolith-vs-microservices triage using named constraints pulled straight "
                      "from the PRD (team size, deployment cadence, failure isolation needs), "
                      "producing an integration map with explicit contracts between systems.",
        "why": "The TPM's job here is not to make the architecture call for engineering -- it is to "
               "name the constraints that should drive it. Confusing those two roles is the most "
               "common way a TPM either overreaches or under-delivers at this stage.",
        "inside": [
            "Mono-vs-Micro Triage Pack",
            "Named constraints sourced directly from the PRD",
            "Integration / contract map engineering can actually scope against",
        ],
        "sample": (
            '<h4>Named Constraints (from the PRD)</h4><ul>'
            '<li>Team size: 4 engineers</li>'
            '<li>Deployment cadence: weekly</li>'
            '<li>Failure isolation: offline sync must not block core dispatch</li></ul>'
            '<h4>Triage Result</h4><p>Modular monolith, with the offline-sync queue isolated behind its own '
            'internal service boundary and contract &mdash; full microservices would outrun a 4-engineer '
            'team&rsquo;s deployment cadence.</p>'
            '<h4>Integration / Contract Map (excerpt)</h4><p>Dispatch module &rarr; Sync Queue module: contract '
            '= <code>{jobId, changeType, payload, clientTimestamp}</code>, delivered at-least-once, '
            'deduplicated by <code>clientTimestamp</code>.</p>'
        ),
    },    {
        "id": "threat-model", "stage": "Week 4 \u00b7 Day 2", "title": "STRIDE Threat Model & Security NFRs (TCD \u00a73)", "week": 4,
        "definition": "A STRIDE threat-model walk across every integration boundary in the "
                      "architecture, culled to the top 5 threats, translated into revised, "
                      "architecture-level Security & Compliance NFRs that supersede the PRD's "
                      "first-draft version.",
        "why": "A TPM doesn't write the compliance program or design the mitigation -- but naming "
               "which compliance frame applies and pinning a threat to a specific arrow or box in "
               "the data flow is what turns a vague 'is this secure?' into a conversation a real "
               "security team can actually validate.",
        "inside": [
            "STRIDE walk across the architecture's data flow (boxes + arrows)",
            "Top-5 threats, each with likelihood, impact, mitigation, and a named owner",
            "Compliance frame check (SOC 2 / privacy regime / industry-specific)",
            "Revised Security & Compliance NFRs (Requirement / Defense / Verification)",
        ],
        "sample": (
            '<h4>Top Threat (STRIDE walk excerpt)</h4>'
            '<p><strong>Threat &mdash; Session token replay</strong><br>'
            '<strong>STRIDE letter:</strong> Spoofing<br>'
            '<strong>Where:</strong> Backend service &rarr; Datastore arrow, right after session token '
            'issuance<br>'
            '<strong>Scenario:</strong> A captured token is replayed from a second device before it '
            'expires.<br>'
            '<strong>Likelihood:</strong> M &nbsp; <strong>Impact:</strong> H<br>'
            '<strong>Mitigation:</strong> Bind the token to a device fingerprint with a 15-minute '
            'expiry &mdash; not "use HTTPS."<br>'
            '<strong>Owner:</strong> Security team (validate the binding approach)</p>'
            '<h4>Compliance Frame Check</h4><ul>'
            '<li>SOC 2: user-action audit trail required (CC7.2), 24-month retention</li>'
            '<li>Privacy: dispatcher PII processed &mdash; a state-level privacy regime applies</li>'
            '<li>Industry-specific: none directly for this feature</li></ul>'
            '<h4>Revised NFR (TCD &sect;3)</h4>'
            '<p><strong>Category:</strong> Security<br>'
            '<strong>Requirement:</strong> Session tokens are bound to a device fingerprint and expire '
            'after 15 minutes.<br>'
            '<strong>Defense:</strong> Directly mitigates the Spoofing threat found in the STRIDE '
            'walk.<br>'
            '<strong>Verification:</strong> Replay a captured token from a second device; access must '
            'be denied.</p>'
            '<p class="mini-note">TCD &sect;3 deepens the PRD&rsquo;s &sect;7 NFRs &mdash; it does not '
            'replace them.</p>'
        ),
    },
    {
        "id": "c4-diagrams", "stage": "Week 4 \u00b7 Day 3", "title": "C4 Context + Container Diagrams", "week": 4,
        "definition": "Two C4-style diagrams -- Context (system + people + external neighbors) and "
                      "Container (every independently deployable unit + how they talk) -- "
                      "stress-tested against failure, trust-boundary, and evolvability lenses.",
        "why": "A diagram a security reviewer or an outsider can follow in 90 seconds replaces "
               "architecture hand-waving with a shared visual vocabulary. The TPM's scope stops at "
               "Context + Container -- Component and Code levels are engineering's job.",
        "inside": [
            "C4 legend (owned-by-us vs. external, sync vs. async arrow, person)",
            "Trust-boundary markup wherever data crosses from our control to someone else's",
            "Three-Lens stress test: failure trace, trust boundary, evolvability",
        ],
        "sample": (
            '<h4>Trust-Boundary Finding (sample)</h4><p>A shared platform audit-log topic was first '
            'drawn as &ldquo;owned by us&rdquo; &mdash; re-checking the container table showed the true '
            'owner is Platform Compliance/Infra. Corrected to cross a trust boundary, the exact mistake '
            'the course warns about: a shared system is not automatically part of &ldquo;our '
            'system.&rdquo;</p>'
            '<h4>Failure Trace (sample)</h4><p>&ldquo;What happens when the audit topic is full?&rdquo; '
            'exposed that the diagram had no drawn retry/dead-letter box between the app and the queue '
            '&mdash; a real gap, logged as an open engineering question, not silently fixed.</p>'
        ),
    },
    {
        "id": "slo-sheet", "stage": "Week 4 \u00b7 Day 4", "title": "Three SLOs + Latency-Budget Walk", "week": 4,
        "definition": "A latency SLO, an availability SLO with an error budget, and a rate-limit "
                      "policy, each passing a percentile + window + defense check, then walked "
                      "hop-by-hop across the real Container diagram to verify the architecture can "
                      "hit the number.",
        "why": "An SLO without a percentile, a window, and a defense is an opinion wearing a "
               "number's clothes. The error budget converts an abstract percentage into a decision "
               "tool that tells a team objectively when to ship features versus when to stop and "
               "fix reliability.",
        "inside": [
            "Latency SLO: p95 \u2264 2.0s / p99 \u2264 5.0s, 30-day window",
            "Availability SLO: 99.5%, \u2248 3.6 hr/month error budget",
            "Rate-limit policy: per-user/per-tenant caps + 429 failure mode",
            "Hop-by-hop latency-budget walk vs. the SLO target",
        ],
        "sample": (
            '<h4>Latency-Budget Walk (sample)</h4><p>Network-in 80ms &rarr; auth check 40ms &rarr; '
            'orchestration API 150ms (dominant hop) &rarr; database write 30ms &rarr; network-out 100ms '
            '= 400ms happy path, comfortably inside the SLO. But the API&rsquo;s own 3-retry backoff '
            'policy pushes the true worst case to &asymp;4,200ms &mdash; still inside p99 \u2264 5.0s, but '
            'with only &asymp;800ms of headroom, not the &asymp;2,400ms the happy-path math alone '
            'implied.</p>'
        ),
    },
    {
        "id": "tcd-shipped", "stage": "Week 4 \u00b7 Day 5", "title": "Top-5 Trade-Offs + TCD Shipped", "week": 4,
        "definition": "Five technical trade-offs in strict Option A vs Option B \u2192 Choice \u2192 "
                      "Accepted cost \u2192 Revisit trigger form, a stakeholder sign-off matrix with a "
                      "named real person per constraint, and a full 6-section Technical "
                      "Considerations Document (TCD) shipped after integration + cross-review.",
        "why": "'We considered microservices but chose a monolith' is a description, not a "
               "trade-off -- naming the accepted cost and the revisit trigger is what separates "
               "senior architectural thinking from a feature list, and a constraint with no named "
               "owner never actually gets implemented.",
        "inside": [
            "5 trade-offs spanning \u2265 3 tension categories",
            "Stakeholder sign-off matrix (real names, honest status -- mostly 'Proposed,' not 'Approved')",
            "6-row integration checklist across all TCD sections",
            "Cross-review + AI sanity check before shipping",
        ],
        "sample": (
            '<h4>Trade-Off (sample)</h4><p><strong>Tension:</strong> latency vs. durability. '
            '<strong>Option A:</strong> write the audit record synchronously. <strong>Option B:</strong> '
            'publish it async with a dead-letter queue. <strong>Choice:</strong> B. '
            '<strong>Accepted cost:</strong> a rare failure can lag the audit trail by up to 10 '
            'seconds. <strong>Revisit trigger:</strong> if audit-lag complaints appear in a compliance '
            'review.</p>'
            '<h4>Ship Status</h4><p>TCD Status: <strong>Approved with gaps</strong> &mdash; honestly '
            'naming what is still open (an unresolved dependency, one trade-off flagged as '
            'under-defended) rather than rubber-stamping every row &ldquo;Approved.&rdquo;</p>'
        ),
    },
    {
        "id": "tmd-data-model", "stage": "Week 5 \u00b7 Day 1", "title": "TMD Section 1 \u2013 Data Model", "week": 5,
        "definition": "An entity model -- fields, keys, indexes tied to a numbered access pattern, "
                      "cardinalities, invariants -- built only after every read and write the "
                      "feature needs has been listed and numbered first.",
        "why": "'Access Pattern First' exists because a schema designed before its queries are "
               "known is a schema that discovers slow queries in production; requiring every index "
               "to cite a numbered pattern keeps the model defensible to an engineer, not just "
               "plausible-looking.",
        "inside": [
            "Access Pattern Sheet (reads + writes, numbered, highest-volume reads circled)",
            "Entity Model (one block per entity: fields/PK/indexes/relationships/invariants)",
            "3 storage trade-offs (normalization, consistency, schema flexibility)",
            "AI schema critique with adopt/defer/reject log",
        ],
        "sample": (
            '<h4>Access Pattern (sample)</h4><p>Pattern #4 (&#9733; highest-volume read): list open '
            'tickets for a shop, filtered by status and priority, ordered by priority then created-at '
            '&mdash; this single pattern drives the index design engineering needs on the Ticket '
            'table.</p>'
            '<h4>Storage Trade-Off (sample)</h4><p>Strong consistency vs. replica reads: the open-ticket '
            'listing read must hit the primary database, not a replica, because a stale read could let '
            'two dispatchers claim the same ticket &mdash; directly protecting a concurrency invariant, '
            'not just a style preference.</p>'
        ),
    },
    {
        "id": "tmd-cloud-topology", "stage": "Week 5 \u00b7 Day 2", "title": "TMD Section 2 \u2013 Cloud Topology", "week": 5,
        "definition": "Five topology decisions for the feature's real component map -- region + "
                      "multi-AZ, managed-vs-self per component, multi-tenancy stance, network "
                      "boundary, and a rough-order-of-magnitude monthly cost table -- closed with a "
                      "required AI sanity check.",
        "why": "Every topology choice trades cost against risk; defaulting to 'managed unless "
               "there's a specific reason not to' and 'pooled tenancy unless there's contractual "
               "evidence otherwise' stops a team from over-engineering for a problem no customer "
               "has actually asked for.",
        "inside": [
            "Region + multi-AZ stance with a named trade-off",
            "Managed-vs-self table for every component (4-question test)",
            "Multi-tenancy stance (pooled default) + network boundary (public HTTPS default)",
            "ROM cost table with egress called out as its own line",
        ],
        "sample": (
            '<h4>Smell to Reject</h4><p>&ldquo;We want full control&rdquo; is not a valid reason to '
            'self-manage a component -- the test asks whether failure modes match real needs, whether '
            'cost is reasonable at this scale, whether compliance allows it, and whether there is a '
            'SPECIFIC reason to control it.</p>'
            '<h4>Cost Surprise (sample)</h4><p>The highest-availability database tier can consume well '
            'over a third of the entire monthly infrastructure budget &mdash; the direct dollar cost of '
            'an availability SLO, made visible instead of buried in an abstract percentage.</p>'
        ),
    },
    {
        "id": "tmd-rest-api", "stage": "Week 5 \u00b7 Day 3", "title": "TMD Section 3 \u2013 REST API Contract", "week": 5,
        "definition": "Every data-model entity checked as a resource candidate, URL paths and HTTP "
                      "methods designed with correct happy/sad/weird-path status codes, and one "
                      "endpoint documented end-to-end -- including idempotency, versioning, and the "
                      "error-body shape.",
        "why": "An API is a public contract that's hard to change later; the day trains catching "
               "two opposite mistakes at once -- a verb disguised as a resource (e.g. a "
               "'/reconcile' action endpoint) and blindly exposing every entity, including ones "
               "that are really internal plumbing a client should never touch directly.",
        "inside": [
            "Resource list, with exclusions reasoned (not every entity becomes an endpoint)",
            "URL path design (nesting sub-resources one level deep)",
            "Methods + status-code table for happy/sad/weird paths",
            "One endpoint fully documented: idempotency key + window, versioning, error body",
        ],
        "sample": (
            '<h4>Deliberate Exclusion (sample)</h4><p>An internal outbox table used only to relay '
            'events to a background process is deliberately NOT exposed as a REST resource &mdash; '
            'exposing it would let a client bypass the exact audit or billing guarantee it exists to '
            'provide.</p>'
            '<h4>Idempotency (sample)</h4><p>An <code>Idempotency-Key</code> header with a 24-hour '
            'window turns a &ldquo;network dropped mid-submit, client retries&rdquo; scenario into a '
            'safe replay instead of a duplicate side effect.</p>'
        ),
    },
]


def _glossarize_day(day):
    """Return a copy of a COURSE_LIFECYCLE day with glossarized *_html fields for week.html.

    The plain what/why/connects/artifacts fields stay untouched -- they still feed
    index.html's lifecycle_json, which is rendered client-side via escapeHtml() and
    would show literal <span> tags as text if they contained markup.
    """
    glossarized = dict(day)
    glossarized["what_html"] = glossarize(day["what"])
    glossarized["why_html"] = glossarize(day["why"])
    glossarized["connects_html"] = glossarize(day["connects"])
    glossarized["artifacts_html"] = [glossarize(a) for a in day["artifacts"]]
    if day.get("diagram"):
        glossarized["diagram"] = glossarize(day["diagram"])
    word_count = len(
        (day["what"] + " " + day["why"] + " " + day["connects"] + " " + " ".join(day["artifacts"])).split()
    )
    glossarized["reading_time"] = max(1, round(word_count / 200))
    return glossarized


def build_weeks():
    """Attach filtered day lists + prev/next week links onto WEEKS_META."""
    weeks_by_id = {w["id"]: dict(w) for w in WEEKS_META}
    for week in weeks_by_id.values():
        week["days"] = [_glossarize_day(d) for d in COURSE_LIFECYCLE if d["week_id"] == week["id"]]

    ordered = [weeks_by_id[w["id"]] for w in WEEKS_META]
    for i, week in enumerate(ordered):
        prev_w = ordered[i - 1] if i > 0 else None
        next_w = ordered[i + 1] if i < len(ordered) - 1 else None
        week["prev"] = {"id": prev_w["id"], "label": prev_w["label"], "theme": prev_w["theme"]} if prev_w else None
        week["next"] = {"id": next_w["id"], "label": next_w["label"], "theme": next_w["theme"]} if next_w else None
    return ordered


def build_glossarized_milestones():
    """Return a copy of MILESTONES with glossarized *_html fields for index.html."""
    out = []
    for m in MILESTONES:
        gm = dict(m)
        gm["definition_html"] = glossarize(m["definition"])
        gm["why_html"] = glossarize(m["why"])
        gm["inside_html"] = [glossarize(item) for item in m["inside"]]
        if m.get("sample"):
            gm["sample"] = glossarize(m["sample"])
        out.append(gm)
    return out


def main():
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["glossarize"] = glossarize

    weeks_by_id = {w["id"]: w for w in WEEKS_META}
    lifecycle_for_json = []
    for day in COURSE_LIFECYCLE:
        week_meta = weeks_by_id[day["week_id"]]
        lifecycle_for_json.append({
            **day,
            "week_label": week_meta["label"],
            "week_theme": week_meta["theme"],
            "week_number": week_meta["number"],
            "link": f"{day['week_id']}.html#{day['anchor']}",
        })
    lifecycle_json = json.dumps(lifecycle_for_json)
    weeks = build_weeks()
    glossary_json = json.dumps({
        e["id"]: {"term": e["term"], "definition": e["definition"], "category": e["category"]}
        for e in GLOSSARY
    })

    # index.html
    index_tpl = env.get_template("index.html")
    index_html = index_tpl.render(
        page_title="TPM Bootcamp Flow Atlas",
        page_description="A visual and plain-language guide to the TPM Bootcamp lifecycle from Week 1 to Week 5.",
        active_page="home",
        header_compact=False,
        weeks_meta=WEEKS_META,
        lifecycle=COURSE_LIFECYCLE,
        lifecycle_json=lifecycle_json,
        milestones=build_glossarized_milestones(),
        glossary_json=glossary_json,
    )
    (ROOT / "index.html").write_text(index_html, encoding="utf-8")
    print("Wrote index.html")

    # week1.html .. week5.html
    week_tpl = env.get_template("week.html")
    for week in weeks:
        week_html = week_tpl.render(
            page_title=f"{week['label']}: {week['theme']} | TPM Bootcamp Flow Atlas",
            page_description=week["blurb"],
            active_page=week["id"],
            header_compact=True,
            week=week,
            total_weeks=len(WEEKS_META),
            lifecycle_json=None,
            glossary_json=glossary_json,
        )
        out_path = ROOT / f"{week['id']}.html"
        out_path.write_text(week_html, encoding="utf-8")
        print(f"Wrote {out_path.name}")

    # glossary-core.html + glossary-technical.html
    glossary_tpl = env.get_template("glossary.html")
    glossary_pages = [
        {
            "page_id": "glossary-core",
            "audience_label": "Core TPM Glossary",
            "lead": "Plain-English definitions for every product/TPM process term used across "
                    "this site -- written so a non-technical reader can follow the whole course.",
            "category": "core",
            "other_href": "glossary-technical.html",
            "other_label": "Technical Glossary",
        },
        {
            "page_id": "glossary-technical",
            "audience_label": "Technical Glossary",
            "lead": "Plain-English definitions for every architecture/engineering term used "
                    "across this site -- no prior technical background required.",
            "category": "technical",
            "other_href": "glossary-core.html",
            "other_label": "Core TPM Glossary",
        },
    ]
    for page in glossary_pages:
        terms = sorted(
            (e for e in GLOSSARY if e["category"] == page["category"]),
            key=lambda e: e["term"].lower(),
        )
        glossary_html = glossary_tpl.render(
            page_title=f"{page['audience_label']} | TPM Bootcamp Flow Atlas",
            page_description=page["lead"],
            active_page=page["page_id"],
            header_compact=True,
            audience_label=page["audience_label"],
            lead=page["lead"],
            terms=terms,
            other_href=page["other_href"],
            other_label=page["other_label"],
            glossary_json=glossary_json,
            lifecycle_json=None,
        )
        out_path = ROOT / f"{page['page_id']}.html"
        out_path.write_text(glossary_html, encoding="utf-8")
        print(f"Wrote {out_path.name}")


if __name__ == "__main__":
    main()

