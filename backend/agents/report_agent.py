"""
Agent 5 — Report Generation Agent.

Generates a PDF using ReportLab. The PDF includes:

    1. Title page
    2. Dataset summary
    3. KPI list
    4. Analysis summary (missing values, dtype table)
    5. Charts (rendered from Plotly figures to PNG via kaleido)

The PDF is saved into `backend/reports/` and a public URL is returned.
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List

import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
)


class ReportAgent:
    def __init__(self, report_folder: str, file_id: str):
        self.report_folder = report_folder
        self.file_id = file_id

    # ------------------------------------------------------------------
    def run(
        self,
        df: pd.DataFrame,
        analysis: Dict[str, Any],
        kpis: Dict[str, Any],
        charts: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        os.makedirs(self.report_folder, exist_ok=True)

        filename = f"autoreport_{self.file_id}.pdf"
        out_path = os.path.join(self.report_folder, filename)

        doc = SimpleDocTemplate(
            out_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title='AutoReport AI — Dataset Report',
            author='AutoReport AI',
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleX', parent=styles['Title'],
            textColor=colors.HexColor('#1e6cf6'),
            spaceAfter=14,
            alignment=1,
        )
        h2 = ParagraphStyle(
            'H2X', parent=styles['Heading2'],
            textColor=colors.HexColor('#1e6cf6'),
            spaceBefore=14, spaceAfter=10,
        )
        normal = styles['BodyText']

        story = []

        # --- Title page -------------------------------------------------
        story.append(Paragraph('AutoReport AI', title_style))
        story.append(Paragraph('Autonomous Dataset Analysis Report', styles['Heading3']))
        story.append(Spacer(1, 0.6 * cm))
        story.append(Paragraph(
            'This report was generated automatically by the AutoReport AI '
            'agentic pipeline. It summarises the uploaded dataset, lists the '
            'top-level KPIs and includes the visualisations produced during '
            'the run.',
            normal,
        ))
        story.append(Spacer(1, 1.0 * cm))

        # --- Dataset summary -------------------------------------------
        story.append(Paragraph('Dataset Summary', h2))
        summary_rows = [
            ['Total Rows', str(analysis.get('rows', '—'))],
            ['Total Columns', str(analysis.get('columns', '—'))],
            ['Numeric Columns', str(len(df.select_dtypes(include='number').columns))],
            ['Categorical Columns', str(len(df.select_dtypes(exclude='number').columns))],
        ]
        story.append(self._simple_table(summary_rows, col_widths=[5 * cm, 10 * cm]))
        story.append(Spacer(1, 0.5 * cm))

        # --- KPIs ------------------------------------------------------
        story.append(Paragraph('Key Performance Indicators', h2))
        if kpis:
            kpi_rows = [['KPI', 'Value']] + [[k, str(v)] for k, v in kpis.items()]
            story.append(self._simple_table(kpi_rows, col_widths=[7 * cm, 8 * cm]))
        else:
            story.append(Paragraph('No KPIs available.', normal))

        # --- Analysis summary ------------------------------------------
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph('Analysis Summary', h2))
        story.append(Paragraph('<b>Missing values per column:</b>', normal))
        missing = analysis.get('missing') or {}
        if missing:
            mv_rows = [['Column', 'Missing']] + [[c, str(n)] for c, n in missing.items()]
            story.append(self._simple_table(mv_rows, col_widths=[7 * cm, 8 * cm]))
        else:
            story.append(Paragraph('No missing values detected.', normal))

        story.append(PageBreak())

        # --- Charts ----------------------------------------------------
        story.append(Paragraph('Visualisations', h2))
        for chart in charts:
            png_path = self._chart_to_png(chart)
            if png_path:
                story.append(Paragraph(chart.get('title', ''), styles['Heading4']))
                try:
                    img = Image(png_path, width=15 * cm, height=8 * cm)
                    story.append(img)
                except Exception:
                    pass
                story.append(Spacer(1, 0.6 * cm))
            else:
                story.append(Paragraph(
                    f"Could not render chart: {chart.get('title', '')}",
                    normal,
                ))

        doc.build(story)

        return {
            'filename': filename,
            'path': out_path,
            'url': f"/reports/{filename}",
        }

    # ------------------------------------------------------------------
    def _simple_table(self, rows, col_widths=None):
        tbl = Table(rows, colWidths=col_widths, hAlign='LEFT')
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e6cf6')),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#f6f8fc')]),
        ]))
        return tbl

    # ------------------------------------------------------------------
    def _chart_to_png(self, chart: Dict[str, Any]) -> str | None:
        """Render a Plotly figure to a temporary PNG file (kaleido)."""
        try:
            # Charts carry serialisable {data, layout} dicts produced by
            # dashboard_agent. Reconstruct a go.Figure from them.
            data = chart.get('data')
            layout = chart.get('layout')
            if not data:
                return None

            # go.Figure() accepts lists of dicts — works across plotly versions.
            fig = go.Figure()
            fig.update(data=data, layout=layout or {})

            tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            tmp.close()
            fig.write_image(tmp.name, format='png', width=1200, height=600, scale=1)
            return tmp.name
        except Exception as e:
            print(f"[ReportAgent] PNG export failed for '{chart.get('title')}': {e}")
            return None  # Graceful skip — chart omitted from PDF but PDF still builds.