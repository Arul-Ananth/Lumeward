from __future__ import annotations

from backend.common.services.newsletter.compiler import compile_html


def render_digest_html(markdown: str) -> str:
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    background: #161617;
    color: #e5e5ea;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 15px;
    line-height: 1.62;
    margin: 0;
    padding: 26px 30px;
}}
h1 {{
    color: #f5f5f7;
    font-size: 25px;
    font-weight: 700;
    line-height: 1.24;
    margin: 0 0 22px;
    padding-bottom: 14px;
    border-bottom: 1px solid #2c2c2e;
}}
h2 {{
    color: #f2f2f7;
    font-size: 19px;
    font-weight: 650;
    margin: 28px 0 10px;
}}
p {{
    margin: 0 0 14px;
}}
ul {{
    margin: 8px 0 18px 22px;
    padding: 0;
}}
li {{
    margin: 0 0 8px;
}}
strong {{
    color: #ffffff;
}}
</style>
</head>
<body>{compile_html(markdown)}</body>
</html>
"""
