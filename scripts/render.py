"""post.json → slide-01.jpg ... (1080x1350) 렌더.

사용법:
  python scripts/render.py 2026-11-24      # 특정 날짜
  python scripts/render.py --pending       # 이미지가 없거나 post.json 이 더 새로운 날짜 전부
"""
import json
import os
import subprocess
import sys

from playwright.sync_api import sync_playwright

from common import QUEUE, ROOT, read_json

TEMPLATE = (ROOT / "templates" / "card.html").read_text(encoding="utf-8")


def changed_files():
    """이번 푸시에서 바뀐 파일 목록 (BEFORE_SHA 환경변수). 알 수 없으면 None."""
    before = os.environ.get("BEFORE_SHA", "")
    if not before or set(before) == {"0"}:
        return None
    try:
        out = subprocess.run(["git", "diff", "--name-only", before, "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
        return set(out.split())
    except Exception:
        return None


CHANGED = changed_files()


def needs_render(folder):
    post = folder / "post.json"
    if not post.exists() or read_json(post, {}).get("status") == "published":
        return False
    if not (folder / "slide-01.jpg").exists() or CHANGED is None:
        return True
    if any(f.startswith("templates/") or f == "scripts/render.py" for f in CHANGED):
        return True
    return f"content/queue/{folder.name}/post.json" in CHANGED


def render_date(page, folder):
    post = read_json(folder / "post.json", {})
    slides = post.get("slides", [])
    for old in folder.glob("slide-*.jpg"):
        old.unlink()
    total = len(slides)
    for i, slide in enumerate(slides, 1):
        data = {"slide": slide, "index": i, "total": total, "handle": post.get("handle", ""),
                "review_no": post.get("review_no", "")}
        tmpl = TEMPLATE
        if post.get("template"):
            tmpl = (ROOT / "templates" / f"{post['template']}.html").read_text(encoding="utf-8")
        html = tmpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
        page.set_content(html, wait_until="networkidle")
        page.evaluate("document.fonts.ready.then(() => 1)")
        page.wait_for_timeout(400)  # 제목 크기 맞춤(fit)이 끝날 시간
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
