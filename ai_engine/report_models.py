"""
PhoneTrace -- AI Engine Data Models (continued)
==================================================

Query, response, and report dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ai_engine.models import QueryType, SectionType


# ---------------------------------------------------------------------------
# AI Query
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AIQuery:
    """A question posed to an AI provider.

    Attributes:
        text: The natural-language question.
        query_type: Category hint for context tailoring.
    """
    text: str
    query_type: QueryType = QueryType.GENERAL


# ---------------------------------------------------------------------------
# AI Response
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AIResponse:
    """Answer returned by an AI provider.

    Attributes:
        answer: The generated answer text.
        confidence: Confidence level (0.0-1.0, 1.0 = certain).
        provider_name: Which provider generated this response.
        supporting_evidence: List of event summaries supporting the answer.
        error: Error message if the query failed.
    """
    answer: str = ""
    confidence: float = 1.0
    provider_name: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


# ---------------------------------------------------------------------------
# Report Section
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ReportSection:
    """One section of an investigation report.

    Attributes:
        title: Section heading.
        content: HTML-formatted section body.
        section_type: Category enum.
    """
    title: str
    content: str
    section_type: SectionType


# ---------------------------------------------------------------------------
# Investigation Report
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class InvestigationReport:
    """Complete AI-generated investigation report.

    Attributes:
        title: Report title.
        sections: Ordered list of report sections.
        generated_at: Generation timestamp.
        provider_name: AI provider that generated the report.
        case_id: Associated case identifier.
    """
    title: str = "PhoneTrace Investigation Report"
    sections: List[ReportSection] = field(default_factory=list)
    generated_at: Optional[datetime] = None
    provider_name: str = ""
    case_id: str = ""

    def to_html(self) -> str:
        """Render the full report as a self-contained HTML document.

        Returns:
            Complete HTML string with inline CSS styling.
        """
        gen_time = (
            self.generated_at.strftime("%Y-%m-%d %H:%M:%S")
            if self.generated_at else "N/A"
        )

        sections_html = ""
        for i, sec in enumerate(self.sections, 1):
            sections_html += f"""
            <div class="section">
                <h2>{i}. {sec.title}</h2>
                <div class="section-body">
                    {sec.content}
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self.title}</title>
<style>
    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #0b0f17;
        color: #f0f6fc;
        margin: 0;
        padding: 40px;
        line-height: 1.6;
    }}
    .report-container {{
        max-width: 900px;
        margin: 0 auto;
        background-color: #101622;
        border: 1px solid #2a3754;
        border-radius: 12px;
        padding: 48px;
    }}
    h1 {{
        color: #00f0ff;
        font-size: 28px;
        margin-bottom: 8px;
        border-bottom: 2px solid #2a3754;
        padding-bottom: 16px;
    }}
    .report-meta {{
        color: #8b9ba8;
        font-size: 13px;
        margin-bottom: 32px;
    }}
    .report-meta span {{
        color: #bf5af2;
        font-weight: 600;
    }}
    h2 {{
        color: #bf5af2;
        font-size: 20px;
        margin-top: 32px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #2a3754;
    }}
    .section {{
        margin-bottom: 24px;
    }}
    .section-body {{
        padding: 0 8px;
    }}
    .section-body p {{
        margin: 8px 0;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
    }}
    th {{
        background-color: #07090e;
        color: #8b9ba8;
        text-align: left;
        padding: 10px 14px;
        font-size: 11px;
        text-transform: uppercase;
        font-weight: 700;
        border-bottom: 1px solid #2a3754;
    }}
    td {{
        padding: 8px 14px;
        border-bottom: 1px solid #171f30;
        font-size: 13px;
    }}
    tr:hover td {{
        background-color: #171f30;
    }}
    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
    }}
    .badge-danger {{
        background-color: rgba(248, 81, 73, 0.15);
        color: #f85149;
        border: 1px solid rgba(248, 81, 73, 0.3);
    }}
    .badge-warning {{
        background-color: rgba(210, 153, 34, 0.15);
        color: #d29922;
        border: 1px solid rgba(210, 153, 34, 0.3);
    }}
    .badge-success {{
        background-color: rgba(63, 185, 80, 0.15);
        color: #3fb950;
        border: 1px solid rgba(63, 185, 80, 0.3);
    }}
    .badge-info {{
        background-color: rgba(0, 240, 255, 0.1);
        color: #00f0ff;
        border: 1px solid rgba(0, 240, 255, 0.25);
    }}
    .highlight {{
        background-color: rgba(248, 81, 73, 0.1);
        border-left: 3px solid #f85149;
        padding: 12px 16px;
        border-radius: 4px;
        margin: 12px 0;
    }}
    .finding {{
        background-color: rgba(191, 90, 242, 0.08);
        border-left: 3px solid #bf5af2;
        padding: 12px 16px;
        border-radius: 4px;
        margin: 12px 0;
    }}
    ul {{
        padding-left: 20px;
    }}
    li {{
        margin-bottom: 6px;
    }}
    .footer {{
        margin-top: 48px;
        padding-top: 16px;
        border-top: 1px solid #2a3754;
        color: #8b9ba8;
        font-size: 11px;
        text-align: center;
    }}
</style>
</head>
<body>
<div class="report-container">
    <h1>{self.title}</h1>
    <div class="report-meta">
        Generated: <span>{gen_time}</span> &middot;
        Provider: <span>{self.provider_name}</span> &middot;
        Case: <span>{self.case_id or 'N/A'}</span>
    </div>
    {sections_html}
    <div class="footer">
        PhoneTrace &mdash; AI-Assisted Android Digital Forensic Investigation Workstation<br>
        This report was generated automatically. All findings should be verified by a qualified examiner.
    </div>
</div>
</body>
</html>"""
