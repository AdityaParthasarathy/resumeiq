# Screenshots

Real captures of the landing page, taken directly from a running instance
(not mockups). Captured via a headless html2canvas injection since there's
no OS-level screenshot tool wired into this workflow -- see
`scripts/extract_screenshot.py` for the extraction half of that pipeline if
these ever need to be regenerated.

- `01-hero.png` — hero section, desktop
- `02-how-it-works-section.png` — the scroll-story section with the "impact" layer active (weak/strong verb tags visible on the mock resume)
- `03-why-rule-based.png` — the four trust/differentiation cards
- `04-roles.png` — the 8 supported target roles
- `05-analyze-form.png` — the functional upload form
- `06-hero-mobile.png` — hero section at 375px, showing the responsive stacked layout

For dashboard screenshots (score breakdown, ATS keyword badges, impact analysis, feedback list), upload `tests/fixtures/strong_resume.docx` with target role "Web Developer" at the live URL — that fixture is designed to show a mix of strong/weak bullets and partial ATS matches.
