# ResumeIQ — Demo Video Script

**Target length:** 3-4 minutes
**Format:** Screen recording of the live app (https://resumeiq-s3xc.onrender.com/) with voiceover, or narrated live if presenting synchronously.

> Note: this is a recording script, not a video file — actually producing a narrated screen recording requires a human (or screen-recording + voice tooling) I don't have access to in this session. Everything below is tested and accurate against the live deployment as of today, so you can record straight from it.

---

## Before recording

1. Open https://resumeiq-s3xc.onrender.com/ in a browser **1-2 minutes before** you start recording, so the free-tier cold start (~30-50s) doesn't happen on camera.
2. Have a resume file ready to upload. `tests/fixtures/strong_resume.docx` in the repo works well — it's designed to show a mix of strong and weak bullets, with and without metrics, so the demo has something interesting to point at in every section.
3. Pick **"Web Developer"** as the target role for that fixture — it shows a partial ATS match (42/100) rather than a trivial 0 or 100, which is more convincing on camera.

---

## Script

**[0:00-0:20] — Hook + problem**
> "Most resumes get filtered by an ATS before a human ever reads them, and most resume-review tools either give vague feedback or use a black-box AI that can't explain its scoring. ResumeIQ is different — it's built entirely on classic, explainable NLP: every score you're about to see traces back to a specific, inspectable rule. No LLM calls, no embeddings."

**[0:20-0:45] — Upload flow**
> "Here's the upload page." *(Show the homepage.)*
> "I'll pick a target role — Web Developer — and upload a resume." *(Select role, drag the file in, click Analyze.)*
> Point out: role picker, drag-and-drop zone, PDF/DOCX support, 5MB limit.

**[0:45-1:15] — Dashboard overview**
> "This is the dashboard — one page, three headline scores at the top: Resume Score, ATS Score, and Impact Score, plus a chart comparing them at a glance." *(Scroll to show the three tiles and the bar chart.)*
> "These tiles are clickable — they jump straight to the detail section." *(Click one to demonstrate.)*

**[1:15-1:50] — Resume Score breakdown**
> "The Resume Score breaks down into six categories straight from the brief — structure, skills, education, projects, contact info, completeness." *(Scroll to the breakdown bars.)*
> "Section detection is header-based — it looks for short lines that match known section keywords, so a bullet that just *mentions* 'skills' mid-sentence doesn't accidentally register as a Skills section."

**[1:50-2:20] — ATS keyword checker + fuzzy matching differentiator**
> "The ATS checker compares the resume against a role-specific keyword bank." *(Scroll to ATS section, point at matched/missing badges.)*
> "This is one of my two differentiators — it's not just exact string matching. See this 'SYNONYM' tag? The resume said 'REST APIs', and the keyword bank has 'REST API' — matched via a synonym map. Elsewhere it catches typos too, like 'dockr' matching 'Docker' through fuzzy string matching. I actually calibrated that fuzzy threshold empirically — a naive threshold would've credited a resume that only mentions Cython with knowing Python, since they score identically similar to a real typo. That's documented as a known limitation, not something I stumbled into."

**[2:20-2:55] — Impact Score differentiator**
> "The second differentiator is the Impact Score." *(Scroll to bullet list.)*
> "Every bullet gets analyzed for three things: is the opening verb strong or weak, does it include a quantified result, and is it written in passive voice — all via spaCy's dependency parser, not a model call." *(Point at a 'strong verb / metric' bullet and a 'weak verb / no metric' one.)*
> "This bullet says 'Responsible for maintaining CI/CD pipelines' — flagged weak, no metric. Compare that to 'Led a team of 4 engineers... increasing conversion by 18%' — strong verb, metric detected."

**[2:55-3:20] — Smart feedback**
> "All three analyses get synthesized into this feedback list — prioritized, specific suggestions, not generic advice." *(Scroll to Smart Feedback section, read one or two aloud.)*

**[3:20-3:45] — Wrap-up**
> "Everything here — the scoring rubric, the ATS matching, the impact analysis — is rule-based and documented, including where it deliberately falls short, like passive-voice detection only catching canonical 'was/were' constructions. The full source, 74 tests, and a project report walking through the architecture and the bugs I caught along the way are all in the repo." *(Show the GitHub repo briefly.)*
> "Thanks for watching."

---

## Optional B-roll / cutaways (if editing)

- The Print/Save-as-PDF button producing a clean report view.
- The mobile-responsive layout (resize the browser or use dev tools device mode).
- A quick look at the test suite passing (`pytest tests/ -v`).
