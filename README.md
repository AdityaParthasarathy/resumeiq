# ResumeIQ

AI-powered resume analyzer built as an AI/NLP capstone project. Upload a PDF or DOCX resume and get a completeness score, an ATS keyword gap report against a target role, and bullet-by-bullet impact feedback — all from classic, explainable NLP (regex, spaCy POS/dependency parsing, rule-based lexicons, fuzzy string matching), no LLM calls or deep learning models.

**Live app:** https://resumeiq-s3xc.onrender.com/ (free tier — first request after idling takes ~30-50s to wake up, and uploaded resumes don't persist across restarts/redeploys since there's no persistent disk on the free plan)

**Repo:** https://github.com/AdityaParthasarathy/resumeiq

## Core features

1. **Resume Upload & Parsing** — accepts PDF/DOCX, extracts text via `pdfplumber`/`python-docx`, stores it.
2. **Resume Score Analyzer** — scores /100 across structure, skills, education, projects, contact info, and completeness, via section detection (header-line regex matching) and rule-based scoring tiers.
3. **ATS Keyword Checker** — compares resume text against a per-role keyword bank and flags gaps, split into must-have/nice-to-have tiers. Covers 8 roles: the 4 named in the original brief (Data Analyst, Web Developer, AI Engineer, Cloud Engineer) plus 4 added afterward as a purely additive expansion (Mobile App Developer, UI/UX Designer, Backend Developer, DevOps Engineer) — same rule-based matching, just more keyword banks.
4. **Smart Feedback System** — turns the score/ATS/impact analysis into prioritized, human-readable suggestions via rule-based templates (no model call).
5. **Dashboard & Report Generation** — a single page with score tiles, a Chart.js comparison chart, per-category breakdowns, keyword badges, bullet-level flags, and a Print/Save-as-PDF report view.

## Differentiators

**A. Impact Score** — scans each resume bullet for:
- strong vs. weak action verbs (curated lexicon + spaCy lemmatization, with a suffix-normalization fallback for cases where spaCy mis-tags a headless bullet fragment)
- quantified results (regex for %, $, multipliers, and numbers next to metric words like "users"/"engineers")
- passive voice (spaCy dependency parse, checking for `nsubjpass`/`auxpass`/`csubjpass` labels)

Aggregated into a per-bullet flag and a weighted /100 impact score.

**B. Fuzzy/synonym-aware ATS matching** — instead of naive exact-string matching, each keyword is checked via exact match → synonym map (`JS` → `JavaScript`, `ML` → `Machine Learning`, etc.) → `rapidfuzz`-based fuzzy match for typos (`dockr` → `Docker`), with the match type shown in the UI. The fuzzy threshold was calibrated empirically, not guessed — see [Known limitations](#known-limitations).

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Flask (app factory pattern) |
| NLP | spaCy (`en_core_web_sm`) + regex + rule-based lexicons |
| Fuzzy matching | rapidfuzz |
| Database | SQLite via Flask-SQLAlchemy |
| Frontend | Jinja2 templates + Tailwind (CDN) + Chart.js |
| Testing | pytest (74 tests) |
| Deployment | Render (gunicorn) |

## Project structure

```
resumeiq/
├── app/
│   ├── __init__.py            # app factory, error handlers
│   ├── config.py               # Dev/Prod/Testing config
│   ├── models.py                # Resume, Analysis (SQLite tables)
│   ├── routes/
│   │   ├── main.py             # GET /, GET /health
│   │   └── upload.py           # POST /upload, GET /resume/<id>
│   ├── services/                # framework-free NLP/scoring logic
│   │   ├── parser.py           # PDF/DOCX -> text
│   │   ├── section_detector.py # section + contact-info detection
│   │   ├── scorer.py           # resume score /100
│   │   ├── ats_matcher.py      # ATS keyword gap analysis
│   │   ├── fuzzy_match.py      # synonym map + rapidfuzz matching
│   │   ├── impact_score.py     # bullet verb/metric/passive analysis
│   │   └── feedback.py         # rule-based suggestion generation
│   ├── templates/
│   └── static/
├── data/
│   ├── keyword_banks.json      # per-role ATS keywords
│   └── synonym_map.json        # abbreviation/alias -> canonical keyword
├── tests/                       # 74 tests, incl. real fixture PDFs/DOCX
├── scripts/generate_test_fixtures.py
├── requirements.txt
├── render.yaml / Procfile
└── run.py / wsgi.py
```

## Running locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python run.py
```

App runs at `http://127.0.0.1:5000`.

### Tests

```bash
python -m pytest tests/ -v
```

## Design notes / defensibility

- **Why not embeddings/an LLM for keyword matching?** Scope constraint: this project stays rule-based/classic-NLP (regex, spaCy, simple statistics) so every scoring decision is traceable to an explicit rule, not a black box. The fuzzy-matching differentiator uses `rapidfuzz` (Levenshtein-based string similarity) plus a hand-built synonym map — no vector search, no model inference.
- **Why does "structure" scoring fold in "experience" instead of scoring it separately?** The brief's six named scoring categories are structure, skills, education, projects, contact info, and completeness — "experience" isn't one of them, so its presence feeds into the structure/completeness signals rather than getting its own top-level score.
- **Section detection is header-based, not ML-based.** A line is treated as a section header only if it's short and matches a known keyword (e.g. "Skills", "Education") — this deliberately avoids misfiring on a bullet that merely *mentions* "skills" mid-sentence.

## Known limitations

These are documented tradeoffs, not oversights:

- **Passive-voice detection** only catches canonical "was/were + past participle" constructions (via spaCy's `auxpass`/`nsubjpass` dependency labels). Reduced passives with no auxiliary ("Errors reduced by 30%") aren't caught, since there's no auxiliary token for the parser to anchor the label on.
- **Fuzzy-match threshold (90) is deliberately conservative.** Empirically, `rapidfuzz.fuzz.ratio("python", "cython")` and `ratio("python", "pyhton")` score identically (83.3) — a looser threshold would credit a resume that only mentions Cython with knowing Python. Fuzzy matching is also skipped for keywords under 5 characters and multi-word phrases, where it gets too noisy to be reliable.
- **Bullet extraction is marker-based** (`-`, `*`, `•`, numbered lists). A resume with no bullet markers at all won't have any bullets analyzed for impact score — the dashboard flags this explicitly rather than silently scoring 0.
- **No persistent storage on the free Render tier.** SQLite lives on the container's ephemeral filesystem; uploaded resumes reset on redeploy or free-tier spin-down/spin-up.

## Deployment

Deployed on Render via `render.yaml` (Blueprint). Build step installs dependencies and downloads the spaCy model; `gunicorn` serves the app. See `render.yaml` for the exact config. No persistent disk is attached (not supported on the free tier — see limitations above).

## Attribution

Built with [Claude Code](https://claude.com/claude-code).
