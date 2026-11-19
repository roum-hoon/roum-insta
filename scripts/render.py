"""post.json → slide-01.jpg ... (1080x1350) 렌더.

사용법:
  python scripts/render.py 2026-11-24      # 특정 날짜
  python scripts/render.py --pending       # 이미지가 없거나 post.json 이 더 새로운 날짜 전부
"""
import json
import sys

from playwright.sync_api import sync_playwright

from common import QUEUE, ROOT, read_json

TEMPLATE = (ROOT / "templates" / "card.html").read_text(encoding="utf-8")


def needs_render(folder):
    post = folder / "post.json"
    first = folder / "slide-01.jpg"
    if not post.exists():
        return False
    if not first.exists():
        return True
    tmpl = ROOT / "templates" / "card.html"
    newest_src = max(post.stat().st_mtime, tmpl.stat().st_mtime)
    return newest_src > first.stat().st_mtime


def render_date(page, folder):
    post = read_json(folder / "post.json", {})
    slides = post.get("slides", [])
    for old in folder.glob("slide-*.jpg"):
        old.unlink()
    total = len(slides)
    for i, slide in enumerate(slides, 1):
        data = {"slide": slide, "index": i, "total": total, "handle": post.get("handle", "")}
        html = TEMPLATE.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
        page.set_content(html, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.screenshot(path=str(folder / f"slide-{i:02d}.jpg"), type="jpeg", quality=92,
                        clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
    print(f"{folder.name}: {total}장 렌더")


def main(args):
    if args and args[0] == "--pending":
        folders = [f for f in sorted(QUEUE.iterdir()) if f.is_dir() and needs_render(f)] if QUEUE.exists() else []
    else:
        folders = [QUEUE / a for a in args]
    if not folders:
        print("렌더할 게시물 없음")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for f in folders:
            render_date(page, f)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
