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
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from datetime import date
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import logging

# Setup logging
logger = logging.getLogger(__name__)


class ModernPDFReport:
    """
    Modern PDF Report Generator for WEB LIFT SEO Audit
    
    Brand Colors:
    - Primary Dark: #023761
    - Primary Mid: #02569b
    - Primary Light: #80aacd
    """
    
    # Brand Colors (RGB format for ReportLab)
    PRIMARY_DARK = colors.HexColor('#023761')
    PRIMARY_MID = colors.HexColor('#02569b')
    PRIMARY_LIGHT = colors.HexColor('#80aacd')
    SUCCESS = colors.HexColor('#10b981')
    WARNING = colors.HexColor('#f59e0b')
    ERROR = colors.HexColor('#ef4444')
    GRAY_50 = colors.HexColor('#f9fafb')
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
            textColor=self.PRIMARY_DARK,
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
            backColor=self.GRAY_50
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
    
    def _create_cover_page(self):
        """Create elegant cover page"""
        # Logo/Title
        title = Paragraph("WEB LIFT", self.styles['MainTitle'])
        self.story.append(Spacer(1, 1*inch))
        self.story.append(title)
        
        subtitle = Paragraph(
            "Professional SEO Audit Report",
            ParagraphStyle(
                name='Subtitle',
                parent=self.styles['Normal'],
                fontSize=20,
                textColor=self.PRIMARY_MID,
                alignment=TA_CENTER,
                spaceAfter=30
            )
        )
        self.story.append(subtitle)
        self.story.append(Spacer(1, 0.5*inch))
        
        # Website URL
        url_style = ParagraphStyle(
            name='URLStyle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=self.PRIMARY_MID,
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        url_label = Paragraph("Website Analyzed:", url_style)
        self.story.append(url_label)
        
        url_value = Paragraph(
            f"<b>{self.data.get('url', 'N/A')}</b>",
            ParagraphStyle(
                name='URLValue',
                parent=self.styles['Normal'],
                fontSize=16,
                textColor=self.PRIMARY_DARK,
                alignment=TA_CENTER,
                spaceAfter=30
            )
        )
        self.story.append(url_value)
        
        # Summary Scores Box
        self._create_summary_scores()
        
        self.story.append(PageBreak())
    
    def _create_summary_scores(self):
        """Create summary scores overview on cover page with comprehensive metrics"""
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
            ['Website Speed', f"{speed}s", '✓ Good' if speed and speed < 2.5 else '⚠ Slow'],
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
            return "✓ Good"
        elif score >= 50:
            return "⚠ Fair"
        else:
            return "✗ Needs Work"
    
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
            f"<b>📋 Recommendation:</b> {recommendation}",
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
                '✓' if kw_lower in title else '✗',
                '✓' if kw_lower in desc else '✗',
                '✓' if kw_lower in heading else '✗'
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
                '✓ Found' if self.data.get('robot_flag') else '✗ Not Found',
                'Essential for controlling search engine crawling'
            ],
            [
                'XML Sitemap',
                '✓ Found' if self.data.get('sitemap_flag') else '✗ Not Found',
                'Helps search engines discover all pages'
            ],
            [
                'Schema Markup',
                '✓ Implemented' if self.data.get('schema_flag') else '✗ Missing',
                'Improves search result display with rich snippets'
            ],
            [
                'Open Graph Protocol',
                '✓ Implemented' if self.data.get('ogp_flag') else '✗ Missing',
                'Optimizes social media sharing appearance'
            ],
            [
                'Favicon',
                '✓ Found' if self.data.get('icon_flag') else '✗ Not Found',
                'Improves brand recognition in browser tabs'
            ],
            [
                'Google Analytics',
                '✓ Installed' if self.data.get('analytics_flag') else '✗ Not Installed',
                'Essential for tracking website performance'
            ],
            [
                'DocType Declaration',
                '✓ Found' if self.data.get('doc_flag') else '✗ Missing',
                f"Current: {self.data.get('Doctype', 'N/A')}"
            ],
            [
                'Character Encoding',
                '✓ Set' if self.data.get('encod_flag') else '✗ Not Set',
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
                f"<b>⚠ Critical:</b> {broken_count} broken link(s) detected. Fix immediately to avoid SEO penalties and poor user experience.",
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
            ['HTTPS Redirect', '✓ Active' if self.data.get('https') else '✗ Inactive'],
            ['DMCA Protection', '✓ Protected' if self.data.get('dmca') else '✗ Not Protected'],
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
            "<b>🔒 Security Recommendations:</b><br/>"
            "• Ensure SSL certificate is always up to date<br/>"
            "• Implement HTTPS redirection for all pages<br/>"
            "• Consider DMCA protection for content security<br/>"
            "• Regular security audits recommended",
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
                '✓' if self.data.get('speed', 99) < 2.5 else '✗'
            ],
            [
                'CSS Minification',
                '✓ Yes' if self.data.get('css') else '✗ No',
                'Yes',
                '✓' if self.data.get('css') else '✗'
            ],
            [
                'JS Minification',
                '✓ Yes' if self.data.get('jss') else '✗ No',
                'Yes',
                '✓' if self.data.get('jss') else '✗'
            ],
            [
                'Optimized Plugins',
                '✓ Yes' if self.data.get('plugins') else '✗ No',
                'Yes',
                '✓' if self.data.get('plugins') else '✗'
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
            "<b>⚡ Performance Recommendations:</b><br/>"
            "• Optimize and compress images (WebP format recommended)<br/>"
            "• Enable browser caching and GZIP compression<br/>"
            "• Minimize HTTP requests by combining files<br/>"
            "• Use a Content Delivery Network (CDN)<br/>"
            "• Defer loading of non-critical JavaScript",
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
            ['Facebook', '✓' if self.data.get('facebook_flag') else '✗', 'Yes' if self.data.get('facebook_flag') else 'No'],
            ['Instagram', '✓' if self.data.get('instagram_flag') else '✗', 'Yes' if self.data.get('instagram_flag') else 'No'],
            ['Twitter', '✓' if self.data.get('twitter_flag') else '✗', 'Yes' if self.data.get('twitter_flag') else 'No'],
            ['LinkedIn', '✓' if self.data.get('linkedin_flag') else '✗', 'Yes' if self.data.get('linkedin_flag') else 'No'],
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
            "<b>📱 Social Media Recommendations:</b><br/>"
            "• Add social media links to increase brand visibility<br/>"
            "• Regular posting increases engagement and SEO benefits<br/>"
            "• Use social media for content distribution<br/>"
            "• Monitor social signals for brand reputation",
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
                '✓ Good' if self.data.get('mob_score', 99) < 3 else '✗ Needs Work'
            ],
            [
                'AMP (Accelerated Mobile Pages)',
                '✓ Enabled' if self.data.get('amp') else '✗ Not Enabled',
                'Recommended for faster mobile loading'
            ],
            [
                'Mobile Rendering',
                '✓ Working' if self.data.get('render') else '✗ Issues Detected',
                'Essential for mobile user experience'
            ],
            [
                'Mobile Preview Optimized',
                '✓ Yes' if self.data.get('mobpreview') else '✗ No',
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
                "<b>⚠ Mobile Speed Needs Improvement:</b><br/>"
                "• Reduce image sizes and use modern formats (WebP)<br/>"
                "• Minimize render-blocking resources<br/>"
                "• Enable text compression<br/>"
                "• Consider implementing AMP for faster mobile pages<br/>"
                "• Test on real mobile devices regularly",
                ParagraphStyle(
                    name='MobileWarning',
                    parent=self.styles['BodyText'],
                    textColor=self.ERROR
                )
            )
        else:
            rec_text = Paragraph(
                "<b>✓ Mobile Performance is Good:</b><br/>"
                "• Continue monitoring mobile performance<br/>"
                "• Test on various devices and screen sizes<br/>"
                "• Keep mobile-first design principles<br/>"
                "• Regularly update mobile optimization",
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
                "✓ Excellent! Your website has no critical issues. Continue monitoring and maintaining current standards.",
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
                auth_data.append(['MozRank', f"{moz_rank}", '✓ Good' if moz_rank >= 5 else '⚠ Fair'])
            
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
                    "<b>⚠ Backlink Strategy Needed:</b> Your site has few referring domains. "
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
                content_data.append(['Word Count', f"{word_count}", '✓' if word_count >= 300 else '⚠'])
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
                    "<b>⚠ Content Quality Improvements:</b><br/>"
                    "• Expand content with more comprehensive information<br/>"
                    "• Use proper heading structure (H1, H2, H3)<br/>"
                    "• Include relevant keywords naturally<br/>"
                    "• Add internal and external links<br/>"
                    "• Improve readability with shorter paragraphs",
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
                        f"<b>🤖 AI Insight:</b> {reasoning[:200]}...",
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
                    f"• <b>[{impact.upper()}]</b> {suggestion[:150]}",
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
                return '✓ Strong'
            elif score >= 30:
                return '⚠ Moderate'
            else:
                return '✗ Weak'
        except (ValueError, TypeError):
            return 'N/A'
    
    
    def     generate(self):
        """
        Generate the complete comprehensive PDF report
        
        Returns:
            str: Path to generated PDF file
        """
        try:
            # Ensure output directory exists
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Create PDF document
            doc = SimpleDocTemplate(
                self.filepath,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )
            
            # Build all sections
            self._create_cover_page()
            self._create_content_analysis()
            self._create_technical_analysis()
            self._create_security_analysis()
            self._create_performance_analysis()
            self._create_seo_metrics()  # NEW: Authority & Technical scores
            self._create_semantic_analysis()  # NEW: E-E-A-T & Content Quality
            self._create_keyword_suggestions()  # NEW: AI-Powered keywords
            self._create_mobile_analysis()
            self._create_social_analysis()
            self._create_action_plan()
            
            # Build PDF
            doc.build(self.story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
            
            logger.info(f"✓ Comprehensive PDF Report generated: {self.filepath}")
            print(f"✓ Comprehensive PDF Report generated: {self.filepath}")
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
• Website Audit (Titles, Meta, Headings, Speed)
• SEO Metrics (Domain Authority, Page Authority, Backlinks via Moz)
• AI-Powered Keyword Suggestions & Semantic Analysis
• Technical SEO Assessment
• Security Evaluation
• Performance Metrics
• Social Media Presence
• Mobile Usability Analysis
• Prioritized Action Plan

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
            
            logger.info(f"✓ Email sent successfully to {self.user_email}")
            print(f"✓ Email sent successfully to {self.user_email}")
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



    