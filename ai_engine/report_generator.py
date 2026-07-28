"""
PhoneTrace -- AI Report Generator
====================================

Produces a structured ``InvestigationReport`` with HTML-formatted
sections covering every forensic dimension of the investigation.

The generator uses the active AI provider for narrative and alibi
sections, and deterministic logic for statistical sections.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime
from typing import List

from ai_engine.models import InvestigationContext, SectionType
from ai_engine.providers.base import AIProvider
from ai_engine.report_models import (
    InvestigationReport,
    ReportSection,
)

logger = logging.getLogger("ai_engine.ReportGenerator")


class ReportGenerator:
    """Generates comprehensive investigation reports.

    Args:
        provider: The AI provider to use for narrative sections.

    Usage::

        generator = ReportGenerator(provider)
        report = generator.generate(context)
        html_output = report.to_html()
    """

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    def generate(self, context: InvestigationContext) -> InvestigationReport:
        """Generate a complete investigation report.

        Args:
            context: The investigation context.

        Returns:
            InvestigationReport with all sections populated.
        """
        logger.info("Generating investigation report...")

        sections: List[ReportSection] = [
            self._section_case_overview(context),
            self._section_timeline_summary(context),
            self._section_incident_analysis(context),
            self._section_alibi_verification(context),
            self._section_communication_analysis(context),
            self._section_movement_analysis(context),
            self._section_correlation_findings(context),
            self._section_anomaly_report(context),
            self._section_ai_narrative(context),
            self._section_conclusions(context),
        ]

        report = InvestigationReport(
            title=f"PhoneTrace Investigation Report — {context.suspect_name}",
            sections=sections,
            generated_at=datetime.now(),
            provider_name=self._provider.name,
            case_id=f"{context.suspect_name}_{context.investigation_period[0][:10]}",
        )

        logger.info("Report generated: %d sections.", len(sections))
        return report

    # ------------------------------------------------------------------
    # Section generators
    # ------------------------------------------------------------------

    @staticmethod
    def _section_case_overview(ctx: InvestigationContext) -> ReportSection:
        content = f"""
        <p>{html.escape(ctx.case_summary)}</p>
        <table>
            <tr><th>Field</th><th>Value</th></tr>
            <tr><td>Suspect</td><td>{html.escape(ctx.suspect_name)}</td></tr>
            <tr><td>Phone Number</td><td>{html.escape(ctx.suspect_phone)}</td></tr>
            <tr><td>Device</td><td>{html.escape(ctx.device_info)}</td></tr>
            <tr>
                <td>Investigation Period</td>
                <td>{ctx.investigation_period[0][:10]} to {ctx.investigation_period[1][:10]}</td>
            </tr>
            <tr>
                <td>Incident Window</td>
                <td>{ctx.incident_window[0][11:16]} to {ctx.incident_window[1][11:16]}
                    on {ctx.incident_window[0][:10]}</td>
            </tr>
            <tr>
                <td>Claimed Location (Alibi)</td>
                <td>{html.escape(ctx.alibi_location)}
                    ({ctx.alibi_coords[0]:.4f}, {ctx.alibi_coords[1]:.4f})</td>
            </tr>
            <tr>
                <td>Incident Location</td>
                <td>{html.escape(ctx.incident_location)}
                    ({ctx.incident_coords[0]:.4f}, {ctx.incident_coords[1]:.4f})</td>
            </tr>
        </table>
        """
        return ReportSection(
            title="Case Overview",
            content=content,
            section_type=SectionType.CASE_OVERVIEW,
        )

    @staticmethod
    def _section_timeline_summary(ctx: InvestigationContext) -> ReportSection:
        s = ctx.statistics
        artifact_rows = "".join(
            f"<tr><td>{html.escape(atype)}</td><td>{count}</td></tr>"
            for atype, count in ctx.artifact_counts.items()
        )

        content = f"""
        <p>The forensic timeline contains <strong>{s.total_events}</strong> events
        spanning the investigation period.</p>

        <table>
            <tr><th>Artifact Type</th><th>Count</th></tr>
            {artifact_rows}
        </table>

        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Busiest Hour</td><td>{s.busiest_hour:02d}:00 ({s.busiest_hour_count} events)</td></tr>
            <tr><td>Busiest Day</td><td>{s.busiest_day} ({s.busiest_day_count} events)</td></tr>
            <tr><td>Activity Sessions</td><td>{s.session_count}</td></tr>
            <tr><td>Correlation Groups</td><td>{s.correlation_count}</td></tr>
            <tr><td>Incident Window Events</td><td>{s.incident_event_count}</td></tr>
        </table>
        """
        return ReportSection(
            title="Timeline Summary",
            content=content,
            section_type=SectionType.TIMELINE_SUMMARY,
        )

    @staticmethod
    def _section_incident_analysis(ctx: InvestigationContext) -> ReportSection:
        if not ctx.incident_events:
            content = "<p>No events recorded during the incident window.</p>"
        else:
            rows = "".join(
                f"<tr><td>{ev.timestamp[11:19]}</td>"
                f"<td><span class='badge badge-info'>{ev.artifact_type}</span></td>"
                f"<td>{html.escape(ev.title)}</td>"
                f"<td>{html.escape(ev.location_label or '—')}</td></tr>"
                for ev in ctx.incident_events
            )
            content = f"""
            <p><strong>{len(ctx.incident_events)}</strong> events occurred during
            the incident window ({ctx.incident_window[0][11:16]} to
            {ctx.incident_window[1][11:16]}).</p>

            <table>
                <tr><th>Time</th><th>Type</th><th>Event</th><th>Location</th></tr>
                {rows}
            </table>
            """
        return ReportSection(
            title="Incident Window Analysis",
            content=content,
            section_type=SectionType.INCIDENT_ANALYSIS,
        )

    def _section_alibi_verification(
        self,
        ctx: InvestigationContext,
    ) -> ReportSection:
        try:
            response = self._provider.check_alibi(
                ctx, ctx.alibi_location, ctx.alibi_coords,
            )
            answer = response.answer
            confidence = response.confidence

            # Determine verdict badge
            if "CONTRADICTED" in answer.upper():
                badge = '<span class="badge badge-danger">CONTRADICTED</span>'
            elif "CONSISTENT" in answer.upper():
                badge = '<span class="badge badge-success">CONSISTENT</span>'
            else:
                badge = '<span class="badge badge-warning">INSUFFICIENT DATA</span>'

            evidence_html = ""
            if response.supporting_evidence:
                items = "".join(
                    f"<li>{html.escape(e)}</li>"
                    for e in response.supporting_evidence
                )
                evidence_html = f"<ul>{items}</ul>"

            content = f"""
            <p><strong>Claimed Alibi Statement to Police:</strong></p>
            <p style="color: #8b9ba8; font-style: italic; padding-left: 12px; border-left: 3px solid #bf5af2; margin-bottom: 20px;">
                Suspect {html.escape(ctx.suspect_name)} claimed to the police that he was at his residence 
                ({html.escape(ctx.alibi_location)}) during the incident window on {ctx.incident_window[0][:10]} 
                from {ctx.incident_window[0][11:16]} to {ctx.incident_window[1][11:16]} IST, and was resting/sleeping.
            </p>

            <p>Verdict Assessment: {badge} &nbsp;&nbsp;&nbsp;&nbsp; (Confidence: {confidence:.0%})</p>

            <div class="highlight">
                <p>{html.escape(answer)}</p>
            </div>

            <p><strong>Supporting GPS Evidence:</strong></p>
            {evidence_html}
            """
        except Exception as exc:
            content = f"<p>Alibi verification failed: {html.escape(str(exc))}</p>"

        return ReportSection(
            title="Alibi Verification",
            content=content,
            section_type=SectionType.ALIBI_VERIFICATION,
        )

    @staticmethod
    def _section_communication_analysis(
        ctx: InvestigationContext,
    ) -> ReportSection:
        c = ctx.communication
        contact_rows = "".join(
            f"<tr><td>{html.escape(name)}</td><td>{count}</td></tr>"
            for name, count in c.top_contacts[:10]
        )

        incident_contacts = (
            ", ".join(html.escape(ic) for ic in c.incident_contacts)
            if c.incident_contacts else "None detected"
        )

        content = f"""
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Calls</td><td>{c.total_calls}</td></tr>
            <tr><td>Total SMS</td><td>{c.total_sms}</td></tr>
            <tr><td>Unknown Contacts</td>
                <td>{c.unknown_contact_count}
                {'<span class="badge badge-warning">Flagged</span>' if c.unknown_contact_count > 0 else ''}
                </td></tr>
        </table>

        <p><strong>Top Contacts:</strong></p>
        <table>
            <tr><th>Contact</th><th>Interactions</th></tr>
            {contact_rows}
        </table>

        <p><strong>Incident Window Contacts:</strong> {incident_contacts}</p>
        """
        return ReportSection(
            title="Communication Analysis",
            content=content,
            section_type=SectionType.COMMUNICATION_ANALYSIS,
        )

    @staticmethod
    def _section_movement_analysis(ctx: InvestigationContext) -> ReportSection:
        if not ctx.movements:
            content = "<p>No significant GPS movements detected.</p>"
        else:
            rows = "".join(
                f"<tr><td>{m.timestamp[11:19]}</td>"
                f"<td>{html.escape(m.from_label)}</td>"
                f"<td>{html.escape(m.to_label)}</td>"
                f"<td>{m.distance_km:.1f} km</td></tr>"
                for m in ctx.movements[:30]
            )

            # Check incident-window movements
            incident_mvmt = [
                m for m in ctx.movements
                if ctx.incident_window[0] <= m.timestamp <= ctx.incident_window[1]
            ]
            incident_note = ""
            if incident_mvmt:
                incident_note = f"""
                <div class="highlight">
                    <p><strong>{len(incident_mvmt)} movement(s)</strong> detected
                    during the incident window — this is critical evidence.</p>
                </div>
                """

            content = f"""
            <p><strong>{len(ctx.movements)}</strong> significant GPS displacements
            detected (threshold: 0.5 km).</p>

            {incident_note}

            <table>
                <tr><th>Time</th><th>From</th><th>To</th><th>Distance</th></tr>
                {rows}
            </table>
            """
        return ReportSection(
            title="Movement Analysis",
            content=content,
            section_type=SectionType.MOVEMENT_ANALYSIS,
        )

    @staticmethod
    def _section_correlation_findings(
        ctx: InvestigationContext,
    ) -> ReportSection:
        if not ctx.correlations:
            content = "<p>No evidence correlations detected.</p>"
        else:
            rows = "".join(
                f"<tr><td>{html.escape(cg.rule_name)}</td>"
                f"<td>{html.escape(cg.anchor_title)}</td>"
                f"<td>{cg.anchor_time[11:19]}</td>"
                f"<td>{cg.correlated_count}</td>"
                f"<td>{cg.confidence:.0%}</td></tr>"
                for cg in ctx.correlations[:30]
            )
            content = f"""
            <p><strong>{len(ctx.correlations)}</strong> cross-artifact correlation
            groups detected.</p>

            <table>
                <tr><th>Rule</th><th>Anchor Event</th><th>Time</th>
                    <th>Related Events</th><th>Confidence</th></tr>
                {rows}
            </table>
            """
        return ReportSection(
            title="Correlation Findings",
            content=content,
            section_type=SectionType.CORRELATION_FINDINGS,
        )

    def _section_anomaly_report(
        self,
        ctx: InvestigationContext,
    ) -> ReportSection:
        try:
            response = self._provider.detect_anomalies(ctx)
            answer = response.answer

            if response.is_error:
                content = f"<p>Anomaly detection failed: {html.escape(response.error or '')}</p>"
            else:
                # Format anomalies as list items
                lines = answer.split("\n")
                items = ""
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("Detected"):
                        # Remove leading numbers/bullets
                        clean = stripped.lstrip("0123456789.) •-")
                        if clean:
                            items += f"<li>{html.escape(clean)}</li>"

                if items:
                    content = f"""
                    <div class="finding">
                        <p><strong>Anomalies Detected</strong></p>
                    </div>
                    <ul>{items}</ul>
                    """
                else:
                    content = f"<p>{html.escape(answer)}</p>"

        except Exception as exc:
            content = f"<p>Anomaly detection error: {html.escape(str(exc))}</p>"

        return ReportSection(
            title="Anomaly Report",
            content=content,
            section_type=SectionType.ANOMALY_REPORT,
        )

    def _section_ai_narrative(self, ctx: InvestigationContext) -> ReportSection:
        try:
            narrative = self._provider.generate_narrative(ctx)
            # Convert plain text to HTML paragraphs
            paragraphs = narrative.split("\n\n")
            html_paragraphs = "".join(
                f"<p>{html.escape(p.strip())}</p>"
                for p in paragraphs
                if p.strip()
            )
            content = f"""
            <div class="finding">
                <p><strong>AI-Generated Narrative</strong>
                (Provider: {html.escape(self._provider.name)})</p>
            </div>
            {html_paragraphs}
            """
        except Exception as exc:
            content = f"<p>Narrative generation failed: {html.escape(str(exc))}</p>"

        return ReportSection(
            title="AI Investigation Narrative",
            content=content,
            section_type=SectionType.AI_NARRATIVE,
        )

    @staticmethod
    def _section_conclusions(ctx: InvestigationContext) -> ReportSection:
        findings: List[str] = []

        # Auto-generate conclusions from context
        s = ctx.statistics
        c = ctx.communication

        findings.append(
            f"The investigation analysed {s.total_events} forensic events "
            f"across {s.session_count} activity sessions."
        )

        if s.incident_event_count > 0:
            findings.append(
                f"{s.incident_event_count} events occurred during the "
                f"incident window, requiring detailed review."
            )

        if c.unknown_contact_count > 0:
            findings.append(
                f"{c.unknown_contact_count} communications involved "
                f"unknown contacts — potential burner phone activity."
            )

        if c.incident_contacts:
            findings.append(
                f"Communication was active during the incident window "
                f"with: {', '.join(c.incident_contacts)}."
            )

        items = "".join(f"<li>{html.escape(f)}</li>" for f in findings)

        content = f"""
        <div class="finding">
            <p><strong>Key Findings</strong></p>
        </div>
        <ul>{items}</ul>

        <div class="highlight">
            <p><strong>Note:</strong> This report was generated automatically
            by PhoneTrace. All findings and conclusions should be verified
            by a qualified forensic examiner before being presented as
            evidence in any legal proceeding.</p>
        </div>
        """
        return ReportSection(
            title="Conclusions & Recommendations",
            content=content,
            section_type=SectionType.CONCLUSIONS,
        )
