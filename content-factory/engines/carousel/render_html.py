"""HTML-шаблоны слайдов — токены темы взяты из корневого index.html студии,
чтобы карусель визуально совпадала с сайтом (Inter, тёмная палитра).
"""
from __future__ import annotations

from html import escape

W, H = 1080, 1350  # 4:5

_FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" '
    'rel="stylesheet">'
)

_BASE_CSS = """
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  html,body{width:%(w)spx;height:%(h)spx;overflow:hidden}
  body{
    font-family:'Inter',sans-serif;background:#0B0F19;color:#E6EAF2;
    display:flex;flex-direction:column;justify-content:space-between;
    padding:72px 64px;-webkit-font-smoothing:antialiased;
  }
  .muted{color:#8A94A8}
  .badge{
    display:inline-block;padding:10px 20px;border-radius:999px;
    background:#131A2A;border:1px solid rgba(255,255,255,.12);
    font-size:28px;font-weight:600;letter-spacing:.02em;
  }
  .page{font-size:26px;color:#8A94A8}
""" % {"w": W, "h": H}


def _wrap(body_html: str, extra_css: str = "") -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">{_FONT_LINK}
<style>{_BASE_CSS}{extra_css}</style></head><body>{body_html}</body></html>"""


def render_cover(title: str, subtitle: str, page_label: str, animated: bool) -> str:
    css = """
      .blob{
        position:absolute;inset:-20%;
        background:radial-gradient(circle at 30% 30%, #7C5CFF 0%, transparent 60%),
                   radial-gradient(circle at 70% 70%, #2DD4BF 0%, transparent 55%);
        filter:blur(60px);opacity:.55;z-index:0;
      }
      @keyframes drift{
        0%{transform:translate(0,0) scale(1)}
        50%{transform:translate(-3%,2%) scale(1.06)}
        100%{transform:translate(0,0) scale(1)}
      }
      .blob.animated{animation:drift 3s ease-in-out infinite}
      .stage{position:relative;flex:1;display:flex;flex-direction:column;justify-content:center;z-index:1}
      h1{font-size:76px;font-weight:800;line-height:1.08;letter-spacing:-.02em}
      p.sub{margin-top:24px;font-size:34px;color:#8A94A8}
      .top,.bottom{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:center}
    """
    blob_class = "blob animated" if animated else "blob"
    body = f"""
      <div class="top"><span class="badge">Poddubotsky AI</span><span class="page">{escape(page_label)}</span></div>
      <div class="{blob_class}"></div>
      <div class="stage">
        <h1>{escape(title)}</h1>
        <p class="sub">{escape(subtitle)}</p>
      </div>
      <div class="bottom"><span class="page muted">свайп →</span></div>
    """
    return _wrap(body, css)


def render_content(number: str, body: str, page_label: str) -> str:
    css = """
      .num{font-size:40px;font-weight:700;color:#2DD4BF}
      .stage{flex:1;display:flex;align-items:center}
      p.body{font-size:46px;line-height:1.35;font-weight:600;letter-spacing:-.01em}
      .top,.bottom{display:flex;justify-content:space-between;align-items:center}
    """
    body_html = f"""
      <div class="top"><span class="num">{escape(number)}</span><span class="page">{escape(page_label)}</span></div>
      <div class="stage"><p class="body">{escape(body)}</p></div>
      <div class="bottom"><span class="page muted">свайп →</span></div>
    """
    return _wrap(body_html, css)


def render_cta(title: str, body: str, page_label: str) -> str:
    css = """
      .stage{flex:1;display:flex;flex-direction:column;justify-content:center}
      h2{font-size:64px;font-weight:800;margin-bottom:28px}
      p.body{font-size:38px;color:#E6EAF2;line-height:1.4}
      .top,.bottom{display:flex;justify-content:space-between;align-items:center}
    """
    body_html = f"""
      <div class="top"><span class="badge">Poddubotsky AI</span><span class="page">{escape(page_label)}</span></div>
      <div class="stage"><h2>{escape(title)}</h2><p class="body">{escape(body)}</p></div>
      <div class="bottom"><span class="page muted">сохрани ↓</span></div>
    """
    return _wrap(body_html, css)


def render_infographic(title: str, stats: list[str]) -> str:
    css = """
      h2{font-size:56px;font-weight:800;margin-bottom:40px}
      .grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;flex:1;align-content:start}
      .card{
        background:#131A2A;border:1px solid rgba(255,255,255,.08);border-radius:20px;
        padding:32px;font-size:30px;line-height:1.35;font-weight:600;
      }
      .top{display:flex;justify-content:space-between;align-items:center}
    """
    cards = "".join(f'<div class="card">{escape(s)}</div>' for s in stats) or '<div class="card muted">Нет данных</div>'
    body_html = f"""
      <div class="top"><span class="badge">Разбор</span></div>
      <h2>{escape(title)}</h2>
      <div class="grid">{cards}</div>
    """
    return _wrap(body_html, css)
