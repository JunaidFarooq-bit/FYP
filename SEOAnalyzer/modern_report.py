"""
WEB LIFT - Modern PDF Report Generator
Generates elegant, professional SEO audit reports with consistent branding
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from datetime import date
import os
import smtplib
import subprocess
from html import escape
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import logging
from django.conf import settings
from django.template.loader import render_to_string

# Setup logging
logger = logging.getLogger(__name__)


class ModernPDFReport:
    """
    Modern PDF Report Generator for WEB LIFT SEO Audit
    
    Brand Colors:
    - Primary Dark: #07164c
    - Primary Mid: #3157ff
    - Accent Cyan: #16c7d8
    """
    
    # Brand Colors (RGB format for ReportLab)
    PRIMARY_DARK = colors.HexColor('#07164c')
    PRIMARY_MID = colors.HexColor('#3157ff')
    PRIMARY_LIGHT = colors.HexColor('#d7e0ff')
    ACCENT = colors.HexColor('#16c7d8')
    ACCENT_GREEN = colors.HexColor('#26c281')
    SOFT_BLUE = colors.HexColor('#eef4ff')
    CARD_BORDER = colors.HexColor('#dfe7f4')
    SUCCESS = colors.HexColor('#10b981')
    WARNING = colors.HexColor('#f59e0b')
    ERROR = colors.HexColor('#ef4444')
    GRAY_50 = colors.HexColor('#f5f7fb')
    GRAY_100 = colors.HexColor('#edf2f7')
    GRAY_500 = colors.HexColor('#718096')
    GRAY_700 = colors.HexColor('#374151')
    GRAY_900 = colors.HexColor('#111827')
    
    def __init__(self, data_dict, user_email, output_dir=None):
        """
        Initialize the PDF report generator
        
        Args:
            data_dict: Dictionary containing all SEO audit data
            user_email: Email address to send the report to
            output_dir: Optional output directory for PDF (default: current directory)
        """
        self.data = data_dict
        self.user_email = user_email
        self.output_dir = output_dir or os.getcwd()
        
        # Generate filename with timestamp
        timestamp = date.today().strftime('%Y%m%d')
        self.filename = f"WEB_LIFT_Report_{timestamp}.pdf"
        self.filepath = os.path.join(self.output_dir, self.filename)
        
        self.styles = self._create_custom_styles()
        self.story = []
        
    def _create_custom_styles(self):
        """Create custom paragraph styles matching the brand"""
        styles = getSampleStyleSheet()
        
        # Main Title Style
        styles.add(ParagraphStyle(
            name='MainTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=28,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=12
        ))
        
        # Section Title Style
        styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=18,
            textColor=self.PRIMARY_DARK,
            spaceBefore=20,
            spaceAfter=12,
            borderPadding=10,
            backColor=self.SOFT_BLUE
        ))
        
        # Subsection Title
        styles.add(ParagraphStyle(
            name='SubsectionTitle',
            parent=styles['Heading3'],
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=self.PRIMARY_MID,
            spaceBefore=12,
            spaceAfter=8
        ))
        
        # Body Text
        styles.add(ParagraphStyle(
            name='MyBodyText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=self.GRAY_700,
            alignment=TA_JUSTIFY,
            spaceAfter=8
        ))

        styles.add(ParagraphStyle(
            name='SmallMuted',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            textColor=self.GRAY_500,
            leading=11
        ))

        styles.add(ParagraphStyle(
            name='CardTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=self.PRIMARY_DARK,
            leading=12
        ))

        styles.add(ParagraphStyle(
            name='CardValue',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=self.PRIMARY_DARK,
            leading=23
        ))
        
        # Success Badge
        styles.add(ParagraphStyle(
            name='SuccessBadge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.white,
            backColor=self.SUCCESS,
            borderPadding=5
        ))
        
        # Warning Badge
        styles.add(ParagraphStyle(
            name='WarningBadge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.white,
            backColor=self.ERROR,
            borderPadding=5
        ))
        
        return styles
    
    def _header_footer(self, canvas, doc):
        """Add header and footer to each page"""
        canvas.saveState()
        
        # Header
        canvas.setFillColor(self.PRIMARY_DARK)
        canvas.rect(0, letter[1] - 50, letter[0], 50, fill=True, stroke=False)
        
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 16)
        canvas.drawString(50, letter[1] - 30, "WEB LIFT")
        
        canvas.setFont('Helvetica', 10)
        canvas.drawRightString(letter[0] - 50, letter[1] - 30, f"Report Date: {date.today().strftime('%B %d, %Y')}")
        
        # Footer
        canvas.setFillColor(self.GRAY_700)
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(letter[0]/2, 30, f"Page {doc.page}")
        canvas.drawString(50, 30, "© WEB LIFT - Professional SEO Audit")
        
        canvas.restoreState()
    
    def _safe_number(self, value, default=0):
        """Return a numeric value from mixed report data."""
        try:
            if value in (None, '', 'N/A'):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _score_color(self, score):
        """Return a theme color for a 0-100 score."""
        score = self._safe_number(score)
        if score >= 70:
            return self.SUCCESS
        if score >= 50:
            return self.WARNING
        return self.ERROR

    def _collect_dashboard_metrics(self):
        """Collect the headline metrics used by the PDF dashboard."""
        seo = self.data.get('seo', {})
        metrics = self.data.get('metrics', {})
        keyword_ai = self.data.get('keyword_ai', {})
        content_stats = keyword_ai.get('content_stats', {})

        title_score = self._safe_number(seo.get('title_score') or self.data.get('title_score'))
        desc_score = self._safe_number(seo.get('description_score') or self.data.get('desc_score'))
        heading_score = self._safe_number(seo.get('heading_score') or self.data.get('heading_score'))
        social_score = self._safe_number(seo.get('social_score') or self.data.get('s_count'))
        mobile_score = self._safe_number(seo.get('mobile_score') or self.data.get('mob_score'))
        quality_score = self._safe_number(content_stats.get('quality_score'))
        da = metrics.get('domain_authority')

        scores = [
            ('Title', title_score),
            ('Description', desc_score),
            ('Headings', heading_score),
            ('Social', social_score),
        ]

        if quality_score:
            scores.append(('AI Content', quality_score))
        if mobile_score:
            scores.append(('Mobile', min(100, max(0, mobile_score))))

        overall = round(sum(score for _, score in scores) / len(scores)) if scores else 0

        return {
            'overall': overall,
            'scores': scores,
            'domain_authority': da,
            'speed': self._safe_number(seo.get('speed') or self.data.get('speed')),
            'internal_links': int(self._safe_number(self.data.get('internal_links'))),
            'external_links': int(self._safe_number(self.data.get('external_links'))),
            'broken_links': int(self._safe_number(self.data.get('b_links'))),
            'w3c_errors': int(self._safe_number(self.data.get('error_len'))),
            'w3c_warnings': int(self._safe_number(self.data.get('warn_len'))),
        }

    def _metric_card_table(self, title, value, note, accent_color=None):
        """Create a compact website-style KPI card."""
        accent_color = accent_color or self.PRIMARY_MID
        card = Table(
            [
                [Paragraph(title.upper(), self.styles['SmallMuted'])],
                [Paragraph(str(value), self.styles['CardValue'])],
                [Paragraph(note, self.styles['SmallMuted'])],
            ],
            colWidths=[1.75 * inch],
            rowHeights=[0.28 * inch, 0.42 * inch, 0.34 * inch]
        )
        card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 1, self.CARD_BORDER),
            ('LINEBEFORE', (0, 0), (0, -1), 4, accent_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return card

    def _score_bar_drawing(self, scores, width=460, height=190):
        """Create a clean horizontal score chart."""
        drawing = Drawing(width, height)
        drawing.add(String(0, height - 12, "Core SEO Score Profile", fontSize=12, fillColor=self.PRIMARY_DARK, fontName='Helvetica-Bold'))
        drawing.add(String(width - 118, height - 12, "0-100 scale", fontSize=8, fillColor=self.GRAY_500))

        chart_x = 92
        chart_y = height - 42
        bar_width = width - chart_x - 18
        row_gap = 24

        for idx, (label, raw_score) in enumerate(scores[:6]):
            score = max(0, min(100, self._safe_number(raw_score)))
            y = chart_y - (idx * row_gap)
            drawing.add(String(0, y + 2, str(label), fontSize=8.5, fillColor=self.GRAY_700))
            drawing.add(Rect(chart_x, y, bar_width, 8, fillColor=self.GRAY_100, strokeColor=None, rx=4, ry=4))
            drawing.add(Rect(chart_x, y, bar_width * (score / 100), 8, fillColor=self._score_color(score), strokeColor=None, rx=4, ry=4))
            drawing.add(String(chart_x + bar_width + 6, y + 1, f"{int(score)}", fontSize=8, fillColor=self.PRIMARY_DARK, fontName='Helvetica-Bold'))

        return drawing

    def _validation_pie_drawing(self, errors, warnings, width=210, height=170):
        """Create a W3C validation issue mix chart."""
        errors = max(0, int(errors))
        warnings = max(0, int(warnings))
        clean = 1 if errors == 0 and warnings == 0 else 0
        values = [errors, warnings, clean]
        labels = ['Errors', 'Warnings', 'Clean']

        drawing = Drawing(width, height)
        drawing.add(String(0, height - 12, "Validation Mix", fontSize=12, fillColor=self.PRIMARY_DARK, fontName='Helvetica-Bold'))

        pie = Pie()
        pie.x = 18
        pie.y = 32
        pie.width = 95
        pie.height = 95
        pie.data = values
        pie.slices[0].fillColor = self.ERROR
        pie.slices[1].fillColor = self.WARNING
        pie.slices[2].fillColor = self.SUCCESS
        pie.strokeColor = colors.white
        drawing.add(pie)

        for idx, label in enumerate(labels):
            color = [self.ERROR, self.WARNING, self.SUCCESS][idx]
            y = 104 - (idx * 22)
            drawing.add(Rect(132, y, 8, 8, fillColor=color, strokeColor=None, rx=2, ry=2))
            drawing.add(String(146, y - 1, f"{label}: {values[idx]}", fontSize=8.5, fillColor=self.GRAY_700))

        return drawing

    def _keyword_bar_drawing(self, width=460, height=180):
        """Create a keyword density mini-chart from available keyword lists."""
        keywords = self.data.get('lst', [])[:6]
        densities = self.data.get('dens', [])[:6]
        if not keywords:
            return None

        numeric_density = [self._safe_number(str(value).replace('%', '')) for value in densities]
        if len(numeric_density) < len(keywords):
            numeric_density.extend([0] * (len(keywords) - len(numeric_density)))

        max_density = max(numeric_density) if numeric_density else 1
        if max_density <= 0:
            max_density = 1

        drawing = Drawing(width, height)
        drawing.add(String(0, height - 12, "Top Keyword Density", fontSize=12, fillColor=self.PRIMARY_DARK, fontName='Helvetica-Bold'))

        chart_x = 135
        chart_y = height - 42
        bar_width = width - chart_x - 44
        row_gap = 22

        for idx, keyword in enumerate(keywords):
            y = chart_y - (idx * row_gap)
            value = numeric_density[idx]
            drawing.add(String(0, y + 1, str(keyword)[:22], fontSize=8, fillColor=self.GRAY_700))
            drawing.add(Rect(chart_x, y, bar_width, 8, fillColor=self.GRAY_100, strokeColor=None, rx=4, ry=4))
            drawing.add(Rect(chart_x, y, bar_width * (value / max_density), 8, fillColor=self.PRIMARY_MID, strokeColor=None, rx=4, ry=4))
            drawing.add(String(chart_x + bar_width + 8, y, f"{value:g}%", fontSize=8, fillColor=self.PRIMARY_DARK))

        return drawing

    def _create_cover_page(self):
        """Create a website-themed report cover page."""
        metrics = self._collect_dashboard_metrics()
        url = self.data.get('url', 'N/A')

        hero = Drawing(468, 205)
        hero.add(Rect(0, 0, 468, 205, fillColor=self.PRIMARY_DARK, strokeColor=None, rx=16, ry=16))
        hero.add(Circle(372, 104, 105, fillColor=colors.HexColor('#1729a6'), strokeColor=None))
        hero.add(Circle(404, 116, 64, fillColor=colors.HexColor('#203bd7'), strokeColor=None))
        hero.add(Circle(102, 151, 13, fillColor=self.PRIMARY_MID, strokeColor=None))
        hero.add(String(36, 168, "WEB LIFT", fontSize=12, fillColor=self.ACCENT, fontName='Helvetica-Bold'))
        hero.add(String(36, 128, "Website Audit", fontSize=31, fillColor=colors.white, fontName='Helvetica-Bold'))
        hero.add(String(36, 102, "Detailed SEO report with content, crawlability, security,", fontSize=10, fillColor=self.PRIMARY_LIGHT))
        hero.add(String(36, 86, "performance, social, and keyword opportunity signals.", fontSize=10, fillColor=self.PRIMARY_LIGHT))
        hero.add(String(36, 52, f"Analyzed URL: {str(url)[:58]}", fontSize=9.5, fillColor=colors.white, fontName='Helvetica-Bold'))
        hero.add(String(36, 32, f"Report Date: {date.today().strftime('%B %d, %Y')}", fontSize=8.5, fillColor=self.PRIMARY_LIGHT))
        hero.add(Circle(366, 105, 39, fillColor=None, strokeColor=self.ACCENT, strokeWidth=7))
        hero.add(String(343, 114, str(metrics['overall']), fontSize=27, fillColor=colors.white, fontName='Helvetica-Bold'))
        hero.add(String(347, 94, "overall", fontSize=8.5, fillColor=self.PRIMARY_LIGHT))

        self.story.append(Spacer(1, 0.2 * inch))
        self.story.append(hero)
        self.story.append(Spacer(1, 0.28 * inch))
        self._create_summary_scores()
        self.story.append(PageBreak())
    
    def _create_summary_scores(self):
        """Create summary scores overview on cover page with comprehensive metrics"""
        metrics = self._collect_dashboard_metrics()
        speed = metrics['speed']
        speed_note = "Target: under 2.5s" if speed else "No speed value"
        da_value = metrics['domain_authority'] if metrics['domain_authority'] is not None else "N/A"

        cards = Table(
            [[
                self._metric_card_table("Overall Score", f"{metrics['overall']}%", self._get_status(metrics['overall']), self._score_color(metrics['overall'])),
                self._metric_card_table("Load Speed", f"{speed:g}s" if speed else "N/A", speed_note, self.ACCENT),
                self._metric_card_table("Broken Links", metrics['broken_links'], "Links to fix first", self.ERROR if metrics['broken_links'] else self.SUCCESS),
                self._metric_card_table("Domain Authority", da_value, "Authority signal", self.PRIMARY_MID),
            ]],
            colWidths=[1.75 * inch, 1.75 * inch, 1.75 * inch, 1.75 * inch],
            hAlign='CENTER'
        )
        cards.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        self.story.append(cards)
        self.story.append(Spacer(1, 0.28 * inch))

        chart_shell = Table(
            [[
                self._score_bar_drawing(metrics['scores'], height=165),
                self._validation_pie_drawing(metrics['w3c_errors'], metrics['w3c_warnings'], height=150),
            ]],
            colWidths=[4.75 * inch, 2.35 * inch]
        )
        chart_shell.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 1, self.CARD_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 1, self.CARD_BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        self.story.append(chart_shell)

        return

        # Get data from both legacy and comprehensive structures
        seo = self.data.get('seo', {})
        metrics = self.data.get('metrics', {})
        keyword_ai = self.data.get('keyword_ai', {})
        
        # Use comprehensive data if available, fall back to legacy
        title_score = seo.get('title_score', 0) or self.data.get('title_score', 0)
        desc_score = seo.get('description_score', 0) or self.data.get('desc_score', 0)
        heading_score = seo.get('heading_score', 0) or self.data.get('heading_score', 0)
        social_score = seo.get('social_score', 0) or self.data.get('s_count', 0)
        speed = seo.get('speed', 0) or self.data.get('speed', 0)
        
        # Get Moz SEO Metrics
        da = metrics.get('domain_authority')
        
        # Get AI Content Quality
        content_stats = keyword_ai.get('content_stats', {})
        ai_quality = content_stats.get('quality_score', 0)
        
        scores_data = [
            ['Metric', 'Score', 'Status'],
            ['Title Optimization', f"{title_score}%", self._get_status(title_score)],
            ['Description Quality', f"{desc_score}%", self._get_status(desc_score)],
            ['Heading Structure', f"{heading_score}%", self._get_status(heading_score)],
            ['Social Presence', f"{social_score}%", self._get_status(social_score)],
            ['Website Speed', f"{speed}s", 'Good' if speed and speed < 2.5 else 'Slow'],
        ]
        
        # Add Moz metrics if available
        if da is not None:
            scores_data.append(['Domain Authority', str(da), self._get_authority_rating(da)])
        
        # Add AI content quality if available
        if ai_quality:
            scores_data.append(['AI Content Quality', f"{ai_quality}%", self._get_status(ai_quality)])
        
        table = Table(scores_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Body
            ('BACKGROUND', (0, 1), (-1, -1), self.GRAY_50),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.GRAY_900),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
        ]))
        
        self.story.append(Spacer(1, 0.5*inch))
        self.story.append(table)
    
    def _get_status(self, score):
        """Get status text based on score"""
        if score >= 70:
            return "Good"
        elif score >= 50:
            return "Fair"
        else:
            return "Needs Work"
    
    def _get_status(self, score):
        """Get clean status text based on score."""
        score = self._safe_number(score)
        if score >= 70:
            return "Good"
        if score >= 50:
            return "Fair"
        return "Needs Work"

    def _create_content_analysis(self):
        """Create Content Analysis section"""
        self.story.append(Paragraph("Content Analysis", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Title Analysis
        self._add_metric_card(
            "Meta Title",
            self.data.get('title', 'Not Found'),
            self.data.get('title_score', 0),
            "Optimal length: 30-60 characters. Use keywords and modifiers like 'best', 'guide', etc."
        )
        
        # Description Analysis
        self._add_metric_card(
            "Meta Description",
            self.data.get('desc', 'Not Found'),
            self.data.get('desc_score', 0),
            "Optimal length: 50-160 characters. Include main keywords and call-to-action."
        )
        
        # Heading Analysis
        heading_status = self.data.get('H', 'None')
        heading_text = f"Heading Structure: {heading_status}"
        self._add_metric_card(
            "Headings (H1, H2)",
            heading_text,
            self.data.get('heading_score', 0),
            "Use H1 once, H2 2-3 times. Include relevant keywords in headings."
        )
        
        # Keyword Density
        if self.data.get('lst') and len(self.data.get('lst', [])) >= 5:
            keyword_chart = self._keyword_bar_drawing(height=170)
            if keyword_chart:
                chart_shell = Table([[keyword_chart]], colWidths=[6.75 * inch])
                chart_shell.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                    ('BOX', (0, 0), (-1, -1), 1, self.CARD_BORDER),
                    ('LEFTPADDING', (0, 0), (-1, -1), 14),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 14),
                    ('TOPPADDING', (0, 0), (-1, -1), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                self.story.append(chart_shell)
                self.story.append(Spacer(1, 0.2 * inch))
            self._add_keyword_density_table()
        
        self.story.append(PageBreak())
    
    def _add_metric_card(self, title, value, score, recommendation):
        """Add a metric card with score and recommendation"""
        # Title
        self.story.append(Paragraph(title, self.styles['SubsectionTitle']))
        
        # Value
        value_str = str(value)[:100] if value else "Not Found"
        value_text = Paragraph(f"<b>Current:</b> {value_str}...", self.styles['BodyText'])
        self.story.append(value_text)
        
        # Score with visual indicator
        score_color = self.SUCCESS if score >= 70 else (self.WARNING if score >= 50 else self.ERROR)
        score_data = [[f"Score: {score}%", self._get_status(score)]]
        score_table = Table(score_data, colWidths=[3*inch, 2*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), score_color),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        self.story.append(score_table)
        
        # Recommendation
        rec_text = Paragraph(
            f"<b>Recommendation:</b> {recommendation}",
            self.styles['BodyText']
        )
        self.story.append(rec_text)
        self.story.append(Spacer(1, 0.3*inch))
    
    def _add_keyword_density_table(self):
        """Add keyword density analysis table"""
        self.story.append(Paragraph("Top Keywords Found", self.styles['SubsectionTitle']))
        
        keywords = self.data.get('lst', [])[:5]
        title = self.data.get('title', '').lower()
        desc = self.data.get('comp_desc', '').lower()
        heading = self.data.get('comp_head', '').lower()
        
        keyword_data = [['Keyword', 'In Title', 'In Description', 'In Heading']]
        
        for kw in keywords:
            kw_lower = kw.lower()
            keyword_data.append([
                kw,
                'Yes' if kw_lower in title else 'No',
                'Yes' if kw_lower in desc else 'No',
                'Yes' if kw_lower in heading else 'No'
            ])
        
        table = Table(keyword_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 0.2*inch))
    
    def _create_technical_analysis(self):
        """Create Technical/Structured Analysis section"""
        self.story.append(Paragraph("Technical Analysis", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Create technical metrics table
        tech_data = [
            ['Feature', 'Status', 'Recommendation'],
            [
                'Robot.txt',
                'Found' if self.data.get('robot_flag') else 'Not Found',
                'Essential for controlling search engine crawling'
            ],
            [
                'XML Sitemap',
                'Found' if self.data.get('sitemap_flag') else 'Not Found',
                'Helps search engines discover all pages'
            ],
            [
                'Schema Markup',
                'Implemented' if self.data.get('schema_flag') else 'Missing',
                'Improves search result display with rich snippets'
            ],
            [
                'Open Graph Protocol',
                'Implemented' if self.data.get('ogp_flag') else 'Missing',
                'Optimizes social media sharing appearance'
            ],
            [
                'Favicon',
                'Found' if self.data.get('icon_flag') else 'Not Found',
                'Improves brand recognition in browser tabs'
            ],
            [
                'Google Analytics',
                'Installed' if self.data.get('analytics_flag') else 'Not Installed',
                'Essential for tracking website performance'
            ],
            [
                'DocType Declaration',
                'Found' if self.data.get('doc_flag') else 'Missing',
                f"Current: {self.data.get('Doctype', 'N/A')}"
            ],
            [
                'Character Encoding',
                'Set' if self.data.get('encod_flag') else 'Not Set',
                f"Current: {self.data.get('Encoding', 'N/A')}"
            ],
        ]
        
        table = Table(tech_data, colWidths=[2*inch, 1.5*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.story.append(table)
        
        # Server Information
        self.story.append(Spacer(1, 0.3*inch))
        self.story.append(Paragraph("Server Information", self.styles['SubsectionTitle']))
        
        server_data = [
            ['Metric', 'Value'],
            ['Server IP', self.data.get('ip', 'Not Found') if self.data.get('ip_flag') else 'Not Found'],
            ['Server Location', self.data.get('loc_name', 'Not Found') if self.data.get('server_loc_flag') else 'Not Found'],
            ['Web Server', self.data.get('webserver', 'Not Found') if self.data.get('tech_flag') else 'Not Found'],
            ['W3C Validation Errors', str(self.data.get('error_len', 0))],
            ['W3C Validation Warnings', str(self.data.get('warn_len', 0))],
        ]
        
        server_table = Table(server_data, colWidths=[2.5*inch, 4*inch])
        server_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_MID),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.story.append(server_table)
        
        # Broken Links Warning
        broken_count = self.data.get('b_links', 0)
        if broken_count > 0:
            self.story.append(Spacer(1, 0.2*inch))
            broken_text = Paragraph(
                f"<b>Critical:</b> {broken_count} broken link(s) detected. Fix immediately to avoid SEO penalties and poor user experience.",
                ParagraphStyle(
                    name='Warning',
                    parent=self.styles['BodyText'],
                    textColor=self.ERROR,
                    fontName='Helvetica-Bold'
                )
            )
            self.story.append(broken_text)
        
        # Links Summary
        self.story.append(Spacer(1, 0.2*inch))
        links_text = Paragraph(
            f"<b>Links Analysis:</b> Internal Links: {self.data.get('internal_links', 0)} | "
            f"External Links: {self.data.get('external_links', 0)} | "
            f"Images without Alt: {self.data.get('alt_count', 0)}",
            self.styles['BodyText']
        )
        self.story.append(links_text)
        
        self.story.append(PageBreak())
    
    def _create_security_analysis(self):
        """Create Security Analysis section"""
        self.story.append(Paragraph("Security Analysis", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # SSL Information
        ssl_data = [
            ['SSL Certificate', 'Details'],
            ['Certificate Name', self.data.get('ssl_name', 'Not Found')],
            ['Organization', self.data.get('ssl_organ', 'Not Found')],
            ['Expiry Date', str(self.data.get('ssl_expiry', 'Not Found'))],
            ['HTTPS Redirect', 'Active' if self.data.get('https') else 'Inactive'],
            ['DMCA Protection', 'Protected' if self.data.get('dmca') else 'Not Protected'],
        ]
        
        table = Table(ssl_data, colWidths=[2.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 0.2*inch))
        
        # Security Recommendations
        rec = Paragraph(
            "<b>Security Recommendations:</b><br/>"
            "- Ensure SSL certificate is always up to date<br/>"
            "- Implement HTTPS redirection for all pages<br/>"
            "- Consider DMCA protection for content security<br/>"
            "- Regular security audits recommended",
            self.styles['BodyText']
        )
        self.story.append(rec)
        
        self.story.append(PageBreak())
    
    def _create_performance_analysis(self):
        """Create Performance Analysis section"""
        self.story.append(Paragraph("Performance Metrics", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Performance scores
        perf_data = [
            ['Metric', 'Value', 'Target', 'Status'],
            [
                'Page Load Speed',
                f"{self.data.get('speed', 0)}s",
                '< 2.5s',
                'Good' if self.data.get('speed', 99) < 2.5 else 'Needs Work'
            ],
            [
                'CSS Minification',
                'Yes' if self.data.get('css') else 'No',
                'Yes',
                'Good' if self.data.get('css') else 'Needs Work'
            ],
            [
                'JS Minification',
                'Yes' if self.data.get('jss') else 'No',
                'Yes',
                'Good' if self.data.get('jss') else 'Needs Work'
            ],
            [
                'Optimized Plugins',
                'Yes' if self.data.get('plugins') else 'No',
                'Yes',
                'Good' if self.data.get('plugins') else 'Needs Work'
            ],
        ]
        
        table = Table(perf_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        self.story.append(table)
        
        # Performance Recommendations
        self.story.append(Spacer(1, 0.2*inch))
        perf_rec = Paragraph(
            "<b>Performance Recommendations:</b><br/>"
            "- Optimize and compress images (WebP format recommended)<br/>"
            "- Enable browser caching and GZIP compression<br/>"
            "- Minimize HTTP requests by combining files<br/>"
            "- Use a Content Delivery Network (CDN)<br/>"
            "- Defer loading of non-critical JavaScript",
            self.styles['BodyText']
        )
        self.story.append(perf_rec)
        
        self.story.append(PageBreak())
    
    def _create_social_analysis(self):
        """Create Social Media Analysis section"""
        self.story.append(Paragraph("Social Media Presence", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Social platforms table
        social_data = [
            ['Platform', 'Status', 'Link Found'],
            ['Facebook', 'Connected' if self.data.get('facebook_flag') else 'Missing', 'Yes' if self.data.get('facebook_flag') else 'No'],
            ['Instagram', 'Connected' if self.data.get('instagram_flag') else 'Missing', 'Yes' if self.data.get('instagram_flag') else 'No'],
            ['Twitter', 'Connected' if self.data.get('twitter_flag') else 'Missing', 'Yes' if self.data.get('twitter_flag') else 'No'],
            ['LinkedIn', 'Connected' if self.data.get('linkedin_flag') else 'Missing', 'Yes' if self.data.get('linkedin_flag') else 'No'],
        ]
        
        table = Table(social_data, colWidths=[2*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        self.story.append(table)
        
        # Social score
        self.story.append(Spacer(1, 0.2*inch))
        social_score = self.data.get('s_count', 0)
        
        # Count connected platforms
        connected = sum([
            self.data.get('facebook_flag', False),
            self.data.get('instagram_flag', False),
            self.data.get('twitter_flag', False),
            self.data.get('linkedin_flag', False)
        ])
        
        score_text = Paragraph(
            f"<b>Social Presence Score: {social_score}%</b><br/>"
            f"Platforms Connected: {connected}/4",
            ParagraphStyle(
                name='SocialScore',
                parent=self.styles['BodyText'],
                fontSize=12,
                textColor=self.PRIMARY_DARK,
                fontName='Helvetica-Bold'
            )
        )
        self.story.append(score_text)
        
        # Recommendations
        self.story.append(Spacer(1, 0.2*inch))
        social_rec = Paragraph(
            "<b>Social Media Recommendations:</b><br/>"
            "- Add social media links to increase brand visibility<br/>"
            "- Regular posting increases engagement and SEO benefits<br/>"
            "- Use social media for content distribution<br/>"
            "- Monitor social signals for brand reputation",
            self.styles['BodyText']
        )
        self.story.append(social_rec)
        
        self.story.append(PageBreak())
    
    def _create_mobile_analysis(self):
        """Create Mobile Usability Analysis section"""
        self.story.append(Paragraph("Mobile Usability", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Mobile metrics table
        mobile_data = [
            ['Metric', 'Value', 'Status'],
            [
                'Mobile Speed Score',
                f"{self.data.get('mob_score', 0)}s",
                'Good' if self.data.get('mob_score', 99) < 3 else 'Needs Work'
            ],
            [
                'AMP (Accelerated Mobile Pages)',
                'Enabled' if self.data.get('amp') else 'Not Enabled',
                'Recommended for faster mobile loading'
            ],
            [
                'Mobile Rendering',
                'Working' if self.data.get('render') else 'Issues Detected',
                'Essential for mobile user experience'
            ],
            [
                'Mobile Preview Optimized',
                'Yes' if self.data.get('mobpreview') else 'No',
                'Affects mobile search appearance'
            ],
        ]
        
        table = Table(mobile_data, colWidths=[2.5*inch, 2*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        self.story.append(table)
        
        # Mobile recommendations
        self.story.append(Spacer(1, 0.2*inch))
        
        mobile_score = self.data.get('mob_score', 99)
        if mobile_score >= 3:
            rec_text = Paragraph(
                "<b>Mobile Speed Needs Improvement:</b><br/>"
                "- Reduce image sizes and use modern formats (WebP)<br/>"
                "- Minimize render-blocking resources<br/>"
                "- Enable text compression<br/>"
                "- Consider implementing AMP for faster mobile pages<br/>"
                "- Test on real mobile devices regularly",
                ParagraphStyle(
                    name='MobileWarning',
                    parent=self.styles['BodyText'],
                    textColor=self.ERROR
                )
            )
        else:
            rec_text = Paragraph(
                "<b>Mobile Performance is Good:</b><br/>"
                "- Continue monitoring mobile performance<br/>"
                "- Test on various devices and screen sizes<br/>"
                "- Keep mobile-first design principles<br/>"
                "- Regularly update mobile optimization",
                ParagraphStyle(
                    name='MobileSuccess',
                    parent=self.styles['BodyText'],
                    textColor=self.SUCCESS
                )
            )
        
        self.story.append(rec_text)
        
        self.story.append(PageBreak())
    
    def _create_action_plan(self):
        """Create prioritized action plan"""
        self.story.append(Paragraph("Recommended Action Plan", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Priority actions
        actions = []
        
        # CRITICAL ISSUES (HIGH Priority)
        if self.data.get('title_score', 0) < 50:
            actions.append(('HIGH', 'Optimize Meta Title (30-60 characters with keywords)'))
        
        if self.data.get('desc_score', 0) < 50:
            actions.append(('HIGH', 'Improve Meta Description (50-160 characters)'))
        
        if not self.data.get('https'):
            actions.append(('HIGH', 'Implement HTTPS redirection for security'))
        
        if self.data.get('b_links', 0) > 0:
            actions.append(('HIGH', f'Fix {self.data.get("b_links")} broken link(s) immediately'))
        
        if self.data.get('H') is None or self.data.get('heading_score', 0) == 0:
            actions.append(('HIGH', 'Add proper heading structure (H1, H2 tags)'))
        
        if not self.data.get('ssl'):
            actions.append(('HIGH', 'Install SSL certificate for website security'))
        
        if self.data.get('speed', 0) > 3:
            actions.append(('HIGH', f'Critical: Page load speed is {self.data.get("speed")}s - optimize immediately'))
        
        # IMPORTANT ISSUES (MEDIUM Priority)
        if not self.data.get('sitemap_flag'):
            actions.append(('MEDIUM', 'Create and submit XML sitemap to search engines'))
        
        if not self.data.get('robot_flag'):
            actions.append(('MEDIUM', 'Create robot.txt file for search engine control'))
        
        if not self.data.get('schema_flag'):
            actions.append(('MEDIUM', 'Implement Schema markup for rich snippets'))
        
        if not self.data.get('analytics_flag'):
            actions.append(('MEDIUM', 'Install Google Analytics for traffic tracking'))
        
        if self.data.get('speed', 0) > 2.5 and self.data.get('speed', 0) <= 3:
            actions.append(('MEDIUM', 'Optimize page load speed (target < 2.5s)'))
        
        if not self.data.get('css'):
            actions.append(('MEDIUM', 'Minify CSS files to improve load speed'))
        
        if not self.data.get('jss'):
            actions.append(('MEDIUM', 'Minify JavaScript files to improve load speed'))
        
        if self.data.get('alt_count', 0) > 0:
            actions.append(('MEDIUM', f'Add alt attributes to {self.data.get("alt_count")} image(s)'))
        
        if not self.data.get('dmca'):
            actions.append(('MEDIUM', 'Consider DMCA protection for content security'))
        
        if self.data.get('mob_score', 0) > 3:
            actions.append(('MEDIUM', 'Improve mobile page load speed'))
        
        if not self.data.get('render'):
            actions.append(('MEDIUM', 'Fix mobile rendering issues'))
        
        if self.data.get('error_len', 0) > 10:
            actions.append(('MEDIUM', f'Fix {self.data.get("error_len")} W3C validation error(s)'))
        
        # ENHANCEMENT ISSUES (LOW Priority)
        if not self.data.get('ogp_flag'):
            actions.append(('LOW', 'Add Open Graph tags for better social sharing'))
        
        if not self.data.get('icon_flag'):
            actions.append(('LOW', 'Add favicon for better brand recognition'))
        
        if self.data.get('s_count', 0) < 75:
            actions.append(('LOW', 'Improve social media presence (connect more platforms)'))
        
        if not self.data.get('plugins'):
            actions.append(('LOW', 'Use optimized plugins for better performance'))
        
        if not self.data.get('amp'):
            actions.append(('LOW', 'Consider implementing AMP for faster mobile pages'))
        
        if not self.data.get('mobpreview'):
            actions.append(('LOW', 'Optimize mobile preview appearance'))
        
        if self.data.get('warn_len', 0) > 20:
            actions.append(('LOW', f'Review {self.data.get("warn_len")} W3C validation warning(s)'))
        
        if self.data.get('external_links', 0) < 3:
            actions.append(('LOW', 'Add more external links to authoritative sources'))
        
        # Create action plan table
        action_data = [['Priority', 'Action Item']]
        for priority, action in actions:
            action_data.append([priority, action])
        
        if len(action_data) > 1:
            table = Table(action_data, colWidths=[1.5*inch, 5*inch])
            
            # Color code priorities
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]
            
            # Color code based on priority
            for idx, (priority, _) in enumerate(actions, start=1):
                if priority == 'HIGH':
                    table_style.append(('BACKGROUND', (0, idx), (0, idx), self.ERROR))
                    table_style.append(('TEXTCOLOR', (0, idx), (0, idx), colors.white))
                    table_style.append(('FONTNAME', (0, idx), (0, idx), 'Helvetica-Bold'))
                elif priority == 'MEDIUM':
                    table_style.append(('BACKGROUND', (0, idx), (0, idx), self.WARNING))
                    table_style.append(('TEXTCOLOR', (0, idx), (0, idx), colors.white))
                    table_style.append(('FONTNAME', (0, idx), (0, idx), 'Helvetica-Bold'))
                else:
                    table_style.append(('BACKGROUND', (0, idx), (0, idx), self.SUCCESS))
                    table_style.append(('TEXTCOLOR', (0, idx), (0, idx), colors.white))
                    table_style.append(('FONTNAME', (0, idx), (0, idx), 'Helvetica-Bold'))
            
            table.setStyle(TableStyle(table_style))
            self.story.append(table)
            
            # Summary
            self.story.append(Spacer(1, 0.3*inch))
            high_count = sum(1 for p, _ in actions if p == 'HIGH')
            medium_count = sum(1 for p, _ in actions if p == 'MEDIUM')
            low_count = sum(1 for p, _ in actions if p == 'LOW')
            
            summary = Paragraph(
                f"<b>Action Summary:</b> {high_count} High Priority | "
                f"{medium_count} Medium Priority | {low_count} Low Priority<br/><br/>"
                f"<b>Next Steps:</b> Focus on HIGH priority items first for maximum SEO impact.",
                self.styles['BodyText']
            )
            self.story.append(summary)
        else:
            success_msg = Paragraph(
                "Excellent. Your website has no critical issues. Continue monitoring and maintaining current standards.",
                ParagraphStyle(
                    name='Success',
                    parent=self.styles['BodyText'],
                    textColor=self.SUCCESS,
                    fontSize=12,
                    fontName='Helvetica-Bold'
                )
            )
            self.story.append(success_msg)
    
    def _create_seo_metrics(self):
        """Create SEO Metrics section with Moz Authority data and backlinks"""
        metrics = self.data.get('metrics', {})
        
        if not metrics:
            return
        
        self.story.append(Paragraph("SEO Metrics & Authority", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Authority Metrics from Moz API
        da = metrics.get('domain_authority')
        pa = metrics.get('page_authority')
        moz_rank = metrics.get('moz_rank')
        
        if da is not None or pa is not None:
            self.story.append(Paragraph("Domain Authority & Page Authority (Moz)", self.styles['SubsectionTitle']))
            
            # Authority scores table
            auth_data = [
                ['Metric', 'Score', 'Rating'],
            ]
            
            if da is not None:
                auth_data.append(['Domain Authority', f"{da}", self._get_authority_rating(da)])
            if pa is not None:
                auth_data.append(['Page Authority', f"{pa}", self._get_authority_rating(pa)])
            if moz_rank is not None:
                auth_data.append(['MozRank', f"{moz_rank}", 'Good' if moz_rank >= 5 else 'Fair'])
            
            if len(auth_data) > 1:
                table = Table(auth_data, colWidths=[2.5*inch, 2*inch, 2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                self.story.append(table)
                self.story.append(Spacer(1, 0.2*inch))
        
        # Backlink profile from Moz
        backlinks = metrics.get('backlinks', {})
        linking_domains = metrics.get('linking_root_domains')
        total_backlinks = metrics.get('total_backlinks')
        
        if linking_domains is not None or total_backlinks is not None:
            self.story.append(Paragraph("Backlink Profile", self.styles['SubsectionTitle']))
            
            backlink_data = [
                ['Metric', 'Value'],
            ]
            
            if linking_domains is not None:
                backlink_data.append(['Linking Root Domains', str(linking_domains)])
            if total_backlinks is not None:
                backlink_data.append(['Total Backlinks', str(total_backlinks)])
            
            ref_domains = backlinks.get('referring_domains', 'N/A')
            if ref_domains != 'N/A':
                backlink_data.append(['Referring Domains (API)', str(ref_domains)])
            
            if len(backlink_data) > 1:
                table = Table(backlink_data, colWidths=[3*inch, 3.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_MID),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                self.story.append(table)
                self.story.append(Spacer(1, 0.2*inch))
            
            # Backlink recommendations
            if linking_domains is not None and linking_domains < 10:
                rec = Paragraph(
                    "<b>Backlink Strategy Needed:</b> Your site has few referring domains. "
                    "Focus on building quality backlinks through guest posting, partnerships, and content marketing.",
                    ParagraphStyle(
                        name='BacklinkWarning',
                        parent=self.styles['BodyText'],
                        textColor=self.WARNING
                    )
                )
                self.story.append(rec)
                self.story.append(Spacer(1, 0.2*inch))
        
        self.story.append(PageBreak())
    
    def _create_semantic_analysis(self):
        """Create Semantic Analysis section with AI-powered content insights"""
        keyword_ai = self.data.get('keyword_ai', {})
        
        if not keyword_ai:
            return
        
        self.story.append(Paragraph("Semantic Analysis & Content Insights", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # AI Content Stats
        content_stats = keyword_ai.get('content_stats', {})
        if content_stats:
            self.story.append(Paragraph("AI-Powered Content Analysis", self.styles['SubsectionTitle']))
            
            word_count = content_stats.get('word_count', 0)
            ai_quality = content_stats.get('quality_score', 0)
            ai_readability = content_stats.get('readability_score', 0)
            
            content_data = [
                ['Metric', 'Value', 'Status'],
            ]
            
            if word_count > 0:
                content_data.append(['Word Count', f"{word_count}", 'Good' if word_count >= 300 else 'Needs Work'])
            if ai_quality > 0:
                content_data.append(['AI Quality Score', f"{ai_quality}%", self._get_status(ai_quality)])
            if ai_readability > 0:
                content_data.append(['Readability Score', f"{ai_readability}%", self._get_status(ai_readability)])
            
            if len(content_data) > 1:
                table = Table(content_data, colWidths=[2.5*inch, 1.5*inch, 2.5*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                self.story.append(table)
                self.story.append(Spacer(1, 0.2*inch))
            
            # Content quality recommendations
            if ai_quality < 50:
                rec = Paragraph(
                    "<b>Content Quality Improvements:</b><br/>"
                    "- Expand content with more comprehensive information<br/>"
                    "- Use proper heading structure (H1, H2, H3)<br/>"
                    "- Include relevant keywords naturally<br/>"
                    "- Add internal and external links<br/>"
                    "- Improve readability with shorter paragraphs",
                    ParagraphStyle(
                        name='QualityWarning',
                        parent=self.styles['BodyText'],
                        textColor=self.WARNING
                    )
                )
                self.story.append(rec)
                self.story.append(Spacer(1, 0.2*inch))
        
        # Search Intent Analysis
        intent_analysis = keyword_ai.get('intent_analysis', {})
        search_intent = keyword_ai.get('search_intent', '')
        
        if search_intent or intent_analysis:
            self.story.append(Paragraph("Search Intent Analysis", self.styles['SubsectionTitle']))
            
            intent_text = Paragraph(
                f"<b>Primary Search Intent:</b> {search_intent.title() if search_intent else 'Informational'}<br/>"
                f"<b>Intent Alignment:</b> Content should match user intent to rank effectively. "
                f"Create content that directly answers user queries for better rankings.",
                self.styles['BodyText']
            )
            self.story.append(intent_text)
            self.story.append(Spacer(1, 0.2*inch))
        
        self.story.append(PageBreak())
    
    def _create_keyword_suggestions(self):
        """Create AI-Powered Keyword Suggestions section"""
        keyword_ai = self.data.get('keyword_ai', {})
        
        if not keyword_ai:
            return
        
        self.story.append(Paragraph("AI-Powered Keyword Opportunities", self.styles['SectionTitle']))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Top Keywords Table
        top_keywords = keyword_ai.get('top_keywords', [])
        if top_keywords:
            self.story.append(Paragraph("Top Keyword Opportunities", self.styles['SubsectionTitle']))
            
            # Limit to top 15
            display_keywords = top_keywords[:15]
            
            keyword_data = [['Keyword', 'Score', 'Priority', 'Type']]
            
            for kw in display_keywords:
                if isinstance(kw, dict):
                    keyword = kw.get('keyword', '')
                    score = kw.get('relevance_score', kw.get('score', 0))
                    priority = kw.get('priority', 'medium')
                    kw_type = kw.get('keyword_type', 'suggested')
                else:
                    keyword = str(kw)
                    score = 50
                    priority = 'medium'
                    kw_type = 'suggested'
                
                keyword_data.append([
                    keyword[:35],  # Limit length
                    f"{int(score)}%",
                    priority.upper(),
                    kw_type.title()
                ])
            
            table = Table(keyword_data, colWidths=[3*inch, 1*inch, 1.2*inch, 1.3*inch])
            
            # Dynamic coloring based on priority
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, self.PRIMARY_LIGHT),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.GRAY_50]),
            ]
            
            # Color code priority badges
            for idx, row in enumerate(display_keywords, start=1):
                if isinstance(row, dict):
                    priority = row.get('priority', 'medium')
                else:
                    priority = 'medium'
                
                if priority == 'high':
                    table_style.append(('BACKGROUND', (2, idx), (2, idx), self.ERROR))
                    table_style.append(('TEXTCOLOR', (2, idx), (2, idx), colors.white))
                elif priority == 'medium':
                    table_style.append(('BACKGROUND', (2, idx), (2, idx), self.WARNING))
                    table_style.append(('TEXTCOLOR', (2, idx), (2, idx), colors.white))
                else:
                    table_style.append(('BACKGROUND', (2, idx), (2, idx), self.SUCCESS))
                    table_style.append(('TEXTCOLOR', (2, idx), (2, idx), colors.white))
            
            table.setStyle(TableStyle(table_style))
            self.story.append(table)
            self.story.append(Spacer(1, 0.3*inch))
        
        # Search Intent Analysis
        intent_analysis = keyword_ai.get('intent_analysis', {})
        search_intent = keyword_ai.get('search_intent', '')
        
        if search_intent or intent_analysis:
            self.story.append(Paragraph("Search Intent Analysis", self.styles['SubsectionTitle']))
            
            intent_text = Paragraph(
                f"<b>Primary Search Intent:</b> {search_intent.title() if search_intent else 'Informational'}<br/>"
                f"<b>Intent Alignment:</b> Content should match user intent to rank effectively.<br/>"
                f"Create content that directly answers user queries for better rankings.",
                self.styles['BodyText']
            )
            self.story.append(intent_text)
            self.story.append(Spacer(1, 0.2*inch))
        
        # Keyword Clusters with AI Reasoning
        clusters = keyword_ai.get('keyword_clusters', {})
        if clusters:
            self.story.append(Paragraph("Keyword Clusters & AI Insights", self.styles['SubsectionTitle']))
            
            for cluster_name, cluster_data in list(clusters.items())[:3]:  # Top 3 clusters
                if isinstance(cluster_data, dict):
                    keywords = cluster_data.get('keywords', [])
                    theme = cluster_data.get('theme', '')
                    reasoning = cluster_data.get('reasoning', '')
                elif isinstance(cluster_data, list):
                    keywords = cluster_data
                    theme = ''
                    reasoning = ''
                else:
                    continue
                
                if not keywords:
                    continue
                
                # Cluster header
                cluster_title = Paragraph(
                    f"<b>Cluster: {cluster_name}</b>",
                    ParagraphStyle(
                        name='ClusterTitle',
                        parent=self.styles['SubsectionTitle'],
                        fontSize=11,
                        textColor=self.PRIMARY_MID
                    )
                )
                self.story.append(cluster_title)
                
                if theme:
                    theme_text = Paragraph(f"<b>Theme:</b> {theme}", self.styles['BodyText'])
                    self.story.append(theme_text)
                
                # Keywords in cluster
                kw_text = f"<b>Keywords:</b> {', '.join(keywords[:10])}"
                if len(keywords) > 10:
                    kw_text += f" (+{len(keywords) - 10} more)"
                
                kw_para = Paragraph(kw_text, self.styles['BodyText'])
                self.story.append(kw_para)
                
                # AI Reasoning
                if reasoning:
                    reasoning_para = Paragraph(
                            f"<b>AI Insight:</b> {reasoning[:200]}...",
                        ParagraphStyle(
                            name='AIReasoning',
                            parent=self.styles['BodyText'],
                            textColor=self.PRIMARY_MID,
                            fontSize=9,
                            leftIndent=20
                        )
                    )
                    self.story.append(reasoning_para)
                
                self.story.append(Spacer(1, 0.15*inch))
        
        # Content Optimization Suggestions
        optimizations = keyword_ai.get('optimization_suggestions', [])
        if optimizations:
            self.story.append(Paragraph("AI Content Optimization Suggestions", self.styles['SubsectionTitle']))
            
            for opt in optimizations[:5]:  # Top 5 suggestions
                if isinstance(opt, dict):
                    suggestion = opt.get('suggestion', '')
                    impact = opt.get('impact', 'medium')
                else:
                    suggestion = str(opt)
                    impact = 'medium'
                
                impact_color = self.ERROR if impact == 'high' else (self.WARNING if impact == 'medium' else self.SUCCESS)
                
                opt_text = Paragraph(
                    f"- <b>[{impact.upper()}]</b> {suggestion[:150]}",
                    self.styles['BodyText']
                )
                self.story.append(opt_text)
                self.story.append(Spacer(1, 0.1*inch))
        
        self.story.append(PageBreak())
    
    def _get_authority_rating(self, score):
        """Get rating text for authority score"""
        if score is None or score == 'N/A':
            return 'N/A'
        try:
            score = int(score)
            if score >= 50:
                return 'Strong'
            elif score >= 30:
                return 'Moderate'
            else:
                return 'Weak'
        except (ValueError, TypeError):
            return 'N/A'

    def _deep_header_footer(self, canvas, doc):
        """Minimal page furniture for the deep audit report."""
        canvas.saveState()
        if doc.page > 1:
            canvas.setFillColor(colors.white)
            canvas.rect(0, letter[1] - 50, letter[0], 50, fill=True, stroke=False)
            canvas.setStrokeColor(self.CARD_BORDER)
            canvas.line(42, letter[1] - 50, letter[0] - 42, letter[1] - 50)
            canvas.setFillColor(self.PRIMARY_DARK)
            canvas.setFont('Helvetica-Bold', 10)
            canvas.drawString(50, letter[1] - 30, "WEB LIFT / SEO DEEP AUDIT REPORT")
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(self.GRAY_500)
            canvas.drawRightString(letter[0] - 50, letter[1] - 30, date.today().strftime('%B %d, %Y'))

        canvas.setStrokeColor(self.CARD_BORDER)
        canvas.line(42, 44, letter[0] - 42, 44)
        canvas.setFillColor(self.GRAY_500)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(50, 28, str(self.data.get('url', '')))
        canvas.drawRightString(letter[0] - 50, 28, f"Page {doc.page}")
        canvas.restoreState()

    def _deep_para(self, text, style='MyBodyText', bold=False):
        """Create a safe paragraph for report content."""
        text = escape(str(text if text not in (None, '') else 'N/A'))
        if bold:
            text = f"<b>{text}</b>"
        return Paragraph(text, self.styles[style])

    def _deep_section(self, title, subtitle=None):
        """Add a consistent section header."""
        block = [[
            Paragraph(escape(title), ParagraphStyle(
                name=f"DeepSection{title[:8]}",
                parent=self.styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=16,
                textColor=self.PRIMARY_DARK,
                leading=19,
            ))
        ]]
        if subtitle:
            block.append([Paragraph(escape(subtitle), self.styles['SmallMuted'])])

        table = Table(block, colWidths=[7.0 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.SOFT_BLUE),
            ('LINEBEFORE', (0, 0), (0, -1), 4, self.PRIMARY_MID),
            ('BOX', (0, 0), (-1, -1), 1, self.CARD_BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 0.18 * inch))

    def _deep_table(self, rows, col_widths, header=True):
        """Create a polished wrapped table."""
        wrapped = []
        header_style = ParagraphStyle(
            name='DeepTableHeader',
            parent=self.styles['CardTitle'],
            textColor=colors.white,
            fontSize=9,
            leading=11,
        )
        cell_style = ParagraphStyle(
            name='DeepTableCell',
            parent=self.styles['MyBodyText'],
            alignment=TA_LEFT,
            leading=12,
        )
        for row_idx, row in enumerate(rows):
            wrapped_row = []
            for value in row:
                if header and row_idx == 0:
                    wrapped_row.append(Paragraph(escape(str(value)), header_style))
                else:
                    wrapped_row.append(Paragraph(escape(str(value if value not in (None, '') else 'N/A')), cell_style))
            wrapped.append(wrapped_row)

        table = Table(wrapped, colWidths=col_widths, repeatRows=1 if header else 0)
        styles = [
            ('BOX', (0, 0), (-1, -1), 1, self.CARD_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, self.CARD_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 9),
            ('RIGHTPADDING', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1 if header else 0), (-1, -1), [colors.white, self.GRAY_50]),
        ]
        if header:
            styles.extend([
                ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_DARK),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ])
        table.setStyle(TableStyle(styles))
        self.story.append(table)
        self.story.append(Spacer(1, 0.18 * inch))
        return table

    def _deep_metric_row(self, cards):
        """Add one row of KPI cards."""
        row = [self._metric_card_table(*card) for card in cards]
        table = Table([row], colWidths=[1.75 * inch] * len(row), hAlign='CENTER')
        table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        self.story.append(table)
        self.story.append(Spacer(1, 0.22 * inch))

    def _deep_list(self, items, empty="No issues detected."):
        """Format list-like values as a readable paragraph."""
        if not items:
            return empty
        if isinstance(items, str):
            return items
        return "; ".join(f"- {str(item)}" for item in items[:8])

    def _deep_status(self, flag, good="Present", bad="Missing"):
        return good if flag else bad

    def _deep_actions(self):
        """Build prioritized recommendations from the audit data."""
        actions = []
        if self._safe_number(self.data.get('title_score')) < 50:
            actions.append(('High', 'Optimize the meta title to 30-60 characters with a clear primary keyword.'))
        if self._safe_number(self.data.get('desc_score')) < 50:
            actions.append(('High', 'Rewrite the meta description with a clear benefit and search intent match.'))
        if not self.data.get('https'):
            actions.append(('High', 'Enable HTTPS redirect across the whole site.'))
        if self._safe_number(self.data.get('b_links')) > 0:
            actions.append(('High', f"Fix {int(self._safe_number(self.data.get('b_links')))} broken link(s)."))
        if self._safe_number(self.data.get('speed')) > 3:
            actions.append(('High', f"Improve page load speed from {self.data.get('speed')}s toward the 2.5s target."))
        if not self.data.get('sitemap_flag'):
            actions.append(('Medium', 'Create and submit an XML sitemap.'))
        if not self.data.get('robot_flag'):
            actions.append(('Medium', 'Add a robots.txt file to guide crawler access.'))
        if not self.data.get('schema_flag'):
            actions.append(('Medium', 'Add schema markup for richer search result eligibility.'))
        if not self.data.get('analytics_flag'):
            actions.append(('Medium', 'Install analytics tracking to measure SEO outcomes.'))
        if self._safe_number(self.data.get('alt_count')) > 0:
            actions.append(('Medium', f"Add descriptive alt text to {int(self._safe_number(self.data.get('alt_count')))} image(s)."))
        if not self.data.get('ogp_flag'):
            actions.append(('Low', 'Add Open Graph metadata for stronger social previews.'))
        if self._safe_number(self.data.get('warn_len')) > 20:
            actions.append(('Low', f"Review {int(self._safe_number(self.data.get('warn_len')))} W3C validation warning(s)."))

        keyword_ai = self.data.get('keyword_ai', {})
        for suggestion in keyword_ai.get('optimization_suggestions', [])[:4]:
            if isinstance(suggestion, dict):
                actions.append((str(suggestion.get('impact', 'Medium')).title(), suggestion.get('suggestion', 'Review content opportunity.')))
            else:
                actions.append(('Medium', str(suggestion)))

        if not actions:
            actions.append(('Monitor', 'No critical blockers detected. Continue monitoring technical health and content quality.'))
        return actions[:16]

    def _build_deep_cover(self):
        """Build the cover for the deep audit report."""
        metrics = self._collect_dashboard_metrics()
        url = str(self.data.get('url', 'N/A'))
        hero = Drawing(500, 315)
        hero.add(Rect(0, 0, 500, 315, fillColor=self.PRIMARY_DARK, strokeColor=None, rx=18, ry=18))
        hero.add(Circle(392, 166, 104, fillColor=colors.HexColor('#13249b'), strokeColor=None))
        hero.add(Circle(420, 172, 58, fillColor=colors.HexColor('#254cff'), strokeColor=None))
        hero.add(Line(316, 58, 468, 248, strokeColor=self.ACCENT, strokeWidth=1))
        hero.add(String(38, 260, "WEB LIFT", fontSize=13, fillColor=self.ACCENT, fontName='Helvetica-Bold'))
        hero.add(String(38, 208, "SEO Deep Audit", fontSize=34, fillColor=colors.white, fontName='Helvetica-Bold'))
        hero.add(String(38, 170, "A detailed technical, content, performance, authority,", fontSize=11, fillColor=self.PRIMARY_LIGHT))
        hero.add(String(38, 152, "and keyword opportunity report with prioritized actions.", fontSize=11, fillColor=self.PRIMARY_LIGHT))
        hero.add(String(38, 96, f"Website: {url[:64]}", fontSize=10, fillColor=colors.white, fontName='Helvetica-Bold'))
        hero.add(String(38, 72, f"Prepared: {date.today().strftime('%B %d, %Y')}", fontSize=9, fillColor=self.PRIMARY_LIGHT))
        hero.add(Circle(385, 160, 49, fillColor=None, strokeColor=self.ACCENT, strokeWidth=8))
        hero.add(String(356, 172, f"{metrics['overall']}%", fontSize=25, fillColor=colors.white, fontName='Helvetica-Bold'))
        hero.add(String(356, 148, "health score", fontSize=8.5, fillColor=self.PRIMARY_LIGHT))
        self.story.append(Spacer(1, 0.35 * inch))
        self.story.append(hero)
        self.story.append(Spacer(1, 0.35 * inch))
        self._deep_metric_row([
            ("Load Speed", f"{metrics['speed']:g}s" if metrics['speed'] else "N/A", "Target: under 2.5s", self.ACCENT),
            ("Broken Links", metrics['broken_links'], "Fix first", self.ERROR if metrics['broken_links'] else self.SUCCESS),
            ("Validation", f"{metrics['w3c_errors']} / {metrics['w3c_warnings']}", "Errors / warnings", self.WARNING if metrics['w3c_errors'] or metrics['w3c_warnings'] else self.SUCCESS),
            ("Authority", metrics['domain_authority'] if metrics['domain_authority'] is not None else "N/A", "Domain score", self.PRIMARY_MID),
        ])
        self.story.append(PageBreak())

    def _build_deep_summary(self):
        metrics = self._collect_dashboard_metrics()
        self._deep_section("Executive Overview", "The most important audit signals before the detailed section-by-section review.")
        charts = Table(
            [[self._score_bar_drawing(metrics['scores'], width=330, height=180),
              self._validation_pie_drawing(metrics['w3c_errors'], metrics['w3c_warnings'], width=195, height=160)]],
            colWidths=[4.55 * inch, 2.45 * inch]
        )
        charts.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, self.CARD_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 1, self.CARD_BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        self.story.append(charts)
        self.story.append(Spacer(1, 0.24 * inch))

        actions = self._deep_actions()
        high = sum(1 for p, _ in actions if p.lower() == 'high')
        medium = sum(1 for p, _ in actions if p.lower() == 'medium')
        low = sum(1 for p, _ in actions if p.lower() == 'low')
        self._deep_metric_row([
            ("High Priority", high, "Immediate fixes", self.ERROR),
            ("Medium Priority", medium, "Next improvements", self.WARNING),
            ("Low Priority", low, "Enhancements", self.SUCCESS),
            ("Total Actions", len(actions), "Prioritized tasks", self.PRIMARY_MID),
        ])

        rows = [['Priority', 'Recommendation']]
        rows.extend(actions[:8])
        self._deep_table(rows, [1.15 * inch, 5.85 * inch])
        self.story.append(PageBreak())

    def _build_deep_content(self):
        self._deep_section("Content Analysis", "Meta title, description, heading structure, keyword coverage, and on-page content quality.")
        self._deep_metric_row([
            ("Title Score", f"{int(self._safe_number(self.data.get('title_score')))}%", self._get_status(self.data.get('title_score', 0)), self._score_color(self.data.get('title_score', 0))),
            ("Description", f"{int(self._safe_number(self.data.get('desc_score')))}%", self._get_status(self.data.get('desc_score', 0)), self._score_color(self.data.get('desc_score', 0))),
            ("Headings", f"{int(self._safe_number(self.data.get('heading_score')))}%", self._get_status(self.data.get('heading_score', 0)), self._score_color(self.data.get('heading_score', 0))),
            ("Images Missing Alt", int(self._safe_number(self.data.get('alt_count'))), "Accessibility and image SEO", self.WARNING if self._safe_number(self.data.get('alt_count')) else self.SUCCESS),
        ])
        rows = [
            ['Element', 'Current Data', 'Audit Notes'],
            ['Meta Title', self.data.get('title', 'Not Found'), self._deep_list(self.data.get('title_issues'), self.data.get('title_verdict', 'Review title length and keyword clarity.'))],
            ['Meta Description', self.data.get('desc') or self.data.get('description', 'Not Found'), self._deep_list(self.data.get('desc_issues'), self.data.get('desc_verdict', 'Review description length and benefit clarity.'))],
            ['Primary Heading', self.data.get('heading') or self.data.get('H', 'Not Found'), self._deep_list(self.data.get('heading_issues'), self.data.get('head_verdict', 'Check H1 usage and heading hierarchy.'))],
        ]
        self._deep_table(rows, [1.55 * inch, 2.75 * inch, 2.7 * inch])

        keyword_chart = self._keyword_bar_drawing(width=460, height=175)
        if keyword_chart:
            self.story.append(keyword_chart)
            self.story.append(Spacer(1, 0.18 * inch))
        if self.data.get('lst'):
            keyword_rows = [['Keyword', 'Density', 'In Title', 'In Description', 'In Heading']]
            title = str(self.data.get('title', '')).lower()
            desc = str(self.data.get('desc') or self.data.get('comp_desc', '')).lower()
            heading = str(self.data.get('heading') or self.data.get('comp_head', '')).lower()
            for idx, kw in enumerate(self.data.get('lst', [])[:10]):
                density = self.data.get('dens', [''])[idx] if idx < len(self.data.get('dens', [])) else ''
                kw_l = str(kw).lower()
                keyword_rows.append([kw, density, 'Yes' if kw_l in title else 'No', 'Yes' if kw_l in desc else 'No', 'Yes' if kw_l in heading else 'No'])
            self._deep_table(keyword_rows, [2.0 * inch, 1.0 * inch, 1.2 * inch, 1.45 * inch, 1.35 * inch])
        self.story.append(PageBreak())

    def _build_deep_technical(self):
        self._deep_section("Crawlability and Technical SEO", "Indexing controls, structured data, validation, links, server and document signals.")
        rows = [
            ['Signal', 'Status', 'Why It Matters'],
            ['Robots.txt', self._deep_status(self.data.get('robot_flag'), 'Found', 'Missing'), 'Controls crawler access and helps avoid crawl waste.'],
            ['XML Sitemap', self._deep_status(self.data.get('sitemap_flag'), 'Found', 'Missing'), 'Helps search engines discover important URLs.'],
            ['Schema Markup', self._deep_status(self.data.get('schema_flag'), 'Implemented', 'Missing'), 'Improves rich result eligibility and entity understanding.'],
            ['Open Graph', self._deep_status(self.data.get('ogp_flag'), 'Implemented', 'Missing'), 'Improves shared link previews on social platforms.'],
            ['Favicon', self._deep_status(self.data.get('icon_flag'), 'Found', 'Missing'), 'Supports brand recognition in browsers and SERP surfaces.'],
            ['Analytics', self._deep_status(self.data.get('analytics_flag'), 'Installed', 'Not Installed'), 'Needed to measure traffic and SEO outcomes.'],
            ['Doctype', self._deep_status(self.data.get('doc_flag'), 'Found', 'Missing'), str(self.data.get('Doctype', 'Current value unavailable.'))],
            ['Encoding', self._deep_status(self.data.get('encod_flag'), 'Set', 'Not Set'), str(self.data.get('Encoding', 'Current value unavailable.'))],
        ]
        self._deep_table(rows, [1.55 * inch, 1.35 * inch, 4.1 * inch])
        self._deep_metric_row([
            ("Internal Links", int(self._safe_number(self.data.get('internal_links'))), "Navigation depth", self.PRIMARY_MID),
            ("External Links", int(self._safe_number(self.data.get('external_links'))), "Authority references", self.ACCENT),
            ("Broken Links", int(self._safe_number(self.data.get('b_links'))), "Fix quickly", self.ERROR if self._safe_number(self.data.get('b_links')) else self.SUCCESS),
            ("W3C Issues", f"{int(self._safe_number(self.data.get('error_len')))} / {int(self._safe_number(self.data.get('warn_len')))}", "Errors / warnings", self.WARNING),
        ])
        server_rows = [
            ['Server Signal', 'Value'],
            ['Server IP', self.data.get('ip', 'Not Found')],
            ['Server Location', self.data.get('loc_name', 'Not Found')],
            ['Web Server', self.data.get('webserver', 'Not Found')],
        ]
        self._deep_table(server_rows, [2.0 * inch, 5.0 * inch])
        self.story.append(PageBreak())

    def _build_deep_security_performance(self):
        self._deep_section("Security and Performance", "Trust, certificate health, HTTPS behavior, speed, and resource optimization.")
        rows = [
            ['Security Signal', 'Status / Value', 'Recommendation'],
            ['SSL Certificate', self.data.get('ssl_name', 'Not Found'), 'Keep certificate metadata valid and monitor expiry.'],
            ['SSL Organization', self.data.get('ssl_organ', 'Not Found'), 'Use trusted certificate authority details where available.'],
            ['SSL Expiry', self.data.get('ssl_expiry', 'Not Found'), 'Renew before expiry to avoid trust and crawl issues.'],
            ['HTTPS Redirect', self._deep_status(self.data.get('https'), 'Active', 'Inactive'), 'Redirect all HTTP URLs to HTTPS.'],
            ['DMCA Protection', self._deep_status(self.data.get('dmca'), 'Protected', 'Not Protected'), 'Useful for sites with original content assets.'],
        ]
        self._deep_table(rows, [1.7 * inch, 2.1 * inch, 3.2 * inch])
        perf_rows = [
            ['Performance Signal', 'Current', 'Target / Action'],
            ['Page Load Speed', f"{self.data.get('speed', 0)}s", 'Aim for under 2.5 seconds.'],
            ['CSS Minification', 'Yes' if self.data.get('css') else 'No', 'Minify and remove unused CSS.'],
            ['JavaScript Minification', 'Yes' if self.data.get('jss') else 'No', 'Minify and defer non-critical scripts.'],
            ['Optimized Plugins', 'Yes' if self.data.get('plugins') else 'No', 'Review plugin weight and unused features.'],
        ]
        self._deep_table(perf_rows, [2.0 * inch, 1.45 * inch, 3.55 * inch])
        self.story.append(PageBreak())

    def _build_deep_authority_keywords(self):
        metrics = self.data.get('metrics', {})
        keyword_ai = self.data.get('keyword_ai', {})
        if not metrics and not keyword_ai:
            return
        self._deep_section("Authority and Keyword Intelligence", "Off-page strength, semantic opportunities, search intent, and AI-assisted content recommendations.")
        if metrics:
            rows = [['Metric', 'Value', 'Interpretation']]
            for key, label in [('domain_authority', 'Domain Authority'), ('page_authority', 'Page Authority'), ('moz_rank', 'MozRank'), ('linking_root_domains', 'Linking Root Domains'), ('total_backlinks', 'Total Backlinks')]:
                if metrics.get(key) is not None:
                    interpretation = self._get_authority_rating(metrics.get(key)) if 'authority' in key else 'Review trend over time'
                    rows.append([label, metrics.get(key), interpretation])
            self._deep_table(rows, [2.2 * inch, 1.3 * inch, 3.5 * inch])
        content_stats = keyword_ai.get('content_stats', {})
        if content_stats:
            self._deep_metric_row([
                ("Word Count", content_stats.get('word_count', 0), "Depth signal", self.PRIMARY_MID),
                ("Quality Score", f"{content_stats.get('quality_score', 0)}%", "Content strength", self._score_color(content_stats.get('quality_score', 0))),
                ("Readability", f"{content_stats.get('readability_score', 0)}%", "Clarity signal", self._score_color(content_stats.get('readability_score', 0))),
                ("Intent", keyword_ai.get('search_intent', 'Informational').title(), "Primary intent", self.ACCENT),
            ])
        top_keywords = keyword_ai.get('top_keywords', [])
        if top_keywords:
            rows = [['Keyword Opportunity', 'Score', 'Priority', 'Type']]
            for item in top_keywords[:15]:
                if isinstance(item, dict):
                    rows.append([item.get('keyword', ''), item.get('relevance_score', item.get('score', 0)), str(item.get('priority', 'medium')).title(), str(item.get('keyword_type', 'suggested')).title()])
                else:
                    rows.append([str(item), 50, 'Medium', 'Suggested'])
            self._deep_table(rows, [3.1 * inch, 1.0 * inch, 1.25 * inch, 1.65 * inch])
        suggestions = keyword_ai.get('optimization_suggestions', [])
        if suggestions:
            rows = [['Impact', 'AI Recommendation']]
            for item in suggestions[:8]:
                if isinstance(item, dict):
                    rows.append([str(item.get('impact', 'Medium')).title(), item.get('suggestion', '')])
                else:
                    rows.append(['Medium', str(item)])
            self._deep_table(rows, [1.2 * inch, 5.8 * inch])
        self.story.append(PageBreak())

    def _build_deep_mobile_social(self):
        self._deep_section("Mobile and Social Readiness", "Mobile experience, AMP/rendering status, and platform presence.")
        mobile_rows = [
            ['Mobile Signal', 'Current', 'Recommendation'],
            ['Mobile Speed Score', self.data.get('mob_score', 'N/A'), 'Keep mobile load time low and reduce render-blocking resources.'],
            ['AMP', 'Enabled' if self.data.get('amp') else 'Not Enabled', 'Optional, useful for some content-heavy mobile experiences.'],
            ['Mobile Rendering', 'Working' if self.data.get('render') else 'Issues Detected', 'Test on real devices and fix layout/rendering failures.'],
            ['Mobile Preview', 'Optimized' if self.data.get('mobpreview') else 'Needs Work', 'Improve SERP preview clarity for mobile users.'],
        ]
        self._deep_table(mobile_rows, [1.8 * inch, 1.55 * inch, 3.65 * inch])
        social_rows = [
            ['Platform', 'Status', 'Action'],
            ['Facebook', 'Connected' if self.data.get('facebook_flag') else 'Missing', 'Add or verify official brand link.'],
            ['Instagram', 'Connected' if self.data.get('instagram_flag') else 'Missing', 'Add or verify official brand link.'],
            ['Twitter / X', 'Connected' if self.data.get('twitter_flag') else 'Missing', 'Add or verify official brand link.'],
            ['LinkedIn', 'Connected' if self.data.get('linkedin_flag') else 'Missing', 'Add or verify official brand link.'],
        ]
        self._deep_table(social_rows, [1.45 * inch, 1.45 * inch, 4.1 * inch])
        self.story.append(PageBreak())

    def _build_deep_action_plan(self):
        self._deep_section("Prioritized SEO Action Plan", "Recommended implementation order based on likely impact and urgency.")
        rows = [['Priority', 'Action Item']]
        rows.extend(self._deep_actions())
        self._deep_table(rows, [1.15 * inch, 5.85 * inch])
        closing = Table(
            [[Paragraph("<b>Implementation Note</b>", self.styles['CardTitle'])],
             [Paragraph("Start with High priority technical blockers, then move into content and authority improvements. Re-run the audit after changes to confirm progress and catch regressions.", self.styles['MyBodyText'])]],
            colWidths=[7.0 * inch]
        )
        closing.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.SOFT_BLUE),
            ('BOX', (0, 0), (-1, -1), 1, self.CARD_BORDER),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        self.story.append(closing)

    def _score_item(self, label, value):
        score = int(max(0, min(100, self._safe_number(value))))
        return {
            'label': label,
            'score': score,
            'status': self._get_status(score),
            'class': 'good' if score >= 70 else 'fair' if score >= 50 else 'poor',
        }

    def _html_metric_cards(self):
        metrics = self._collect_dashboard_metrics()
        return [
            {'label': 'Overall Score', 'value': f"{metrics['overall']}%", 'note': self._get_status(metrics['overall']), 'tone': 'blue'},
            {'label': 'Load Speed', 'value': f"{metrics['speed']:g}s" if metrics['speed'] else 'N/A', 'note': 'Target under 2.5s', 'tone': 'cyan'},
            {'label': 'Broken Links', 'value': metrics['broken_links'], 'note': 'Fix first', 'tone': 'red' if metrics['broken_links'] else 'green'},
            {'label': 'Validation', 'value': f"{metrics['w3c_errors']} / {metrics['w3c_warnings']}", 'note': 'Errors / warnings', 'tone': 'amber'},
            {'label': 'Authority', 'value': metrics['domain_authority'] if metrics['domain_authority'] is not None else 'N/A', 'note': 'Domain score', 'tone': 'blue'},
        ]

    def _html_keyword_rows(self):
        title = str(self.data.get('title', '')).lower()
        desc = str(self.data.get('desc') or self.data.get('comp_desc', '')).lower()
        heading = str(self.data.get('heading') or self.data.get('comp_head', '')).lower()
        densities = self.data.get('dens', [])
        rows = []
        max_density = 1
        parsed = []
        for idx, kw in enumerate(self.data.get('lst', [])[:12]):
            density = densities[idx] if idx < len(densities) else ''
            numeric = self._safe_number(str(density).replace('%', ''))
            max_density = max(max_density, numeric)
            parsed.append((kw, density, numeric))

        for kw, density, numeric in parsed:
            kw_l = str(kw).lower()
            rows.append({
                'keyword': kw,
                'density': density,
                'density_value': numeric,
                'bar_width': round((numeric / max_density) * 100, 1) if max_density else 0,
                'in_title': kw_l in title,
                'in_description': kw_l in desc,
                'in_heading': kw_l in heading,
            })
        return rows

    def _html_keyword_opportunities(self):
        keyword_ai = self.data.get('keyword_ai', {})
        opportunities = []
        for item in keyword_ai.get('top_keywords', [])[:15]:
            if isinstance(item, dict):
                opportunities.append({
                    'keyword': item.get('keyword', ''),
                    'score': int(self._safe_number(item.get('relevance_score', item.get('score', 0)))),
                    'priority': str(item.get('priority', 'medium')).title(),
                    'type': str(item.get('keyword_type', 'suggested')).title(),
                })
            else:
                opportunities.append({'keyword': str(item), 'score': 50, 'priority': 'Medium', 'type': 'Suggested'})
        return opportunities

    def _html_platforms(self):
        return [
            ('Facebook', self.data.get('facebook_flag')),
            ('Instagram', self.data.get('instagram_flag')),
            ('Twitter / X', self.data.get('twitter_flag')),
            ('LinkedIn', self.data.get('linkedin_flag')),
        ]

    def _html_issue_text(self, key, fallback):
        value = self.data.get(key)
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value[:6]]
        if value:
            return [str(value)]
        return [fallback]

    def _build_html_context(self):
        metrics = self._collect_dashboard_metrics()
        keyword_ai = self.data.get('keyword_ai', {})
        content_stats = keyword_ai.get('content_stats', {})
        scores = [
            self._score_item('Meta Title', self.data.get('title_score', 0)),
            self._score_item('Meta Description', self.data.get('desc_score', 0)),
            self._score_item('Heading Structure', self.data.get('heading_score', 0)),
            self._score_item('Social Presence', self.data.get('s_count', 0)),
        ]
        if content_stats.get('quality_score'):
            scores.append(self._score_item('AI Content Quality', content_stats.get('quality_score')))
        if self.data.get('mob_score'):
            scores.append(self._score_item('Mobile Readiness', min(100, self._safe_number(self.data.get('mob_score')))))

        return {
            'report': {
                'url': self.data.get('url', 'N/A'),
                'date': date.today().strftime('%B %d, %Y'),
                'overall': metrics['overall'],
                'overall_status': self._get_status(metrics['overall']),
            },
            'cards': self._html_metric_cards(),
            'scores': scores,
            'actions': [{'priority': p, 'text': a} for p, a in self._deep_actions()],
            'content': {
                'title': self.data.get('title', 'Not Found'),
                'description': self.data.get('desc') or self.data.get('description', 'Not Found'),
                'heading': self.data.get('heading') or self.data.get('H', 'Not Found'),
                'title_issues': self._html_issue_text('title_issues', self.data.get('title_verdict', 'Review title quality.')),
                'desc_issues': self._html_issue_text('desc_issues', self.data.get('desc_verdict', 'Review description quality.')),
                'heading_issues': self._html_issue_text('heading_issues', self.data.get('head_verdict', 'Review heading hierarchy.')),
                'alt_count': int(self._safe_number(self.data.get('alt_count'))),
            },
            'keywords': self._html_keyword_rows(),
            'technical': [
                ('Robots.txt', self._deep_status(self.data.get('robot_flag'), 'Found', 'Missing'), 'Controls crawler access and crawl waste.'),
                ('XML Sitemap', self._deep_status(self.data.get('sitemap_flag'), 'Found', 'Missing'), 'Helps search engines discover important URLs.'),
                ('Schema Markup', self._deep_status(self.data.get('schema_flag'), 'Implemented', 'Missing'), 'Supports rich results and entity clarity.'),
                ('Open Graph', self._deep_status(self.data.get('ogp_flag'), 'Implemented', 'Missing'), 'Improves social sharing previews.'),
                ('Favicon', self._deep_status(self.data.get('icon_flag'), 'Found', 'Missing'), 'Supports brand recognition.'),
                ('Analytics', self._deep_status(self.data.get('analytics_flag'), 'Installed', 'Not Installed'), 'Measures traffic and SEO outcomes.'),
                ('Doctype', self._deep_status(self.data.get('doc_flag'), 'Found', 'Missing'), str(self.data.get('Doctype', 'Current value unavailable.'))),
                ('Encoding', self._deep_status(self.data.get('encod_flag'), 'Set', 'Not Set'), str(self.data.get('Encoding', 'Current value unavailable.'))),
            ],
            'server': {
                'ip': self.data.get('ip', 'Not Found'),
                'location': self.data.get('loc_name', 'Not Found'),
                'webserver': self.data.get('webserver', 'Not Found'),
                'internal_links': int(self._safe_number(self.data.get('internal_links'))),
                'external_links': int(self._safe_number(self.data.get('external_links'))),
                'broken_links': int(self._safe_number(self.data.get('b_links'))),
                'errors': int(self._safe_number(self.data.get('error_len'))),
                'warnings': int(self._safe_number(self.data.get('warn_len'))),
            },
            'security': [
                ('SSL Certificate', self.data.get('ssl_name', 'Not Found'), 'Keep certificate metadata valid.'),
                ('SSL Organization', self.data.get('ssl_organ', 'Not Found'), 'Use trusted certificate authority details where available.'),
                ('SSL Expiry', self.data.get('ssl_expiry', 'Not Found'), 'Renew before expiry.'),
                ('HTTPS Redirect', self._deep_status(self.data.get('https'), 'Active', 'Inactive'), 'Redirect all HTTP URLs to HTTPS.'),
                ('DMCA Protection', self._deep_status(self.data.get('dmca'), 'Protected', 'Not Protected'), 'Useful for original content assets.'),
            ],
            'performance': [
                ('Page Load Speed', f"{self.data.get('speed', 0)}s", 'Aim for under 2.5 seconds.'),
                ('CSS Minification', 'Yes' if self.data.get('css') else 'No', 'Minify and remove unused CSS.'),
                ('JavaScript Minification', 'Yes' if self.data.get('jss') else 'No', 'Minify and defer non-critical scripts.'),
                ('Optimized Plugins', 'Yes' if self.data.get('plugins') else 'No', 'Review plugin weight and unused features.'),
            ],
            'metrics': self.data.get('metrics', {}),
            'content_stats': content_stats,
            'keyword_ai': keyword_ai,
            'keyword_opportunities': self._html_keyword_opportunities(),
            'platforms': [{'name': name, 'connected': bool(flag)} for name, flag in self._html_platforms()],
            'mobile': [
                ('Mobile Speed Score', self.data.get('mob_score', 'N/A'), 'Keep mobile load time low.'),
                ('AMP', 'Enabled' if self.data.get('amp') else 'Not Enabled', 'Optional for some content-heavy pages.'),
                ('Mobile Rendering', 'Working' if self.data.get('render') else 'Issues Detected', 'Test on real devices.'),
                ('Mobile Preview', 'Optimized' if self.data.get('mobpreview') else 'Needs Work', 'Improve mobile SERP clarity.'),
            ],
        }

    def _find_browser_executable(self):
        """Find a Chromium-based browser that can print HTML to PDF."""
        candidates = [
            os.environ.get('CHROME_PATH'),
            os.environ.get('EDGE_PATH'),
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    def _project_base_dir(self):
        """Return the Django project base directory with a safe local fallback."""
        try:
            return str(settings.BASE_DIR)
        except Exception:
            return str(Path(__file__).resolve().parent.parent)

    def _print_html_with_browser(self, html_path):
        """Use installed Chrome/Edge to print the rendered HTML report to PDF."""
        browser = self._find_browser_executable()
        if not browser:
            raise RuntimeError("No Chrome or Edge executable found for HTML PDF rendering.")

        cmd = [
            browser,
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--run-all-compositor-stages-before-draw',
            '--virtual-time-budget=1000',
            '--print-to-pdf-no-header',
            '--no-pdf-header-footer',
            f'--print-to-pdf={os.path.abspath(self.filepath)}',
            Path(html_path).resolve().as_uri(),
        ]
        completed = subprocess.run(
            cmd,
            cwd=self.output_dir,
            capture_output=True,
            text=True,
            timeout=45
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "Browser PDF rendering failed.").strip())
        if not os.path.exists(self.filepath) or os.path.getsize(self.filepath) == 0:
            raise RuntimeError("Browser PDF renderer did not create a PDF file.")
        return self.filepath

    def _generate_html_pdf(self):
        """Render the SEO report as themed HTML and save it as PDF."""
        context = self._build_html_context()
        base_dir = self._project_base_dir()
        css_path = os.path.join(base_dir, 'SEOAnalyzer', 'static', 'reports', 'seo-deep-audit-report.css')
        if os.path.exists(css_path):
            context['css_file_url'] = Path(css_path).resolve().as_uri()
        html = render_to_string('reports/seo_deep_audit_report.html', context)
        html_path = os.path.join(self.output_dir, self.filename.replace('.pdf', '.html'))
        with open(html_path, 'w', encoding='utf-8') as handle:
            handle.write(html)

        try:
            return self._print_html_with_browser(html_path)
        except Exception as browser_error:
            logger.warning(f"Browser HTML PDF generation failed: {browser_error}")

        try:
            from weasyprint import HTML, CSS
        except Exception as exc:
            raise RuntimeError(f"No HTML PDF renderer is available: {exc}")

        stylesheets = [CSS(filename=css_path)] if os.path.exists(css_path) else []
        HTML(string=html, base_url=base_dir).write_pdf(self.filepath, stylesheets=stylesheets)
        return self.filepath
    
    
    def     generate(self):
        """
        Generate the complete SEO deep audit PDF report
        
        Returns:
            str: Path to generated PDF file
        """
        try:
            # Ensure output directory exists
            os.makedirs(self.output_dir, exist_ok=True)

            try:
                pdf_path = self._generate_html_pdf()
                logger.info(f"HTML SEO Deep Audit PDF generated: {pdf_path}")
                print(f"HTML SEO Deep Audit PDF generated: {pdf_path}")
                return pdf_path
            except Exception as html_error:
                logger.warning(f"HTML PDF generation failed, falling back to ReportLab: {html_error}")
            
            # Create PDF document
            doc = SimpleDocTemplate(
                self.filepath,
                pagesize=letter,
                rightMargin=0.55*inch,
                leftMargin=0.55*inch,
                topMargin=0.7*inch,
                bottomMargin=0.65*inch
            )
            
            # Build the deep audit report from scratch.
            self.story = []
            self._build_deep_cover()
            self._build_deep_summary()
            self._build_deep_content()
            self._build_deep_technical()
            self._build_deep_security_performance()
            self._build_deep_authority_keywords()
            self._build_deep_mobile_social()
            self._build_deep_action_plan()
            
            # Build PDF
            doc.build(self.story, onFirstPage=self._deep_header_footer, onLaterPages=self._deep_header_footer)
            
            logger.info(f"Comprehensive PDF Report generated: {self.filepath}")
            print(f"Comprehensive PDF Report generated: {self.filepath}")
            return self.filepath
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise
    
    def send_email(self, sender_email, sender_password):
        """
        Send the PDF report via email
        
        Args:
            sender_email: Sender's email address
            sender_password: Sender's email password or app password
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if not os.path.exists(self.filepath):
            return {
                'success': False,
                'message': f"Report file {self.filepath} not found"
            }
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = self.user_email
            msg['Subject'] = f"WEB LIFT SEO Audit Report - {date.today().strftime('%B %d, %Y')}"
            
            # Email body
            body = f"""Dear Valued Customer,

Thank you for using WEB LIFT for your SEO audit needs.

Please find attached your comprehensive SEO audit report for:
{self.data.get('url', 'your website')}

This comprehensive report includes:
- Website Audit (Titles, Meta, Headings, Speed)
- SEO Metrics (Domain Authority, Page Authority, Backlinks via Moz)
- AI-Powered Keyword Suggestions & Semantic Analysis
- Technical SEO Assessment
- Security Evaluation
- Performance Metrics
- Social Media Presence
- Mobile Usability Analysis
- Prioritized Action Plan

If you have any questions or need assistance implementing the recommendations,
please don't hesitate to contact us.

Best regards,
WEB LIFT Team
Professional SEO Audit Services
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            with open(self.filepath, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={os.path.basename(self.filepath)}'
            )
            msg.attach(part)
            
            # Send email
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {self.user_email}")
            print(f"Email sent successfully to {self.user_email}")
            return {
                'success': True,
                'message': f"Email sent successfully to {self.user_email}"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = "Email authentication failed. Check credentials."
            logger.error(f"{error_msg} - {str(e)}")
            return {
                'success': False,
                'message': error_msg
            }
            
        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }


def generate_seo_report(data_dict, user_email, sender_email, sender_password, output_dir=None, send_email=True):
    """
    Main function to generate and optionally send SEO report
    
    Args:
        data_dict: Dictionary containing all SEO audit data
        user_email: Recipient email address
        sender_email: Sender email address  
        sender_password: Sender email password
        output_dir: Optional output directory (default: current directory)
        send_email: Whether to send email (default: True)
    
    Returns:
        dict: {
            'success': bool,
            'pdf_path': str or None,
            'email_sent': bool,
            'message': str
        }
    """
    result = {
        'success': False,
        'pdf_path': None,
        'email_sent': False,
        'message': ''
    }
    
    try:
        # Validate required data
        if not data_dict:
            result['message'] = "Error: data_dict is required"
            return result
        
        if not data_dict.get('url'):
            result['message'] = "Error: 'url' field is required in data_dict"
            return result
        
        # Generate PDF
        logger.info(f"Starting report generation for: {data_dict.get('url')}")
        report = ModernPDFReport(data_dict, user_email, output_dir=output_dir)
        pdf_path = report.generate()
        
        result['pdf_path'] = pdf_path
        result['success'] = True
        result['message'] = f"Report generated successfully: {pdf_path}"
        
        # Send email if requested and credentials provided
        if send_email and user_email and sender_email and sender_password:
            logger.info(f"Sending email to: {user_email}")
            email_result = report.send_email(sender_email, sender_password)
            result['email_sent'] = email_result['success']
            
            if email_result['success']:
                result['message'] += f" | {email_result['message']}"
            else:
                result['message'] += f" | Email failed: {email_result['message']}"
        elif send_email:
            result['message'] += " | Email not sent (missing credentials or user email)"
        
        logger.info(f"Report generation completed: {result['message']}")
        return result
        
    except Exception as e:
        error_msg = f"Error generating report: {str(e)}"
        logger.error(error_msg)
        result['message'] = error_msg
        return result



    
