"""Страница гайда — тот же токен-набор темы, что и в корневом index.html студии
(см. /home/user/ai-studio/index.html: --bg/--surface/--border/--text/--muted, Inter).
"""
from __future__ import annotations

from html import escape

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" '
    'rel="stylesheet">'
)

_CSS = """
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  :root{
    --bg:#0B0F19;--surface:#131A2A;--border:rgba(255,255,255,.08);
    --text:#E6EAF2;--muted:#8A94A8;--accent:#2DD4BF;
  }
  html{scroll-behavior:smooth}
  body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);line-height:1.7;
       -webkit-font-smoothing:antialiased}
  a{color:var(--accent);text-decoration:none}
  .container{max-width:720px;margin:0 auto;padding:0 24px}
  nav{position:sticky;top:0;z-index:10;background:rgba(11,15,25,.85);backdrop-filter:blur(12px);
      border-bottom:1px solid var(--border)}
  .nav-inner{display:flex;align-items:center;justify-content:space-between;height:60px;
             max-width:720px;margin:0 auto;padding:0 24px}
  .wordmark{font-size:15px;font-weight:600;color:var(--text)}
  article{padding:64px 0}
  .label{font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
         color:var(--muted);margin-bottom:16px}
  h1{font-size:clamp(28px,5vw,44px);font-weight:700;letter-spacing:-.02em;line-height:1.2;margin-bottom:24px}
  p{font-size:17px;color:var(--text);margin-bottom:20px}
  p.lead{font-size:19px;color:var(--muted)}
  .figure{margin:32px 0}
  .figure img{width:100%;border-radius:16px;border:1px solid var(--border);display:block}
  .figure figcaption{font-size:13px;color:var(--muted);margin-top:8px}
  blockquote{border-left:3px solid var(--accent);padding-left:20px;color:var(--muted);
             font-size:15px;margin:32px 0}
  .cta{margin-top:48px;padding:28px;border-radius:16px;background:var(--surface);
       border:1px solid var(--border)}
  .cta .badge{display:inline-block;padding:6px 14px;border-radius:999px;background:var(--bg);
             border:1px solid var(--border);font-size:13px;font-weight:600;margin-bottom:12px}
  footer{padding:32px 0;border-top:1px solid var(--border);color:var(--muted);font-size:13px}
"""


def _paragraphs(text: str) -> str:
    parts = [p.strip() for p in text.split("\n") if p.strip()]
    if not parts:
        parts = [text.strip()]
    return "".join(f"<p>{escape(p)}</p>" for p in parts)


def render_guide(
    title: str,
    lead: str,
    body: str,
    codeword: str,
    source_url: str | None,
    infographic_rel: str | None,
    site_root_rel: str = "../..",
) -> str:
    figure_html = ""
    if infographic_rel:
        figure_html = f"""
        <figure class="figure">
          <img src="{escape(infographic_rel)}" alt="Инфографика: {escape(title)}" loading="lazy">
          <figcaption>Инфографика по теме</figcaption>
        </figure>"""

    source_html = ""
    if source_url:
        source_html = f'<blockquote>Источник: <a href="{escape(source_url)}">{escape(source_url)}</a></blockquote>'

    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)} — Poddubotsky AI</title>
{_FONT_LINK}
<style>{_CSS}</style></head><body>
<nav><div class="nav-inner">
  <a class="wordmark" href="{escape(site_root_rel)}/">← Poddubotsky AI Studio</a>
</div></nav>
<div class="container"><article>
  <div class="label">Разбор</div>
  <h1>{escape(title)}</h1>
  <p class="lead">{escape(lead)}</p>
  {figure_html}
  {_paragraphs(body)}
  {source_html}
  <div class="cta">
    <span class="badge">Кодовое слово: {escape(codeword)}</span>
    <p style="margin:0">Напиши «{escape(codeword)}» в комментарии под постом — пришлю карусель и гайд.</p>
  </div>
</article></div>
<footer><div class="container">Poddubotsky AI Studio</div></footer>
</body></html>"""
