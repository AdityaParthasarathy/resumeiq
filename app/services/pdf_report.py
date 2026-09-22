"""Server-generated PDF export of a resume's analysis.

Built with reportlab (pure-Python wheels -- no Cairo/Pango/wkhtmltopdf system
libraries to install), laid out directly with Platypus flowables rather than
converting the dashboard's Tailwind HTML, since neither Render's plain Python
buildpack nor an HTML-to-PDF renderer can be relied on to reproduce that CSS.
This is a distinct, print-purposed layout of the same analysis data, not a
screenshot of the page -- the browser's own "Print / Save as PDF" still
covers that if someone wants a literal copy of what's on screen.
"""

from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND = colors.HexColor("#4f46e5")
SKY = colors.HexColor("#0284c7")
EMERALD = colors.HexColor("#059669")
AMBER = colors.HexColor("#b45309")
RED = colors.HexColor("#dc2626")
INK = colors.HexColor("#1e293b")
INK_SOFT = colors.HexColor("#475569")
MUTED = colors.HexColor("#94a3b8")
LINE = colors.HexColor("#e2e8f0")
PAGE_MARGIN = 0.65 * inch

PRIORITY_COLOR = {"critical": RED, "high": AMBER, "medium": SKY, "low": MUTED, "info": EMERALD}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "RIQTitle", parent=base["Title"], textColor=BRAND, fontSize=20, spaceAfter=2, alignment=0
        ),
        "meta": ParagraphStyle("RIQMeta", parent=base["Normal"], textColor=MUTED, fontSize=9, spaceAfter=14),
        "h2": ParagraphStyle(
            "RIQH2", parent=base["Heading2"], textColor=INK, fontSize=12.5, spaceBefore=16, spaceAfter=6
        ),
        "h3": ParagraphStyle(
            "RIQH3", parent=base["Heading3"], textColor=INK_SOFT, fontSize=9.5, spaceBefore=8, spaceAfter=3,
            uppercase=False,
        ),
        "body": ParagraphStyle("RIQBody", parent=base["Normal"], textColor=INK_SOFT, fontSize=9.5, leading=13.5),
        "small": ParagraphStyle("RIQSmall", parent=base["Normal"], textColor=MUTED, fontSize=8, leading=11),
        "cell": ParagraphStyle("RIQCell", parent=base["Normal"], textColor=INK_SOFT, fontSize=9, leading=12.5),
        "score_label": ParagraphStyle("RIQScoreLabel", parent=base["Normal"], textColor=MUTED, fontSize=8.5),
        "score_num": ParagraphStyle("RIQScoreNum", parent=base["Normal"], textColor=INK, fontSize=20, leading=24),
    }


def _score_summary_table(styles, score, ats, impact, benchmarks):
    def cell(label, value, suffix, color, key):
        pct = benchmarks.get(key)
        pct_line = f"~{pct['percentile']}th percentile*" if pct else ""
        return [
            Paragraph(label, styles["score_label"]),
            Paragraph(f'<font color="{color.hexval()}">{value}</font>{suffix}', styles["score_num"]),
            Paragraph(pct_line, styles["small"]),
        ]

    impact_value = impact.get("impact_score")
    row = [
        cell("RESUME SCORE", score["total"], " /100", BRAND, "resume_score"),
        cell(f"ATS SCORE — {ats['role']}", ats["ats_score"], " /100", SKY, "ats_score"),
        cell(
            "IMPACT SCORE",
            impact_value if impact_value is not None else "N/A",
            " /100" if impact_value is not None else "",
            EMERALD,
            "impact_score",
        ),
    ]
    # Transpose: each "cell" is 3 stacked paragraphs -> build a 3-row table.
    table = Table([[r[i] for r in row] for i in range(3)], colWidths=[2.13 * inch] * 3)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.75, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.75, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _breakdown_table(styles, breakdown, max_breakdown):
    rows = [["Category", "Points"]]
    for category, points in breakdown.items():
        rows.append([category.replace("_", " ").title(), f"{points} / {max_breakdown[category]}"])
    table = Table(rows, colWidths=[3.5 * inch, 1.5 * inch], repeatRows=1)
    table.setStyle(_table_style(header=True))
    return table


def _table_style(header=True):
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK_SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if header:
        style += [
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    return TableStyle(style)


def _keyword_paragraph(styles, details):
    parts = []
    for d in details:
        color = EMERALD if d["matched"] else MUTED
        mark = "✓ " if d["matched"] else "✗ "
        parts.append(f'<font color="{color.hexval()}">{mark}{d["keyword"]}</font>')
    return Paragraph(", ".join(parts) if parts else "—", styles["cell"])


def _role_fit_table(styles, role_fit):
    rows = [["Role", "Keywords matched", "ATS fit"]]
    for r in role_fit:
        label = r["role"]
        if r["is_target"]:
            label += "  (your target)"
        elif r["is_best_fit"]:
            label += "  (best fit)"
        rows.append([label, f"{r['total_matched']}/{r['total_keywords']}", f"{r['ats_score']}/100"])
    table = Table(rows, colWidths=[3 * inch, 1.5 * inch, 1 * inch], repeatRows=1)
    table.setStyle(_table_style(header=True))
    return table


def _impact_table(styles, bullets):
    rows = [["Bullet", "Verb", "Metric", "Passive"]]
    for b in bullets:
        rows.append(
            [
                Paragraph(b["text"], styles["cell"]),
                b["verb_strength"],
                "yes" if b["has_metric"] else "no",
                "yes" if b["is_passive"] else "no",
            ]
        )
    table = Table(rows, colWidths=[3.6 * inch, 0.9 * inch, 0.8 * inch, 0.9 * inch], repeatRows=1)
    table.setStyle(_table_style(header=True))
    return table


def _feedback_list(styles, feedback):
    items = []
    for s in feedback:
        color = PRIORITY_COLOR.get(s["priority"], INK_SOFT)
        text = (
            f'<font color="{color.hexval()}"><b>[{s["priority"].upper()}]</b></font> '
            f'<b>{s["category"]}:</b> {s["message"]}'
        )
        items.append(ListItem(Paragraph(text, styles["body"]), spaceAfter=5, bulletColor=color))
    return ListFlowable(items, bulletType="bullet", leftIndent=14)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        PAGE_MARGIN,
        0.45 * inch,
        "Generated by ResumeIQ — rule-based analysis, no LLM involved. Percentiles are a modeled "
        "estimate, not live user data.",
    )
    canvas.drawRightString(LETTER[0] - PAGE_MARGIN, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_report_pdf(resume, score, ats, impact, feedback, role_fit, benchmarks):
    """Render the full analysis to a PDF and return it as bytes."""
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=PAGE_MARGIN,
        bottomMargin=0.85 * inch,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        title=f"ResumeIQ Report — {resume.original_filename}",
    )

    story = [
        Paragraph("ResumeIQ Report", styles["title"]),
        Paragraph(
            f"{resume.original_filename} &middot; Target role: {ats['role']} &middot; "
            f"Generated {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            styles["meta"],
        ),
        _score_summary_table(styles, score, ats, impact, benchmarks),
        Spacer(1, 16),
        Paragraph("Resume Score Breakdown", styles["h2"]),
        _breakdown_table(styles, score["breakdown"], score["max_breakdown"]),
        Paragraph(f"ATS Keyword Check — {ats['role']}", styles["h2"]),
        Paragraph(
            f'{ats["total_matched"]} / {ats["total_keywords"]} role keywords found &mdash; '
            f'ATS Score: {ats["ats_score"]}/100',
            styles["body"],
        ),
        Paragraph("Must-have keywords", styles["h3"]),
        _keyword_paragraph(styles, ats["must_have"]["details"]),
        Paragraph("Nice-to-have keywords", styles["h3"]),
        _keyword_paragraph(styles, ats["nice_to_have"]["details"]),
        Paragraph("Role Fit Across Roles", styles["h2"]),
        Paragraph(
            "The same resume, scored against every role's keyword bank, not just the one above.",
            styles["body"],
        ),
        Spacer(1, 6),
        _role_fit_table(styles, role_fit),
    ]

    story.append(Paragraph("Bullet-by-bullet Impact Analysis", styles["h2"]))
    if impact.get("bullets"):
        story.append(_impact_table(styles, impact["bullets"]))
    else:
        story.append(
            Paragraph(
                "No bulleted lines were detected under Experience/Projects, so impact couldn't be scored.",
                styles["body"],
            )
        )

    story.append(Paragraph("Smart Feedback", styles["h2"]))
    if feedback:
        story.append(_feedback_list(styles, feedback))
    else:
        story.append(Paragraph("No issues flagged.", styles["body"]))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", color=LINE, thickness=0.75))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "Every score above traces back to a named rule in the analyzer — keyword matching, "
            "section detection, and spaCy-based NLP, not a language model. See resumeiq for the full "
            "methodology.",
            styles["small"],
        )
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
