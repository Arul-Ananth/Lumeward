from __future__ import annotations

from backend.common.services.newsletter.compiler import compile_html


def render_digest_html(markdown: str, theme_mode: str = "dark") -> str:
    palette = _palette(theme_mode)
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    background: {palette["body_bg"]};
    color: {palette["body_text"]};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 15px;
    line-height: 1.62;
    margin: 0;
    padding: 26px 30px;
}}
h1 {{
    color: {palette["heading"]};
    font-size: 25px;
    font-weight: 700;
    line-height: 1.24;
    margin: 0 0 22px;
    padding-bottom: 14px;
    border-bottom: 1px solid {palette["rule"]};
}}
h2 {{
    color: {palette["heading"]};
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
    color: {palette["strong"]};
}}
</style>
</head>
<body>{compile_html(markdown)}</body>
</html>
"""


def _palette(theme_mode: str) -> dict[str, str]:
    if theme_mode == "light":
        return {
            "body_bg": "#ffffff",
            "body_text": "#1c1c1e",
            "heading": "#111113",
            "rule": "#d1d1d6",
            "strong": "#000000",
        }
    return {
        "body_bg": "#161617",
        "body_text": "#e5e5ea",
        "heading": "#f5f5f7",
        "rule": "#2c2c2e",
        "strong": "#ffffff",
    }
