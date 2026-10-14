"""
Report Generator for Local Skill & Job Exchange Platform.
Supports PDF (via ReportLab) and CSV exports for the 4 institutional report types:
1. User Activity Reports
2. Skill Demand Reports
3. System Usage Statistics
4. Admin Summary Reports
Community Engineering Project (BIT42304) - TGPCET Nagpur
"""

import csv
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def get_report_data(conn, report_type):
    """Fetch structured data for the given report type."""
    cursor = conn.cursor()

    if report_type == 'user_activity':
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.role, u.neighborhood, u.rating, u.status, u.created_at,
                   (SELECT COUNT(*) FROM skills WHERE user_id = u.id) as total_skills,
                   (SELECT COUNT(*) FROM jobs WHERE user_id = u.id) as total_jobs_posted
            FROM users u
            ORDER BY u.created_at DESC;
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        summary = {
            'total_users': len(rows),
            'providers': sum(1 for r in rows if r['role'] in ['provider', 'both']),
            'requesters': sum(1 for r in rows if r['role'] in ['requester', 'both']),
            'active_users': sum(1 for r in rows if r['status'] == 'active'),
        }
        return {'title': 'User Activity Report', 'rows': rows, 'summary': summary}

    elif report_type == 'skill_demand':
        cursor.execute("""
            SELECT j.category, 
                   COUNT(j.id) as jobs_posted,
                   AVG(j.budget) as avg_budget,
                   (SELECT COUNT(*) FROM skills WHERE category = j.category) as available_providers
            FROM jobs j
            GROUP BY j.category
            ORDER BY jobs_posted DESC;
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        for r in rows:
            r['avg_budget'] = round(r['avg_budget'] or 0, 2)
            posted = r['jobs_posted']
            providers = r['available_providers']
            r['gap_ratio'] = round((posted / max(providers, 1)), 2)
            r['demand_level'] = 'High' if posted > providers else ('Balanced' if posted == providers else 'Saturated')

        return {'title': 'Skill Demand & Supply Gap Report', 'rows': rows, 'summary': {'categories_tracked': len(rows)}}

    elif report_type == 'system_usage':
        cursor.execute("SELECT COUNT(*) as cnt FROM users;")
        total_users = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM skills;")
        total_skills = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM jobs;")
        total_jobs = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'completed';")
        completed_jobs = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM messages;")
        total_messages = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM reviews;")
        total_reviews = cursor.fetchone()['cnt']
        cursor.execute("SELECT AVG(rating) as avg_r FROM reviews;")
        avg_platform_rating = round(cursor.fetchone()['avg_r'] or 4.8, 2)

        # Recent activities
        cursor.execute("""
            SELECT l.action, l.details, l.created_at, u.name as user_name
            FROM activity_logs l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT 15;
        """)
        logs = [dict(r) for r in cursor.fetchall()]

        summary = {
            'total_users': total_users,
            'total_skills': total_skills,
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'resolution_rate': f"{round((completed_jobs / max(total_jobs, 1)) * 100, 1)}%",
            'total_messages': total_messages,
            'total_reviews': total_reviews,
            'avg_rating': avg_platform_rating
        }
        return {'title': 'System Usage Statistics Report', 'rows': logs, 'summary': summary}

    elif report_type == 'admin_summary':
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role != 'admin';")
        community_members = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'open';")
        open_jobs = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'completed';")
        completed_jobs = cursor.fetchone()['cnt']
        cursor.execute("SELECT SUM(budget) as total_val FROM jobs WHERE status = 'completed';")
        total_economy_value = round(cursor.fetchone()['total_val'] or 0.0, 2)

        cursor.execute("""
            SELECT neighborhood, COUNT(*) as jobs_count
            FROM jobs
            GROUP BY neighborhood
            ORDER BY jobs_count DESC
            LIMIT 5;
        """)
        top_neighborhoods = [dict(r) for r in cursor.fetchall()]

        summary = {
            'community_members': community_members,
            'open_opportunities': open_jobs,
            'successful_exchanges': completed_jobs,
            'estimated_economy_generated': f"INR {total_economy_value:,.2f}",
            'top_neighborhoods': top_neighborhoods
        }
        return {'title': 'Executive Admin Summary Report', 'rows': top_neighborhoods, 'summary': summary}

    raise ValueError(f"Unknown report type: {report_type}")


def generate_csv_report(conn, report_type):
    """Generate CSV text output for a given report type."""
    data = get_report_data(conn, report_type)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([f"# {data['title']}"])
    writer.writerow([f"# Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([f"# Institution: TGPCET - Information Technology Department"])
    writer.writerow([])

    if data['rows']:
        headers = list(data['rows'][0].keys())
        writer.writerow(headers)
        for row in data['rows']:
            writer.writerow([row.get(h, '') for h in headers])

    return output.getvalue()


def generate_pdf_report(conn, report_type):
    """Generate high quality institutional PDF report using ReportLab."""
    data = get_report_data(conn, report_type)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#1A365D")   # Deep navy
    accent_color = colors.HexColor("#2B6CB0")    # Blue
    text_dark = colors.HexColor("#2D3748")       # Charcoal

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=accent_color,
        spaceAfter=12
    )

    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=6
    )

    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=text_dark
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=text_dark
    )

    story = []

    # Header / Institution Branding
    story.append(Paragraph("TULSIRAMJI GAIKWAD-PATIL COLLEGE OF ENGINEERING & TECHNOLOGY", subtitle_style))
    story.append(Paragraph("Department of Information Technology • Community Engineering Project (BIT42304)", normal_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))
    
    # Report Title
    story.append(Paragraph(f"LOCAL SKILL & JOB EXCHANGE PLATFORM: {data['title'].upper()}", title_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y - %I:%M %p')} | System Report", normal_style))
    story.append(Spacer(1, 10))

    # Summary KPI Box
    if 'summary' in data and data['summary']:
        story.append(Paragraph("Executive Summary & Platform Metrics", section_style))
        summary_items = []
        for k, v in data['summary'].items():
            if not isinstance(v, list):
                label = k.replace('_', ' ').title()
                summary_items.append(f"<b>{label}:</b> {v}")
        
        # Grid format for KPIs
        kpi_text = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(summary_items)
        story.append(Paragraph(kpi_text, normal_style))
        story.append(Spacer(1, 12))

    # Data Table
    story.append(Paragraph("Detailed Records & Analysis", section_style))
    
    if data['rows']:
        headers = list(data['rows'][0].keys())
        # Filter headers for neat presentation
        display_headers = [h.replace('_', ' ').title() for h in headers]
        
        table_data = [[Paragraph(dh, table_header_style) for dh in display_headers]]
        
        for r in data['rows'][:40]:  # limit to top 40 for clean PDF page fit
            row_cells = []
            for h in headers:
                val = str(r.get(h, ''))
                # truncate very long text
                if len(val) > 40:
                    val = val[:37] + "..."
                row_cells.append(Paragraph(val, table_cell_style))
            table_data.append(row_cells)

        t = Table(table_data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No activity records available for this reporting period.", normal_style))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E0"), spaceAfter=6))
    story.append(Paragraph("Local Skill & Job Exchange Platform • TGPCET Community Project • Confidential & Proprietary Report", normal_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
