"""오늘(KST) 게시물을 인스타에 캐러셀로 게시한다. 승인된 날짜만."""
import sys
import time
from datetime import datetime

from common import (APPROVALS, KST, PUBLISHED, QUEUE, graph_get, graph_post,
                    load_config, read_json, today_kst, write_json)


def wait_finished(cfg, cid, label):
    for _ in range(30):
        st = graph_get(cfg, cid, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"{label} 컨테이너 오류: {st}")
        time.sleep(5)
    raise RuntimeError(f"{label} 컨테이너가 시간 안에 준비되지 않았습니다.")


def main(date=None):
    cfg = load_config()
    date = date or today_kst()
    folder = QUEUE / date
    post_path = folder / "post.json"
    if not post_path.exists():
        print(f"{date}: 게시물 없음 → 건너뜀")
        return

    post = read_json(post_path, {})
    published = read_json(PUBLISHED, {"posts": []})
    if post.get("status") == "published" or any(p["date"] == date for p in published["posts"]):
        print(f"{date}: 이미 게시됨")
        return

    approved = read_json(APPROVALS, {"approved": []}).get("approved", [])
    if cfg["posting"].get("require_approval", True) and post.get("status") != "approved" and date not in approved:
        print(f"{date}: 승인되지 않음 → 게시 안 함")
        return

    images = sorted(folder.glob("slide-*.jpg"))
    if not images:
        raise SystemExit(f"{date}: 카드 이미지가 없습니다 (렌더 확인).")
    if len(images) > 10:
        images = images[:10]

    ig = cfg["ig_user_id"]
    base = cfg["public_base_url"].rstrip("/")
    children = []
    for img in images:
        url = f"{base}/content/queue/{date}/{img.name}"
        res = graph_post(cfg, f"{ig}/media", {"image_url": url, "is_carousel_item": "true"})
        wait_finished(cfg, res["id"], img.name)
        children.append(res["id"])

    tags = " ".join("#" + t.lstrip("#") for t in post.get("hashtags", []))
    caption = post.get("caption", "").strip()
    if tags:
        caption = f"{caption}\n\n{tags}"

    if len(children) == 1:
        res = graph_post(cfg, f"{ig}/media", {"image_url": f"{base}/content/queue/{date}/{images[0].name}",
                                               "caption": caption})
    else:
        res = graph_post(cfg, f"{ig}/media", {"media_type": "CAROUSEL", "children": ",".join(children),
                                               "caption": caption})
    wait_finished(cfg, res["id"], "carousel")
    pub = graph_post(cfg, f"{ig}/media_publish", {"creation_id": res["id"]})
    media_id = pub["id"]
    link = graph_get(cfg, media_id, {"fields": "permalink"}).get("permalink", "")

    published["posts"].append({"date": date, "media_id": media_id, "permalink": link,
                               "topic": post.get("topic", ""),
                               "published_at": datetime.now(KST).isoformat(timespec="seconds")})
    write_json(PUBLISHED, published)
    post["status"] = "published"
    write_json(post_path, post)
    print(f"{date}: 게시 완료 {link}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
