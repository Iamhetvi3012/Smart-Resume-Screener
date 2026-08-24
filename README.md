# Smart Resume Screener

An AI-powered resume screening tool that parses resumes (PDF/DOCX/TXT), extracts
structured candidate data, and uses an LLM to score each candidate against a job
description — with detailed, human-readable justification for every score.

Supports both **single-resume screening** and **batch screening** (upload multiple
resumes against one job description and get a ranked shortlist of candidates).

---

## Features

- **Resume parsing** — extracts name, contact info, education, work experience,
  skills, projects, publications, and extracurriculars from PDF/DOCX/TXT files.
- **LLM-based scoring** — rates each candidate 0–10 across five weighted
  categories (skills, experience, education, projects, cultural fit), plus an
  overall weighted score and a hiring recommendation.
- **Batch screening & shortlisting** — upload multiple resumes at once and get
  them ranked best-to-worst against a single job description.
- **Caching** — resumes and screening results are cached by file hash in
  Supabase, so re-screening the same resume against the same job description
  doesn't re-call the LLM.
- **Web dashboard** — a single-page frontend for both single and batch modes,
  showing score breakdowns, matched/missing skills, strengths, and concerns.

---

## Architecture

```
                     ┌─────────────────────────┐
                     │  Frontend (index.html)  │
                     │ Single mode / Batch mode│
                     └────────────┬────────────┘
                                  │ multipart/form-data
                                  ▼
                     ┌─────────────────────────┐
                     │      Flask API (app.py) │
                     │  /api/parse             │
                     │  /api/screen            │
                     │  /api/screen-batch      │
                     └────────────┬────────────┘
                                  │
                 ┌────────────────┼─────────────────┐
                 ▼                                  ▼
     ┌───────────────────────┐          ┌───────────────────────────┐
     │   Cache check         │          │   Parser (parser.py)      │
     │   (cache_manager.py)  │◀───────▶│   Groq + Instructor →     │
     │   keyed by file hash  │  miss    │   structured resume JSON  │
     └───────────┬───────────┘          └───────────┬───────────────┘
                 │ hit                              │
                 │                                  ▼
                 │                     ┌────────────────────────────┐
                 │                     │  Screener (screener.py)    │
                 │                     │  Groq + Instructor →       │
                 │                     │  ResumeScreeningResult     │
                 │                     │  (scores + justification)  │
                 │                     └───────────┬────────────────┘
                 │                                 │
                 └────────────────┬────────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │   Supabase (Postgres)   │
                     │  parsed_resumes         │
                     │  screening_results      │
                     └────────────┬────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  JSON response returned │
                     │  to frontend, rendered  │
                     │  as score cards /       │
                     │  ranked shortlist       │
                     └─────────────────────────┘
```
## Screenshots

### Dashboard
![Dashboard](screenshot/dashboard.png)

### Upload / Batch Screening
![File Upload](screenshot/fileupload.png)

### Ranked Shortlist
![Shortlisted Candidates](screenshot/shortlisted_resume.png)

### Candidate Screening Result
![Screening Result](screenshot/result.png)

---
**Flow, in words:**
1. User uploads one resume (single mode) or several (batch mode) plus a job
   title/description via the frontend.
2. Flask hashes the file and checks Supabase for a cached parse/screening result.
3. On a cache miss, `parser.py` sends the resume text to Groq (via the
   `instructor` library) and gets back structured JSON (skills, experience,
   education, projects, etc.).
4. `screener.py` sends that structured resume plus the job description to Groq
   with a scoring prompt, and gets back a `ResumeScreeningResult` — five
   category scores with reasoning, an overall weighted score, a
   recommendation, and lists of strengths/concerns.
5. Results are cached in Supabase (`parsed_resumes`, `screening_results`
   tables, keyed by file hash) so repeat requests skip the LLM call.
6. In batch mode, this repeats per file, and the API sorts all candidates by
   `overall_score` descending before returning the ranked shortlist.

---

## LLM Prompts

The scoring prompt lives in `backend/screener.py`, inside `ResumeScreener.screen_resume()`.
It is sent to Groq's `openai/gpt-oss-120b` model via the `instructor` library, which
forces the model's output into a strict JSON schema (`ResumeScreeningResult`) — this is
what removes any need for us to manually parse free-text LLM output.

### System prompt

```
You are an expert technical recruiter and resume screener with deep knowledge across multiple industries.
Your job is to evaluate how well a candidate's resume matches a job opening.
Be critical in your evaluation and fair in your rating. Don't hesitate to lower scores if the candidate does not meet expectations.
In fact lower scores are more common than high scores.

EVALUATION GUIDELINES:
1. Be objective and fair in your assessment
2. Consider both technical skills and soft skills but prioritize technical fit
3. Look for relevant experience, not just years
4. Value projects and certifications that demonstrate practical skills. Value projects which are unique and show commitment to learning and coding rather than generic slop taken from github.
5. Consider transferable skills from different domains
6. Be realistic about skill gaps - focus on critical vs. nice-to-have
7. Use the full 0-10 scale (don't cluster around 7-8). This is a matter of choosing a candidate so each field of rating must reflect the candidate's skills in their entirety
8. Provide actionable, specific feedback
9. Even if a candidate seems strong in some fields if they do not have the required skills or the experience for the job then overall rating should be low.

SCORING SCALE:
9-10: Exceptional match, rare to find better
7-8: Strong match, highly qualified
5-6: Good match, qualified with some gaps
3-4: Potential match, significant gaps but trainable
0-2: Poor match, major misalignment
```

### User prompt (templated per request)

```
Evaluate this candidate's resume for the following position:

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{resume_summary}

SCORING WEIGHTS:
- Skills: {skills_weight}%
- Experience: {experience_weight}%
- Education: {education_weight}%
- Projects: {projects_weight}%
- Cultural Fit: {cultural_fit_weight}%

Provide a comprehensive evaluation with scores for each category and an overall assessment.
Calculate the overall score using the weighted average of individual category scores.
Be specific in your reasoning and provide actionable insights.
```

Default weights: `skills: 30%`, `experience: 25%`, `education: 15%`,
`projects: 15%`, `cultural_fit: 5%` — all overridable per-request via an
optional `weights` JSON field, matching the "rate fit on 1–10 with
justification" pattern the project spec asked for, but broken down into five
independently-justified sub-scores rather than a single number.

### Output schema (enforced via `instructor` + Pydantic)

Each category (`skill_match`, `experience_match`, `education_match`,
`project_match`, `cultural_fit`) returns a `score` (0–10) plus a `reasoning`
string explaining *why*. The top-level result also includes:
- `overall_score` — weighted average, explicitly instructed to drop sharply
  if the candidate fails badly in any one category
- `recommendation` — one of `Strong Match / Good Match / Potential Match /
  Weak Match / Not a Match`
- `summary` — 2–3 sentence executive summary
- `strengths` / `concerns` — top 3–5 each

This structured schema is what the frontend renders as score bars, skill tags,
and strength/concern lists.

---

## API Endpoints

| Method | Endpoint             | Description                                                        |
|--------|-----------------------|----------------------------------------------------------------------|
| POST   | `/api/parse`          | Parse a single resume file, return structured JSON (cached by hash) |
| POST   | `/api/screen`         | Parse + screen a single resume against one job description          |
| POST   | `/api/screen-batch`   | Parse + screen multiple resumes against one job description, returns a ranked shortlist |
| GET    | `/api/health`         | Health check                                                        |

`/api/screen-batch` accepts multiple files under the `files` field, plus
`job_title` and `job_description` form fields, and an optional `weights` JSON
string. It returns:
```json
{
  "success": true,
  "total_candidates": 3,
  "shortlist": [
    { "filename": "...", "candidate_name": "...", "overall_score": 8.2, "data": { "parsed": {...}, "screened": {...} } },
    { "filename": "...", "candidate_name": "...", "overall_score": 6.5, "data": {...} }
  ],
  "errors": []
}
```
sorted by `overall_score` descending.

---

## Tech Stack

- **Backend**: Python, Flask, Flask-CORS
- **LLM**: Groq (`openai/gpt-oss-120b`) via the `instructor` library for
  structured/schema-enforced outputs
- **Database**: Supabase (Postgres) for caching parsed resumes and screening
  results
- **Parsing**: PyPDF2, python-docx
- **Frontend**: Vanilla HTML/CSS/JS (no framework), single `index.html`

---

## Setup

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment variables
Create `backend/.env`:
```
GROQ_API_KEY=your_groq_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### 3. Set up the database
Run the SQL in `backend/supabase_setup.sql` in your Supabase project's SQL Editor
(creates `parsed_resumes` and `screening_results` tables with caching indexes
and auto-updating timestamps).

### 4. Run the backend
```bash
python app.py
```
Server starts at `http://127.0.0.1:5000`.

### 5. Open the frontend
Open `frontend/index.html` directly in a browser. It talks to the backend at
`http://localhost:5000` by default (edit the `API_BASE` constant near the top
of the `<script>` block in `index.html` if your backend runs elsewhere).

---

## Supported File Types

PDF, DOCX, DOC, and TXT resumes are supported for both single and batch
screening.

---

## Known Limitations

- Supabase tables are currently used primarily as a **cache** (keyed by file
  hash) rather than a browsable candidate database — there is no endpoint yet
  to list all previously-screened candidates independent of a specific job
  description.
- No authentication — intended for local/demo use.
- Development Flask server only (`app.run(debug=True)`); not configured for
  production deployment.