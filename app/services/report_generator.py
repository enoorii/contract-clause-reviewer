from typing import Any


def generate_report_html(analysis_data: dict[str, Any]) -> str:
    # Use .get() to avoid KeyError
    title = analysis_data.get("title", "Contract Analysis Report")
    document_summary = analysis_data.get("document_summary", "")
    document_type = analysis_data.get("document_type", "")
    overall_risk_score = analysis_data.get("overall_risk_score", 0)
    recommendations = analysis_data.get("recommendations", [])
    clauses = analysis_data.get("clauses", [])
    created_at = analysis_data.get("created_at")
    if created_at:
        created_at = (
            created_at.strftime("%Y-%m-%d %H:%M")
            if hasattr(created_at, "strftime")
            else str(created_at)
        )

    risk_colors = {
        "low": "#28a745",
        "average": "#ffc107",
        "high": "#fd7e14",
        "critical": "#dc3545",
    }

    # Build clauses table rows (handle empty list)
    if not clauses:
        clauses_rows = "<tr><td colspan='5' style='text-align:center;'>No clauses available.</td></tr>"
    else:
        clauses_rows = ""
        for clause in clauses:
            risk_level = clause.get("risk_level", "average").lower()
            color = risk_colors.get(risk_level, "#6c757d")
            key_terms = ", ".join(clause.get("key_terms", []))
            suggested_actions = "<br>".join(clause.get("suggested_actions", []))
            clauses_rows += f"""
            <tr>
                <td>{clause.get("clause_type", "")}</td>
                <td>{clause.get("summary", "")}</td>
                <td style="background-color:{color}; color:white; text-align:center;">{risk_level.capitalize()}</td>
                <td>{key_terms}</td>
                <td>{suggested_actions}</td>
            </tr>
            """

    # Recommendations list
    rec_items = "".join(f"<li>{rec}</li>" for rec in recommendations)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #6c757d;
            }}
        }}
        body {{
            font-family: 'Helvetica', 'Arial', sans-serif;
            line-height: 1.6;
            color: #212529;
        }}
        h1, h2, h3 {{
            color: #1a1a2e;
        }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid #0d6efd;
            padding-bottom: 10px;
        }}
        .meta {{
            text-align: center;
            margin-bottom: 20px;
            color: #6c757d;
            font-size: 12pt;
        }}
        .score-box {{
            background: #f8f9fa;
            border-left: 5px solid #0d6efd;
            padding: 10px 15px;
            margin: 20px 0;
        }}
        .score-value {{
            font-size: 24pt;
            font-weight: bold;
            color: #0d6efd;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 10pt;
        }}
        th {{
            background: #e9ecef;
            border: 1px solid #dee2e6;
            padding: 8px;
            text-align: left;
        }}
        td {{
            border: 1px solid #dee2e6;
            padding: 8px;
            vertical-align: top;
        }}
        .recommendations {{
            background: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .recommendations ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .footer {{
            text-align: center;
            font-size: 9pt;
            color: #6c757d;
            margin-top: 30px;
            border-top: 1px solid #dee2e6;
            padding-top: 10px;
        }}
        /* Page breaks */
        .page-break {{
            page-break-before: always;
        }}
        /* Avoid breaking inside table rows */
        tr {{
            page-break-inside: avoid;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="meta">
        <span>Document Type: {document_type}</span>
        {f"<span> | Generated: {created_at}</span>" if created_at else ""}
    </div>

    <div class="score-box">
        <strong>Overall Risk Score:</strong>
        <span class="score-value">{overall_risk_score}</span> / 100
    </div>

    <h2>Document Summary</h2>
    <p>{document_summary}</p>

    <h2>Clause Analysis</h2>
    <table>
        <thead>
            <tr>
                <th>Clause Type</th>
                <th>Summary</th>
                <th>Risk Level</th>
                <th>Key Terms</th>
                <th>Suggested Actions</th>
            </tr>
        </thead>
        <tbody>
            {clauses_rows}
        </tbody>
    </table>

    <div class="recommendations">
        <h3>Recommendations</h3>
        <ul>
            {rec_items}
        </ul>
    </div>

    <div class="footer">
        Generated by Contract Clause Reviewer
    </div>
</body>
</html>
    """
    return html
