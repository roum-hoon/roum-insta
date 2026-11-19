"""경쟁 계정 추적 (Business Discovery). 매주 실행."""
import csv
from datetime import datetime

import yaml

from common import KST, ROOT, graph_get, load_config

DATA = ROOT / "data"
FIELDS = ("business_discovery.username({u}){{username,followers_count,media_count,"
          "media.limit(12){{like_count,comments_count,timestamp,caption,media_type,permalink}}}}")


def last_followers():
    path = DATA / "competitors.csv"
    out = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out[row["username"]] = int(row["followers"])
    return out


def main():
    cfg = load_config()
    with open(ROOT / "competitors.yaml", encoding="utf-8") as f:
        comp = yaml.safe_load(f) or {}
    users = (comp.get("tracked") or []) + (comp.get("bench") or [])
    if not users:
        print("competitors.yaml 에 계정이 없습니다")
        return
    DATA.mkdir(exist_ok=True)
    prev = last_followers()
    now = datetime.now(KST).strftime("%Y-%m-%d")
    acc_path, post_path = DATA / "competitors.csv", DATA / "competitor_posts.csv"
    new_acc = not acc_path.exists()
    new_post = not post_path.exists()
    with open(acc_path, "a", newline="", encoding="utf-8") as fa, \
         open(post_path, "a", newline="", encoding="utf-8") as fp:
        wa, wp = csv.writer(fa), csv.writer(fp)
        if new_acc:
            wa.writerow(["date", "username", "followers", "media_count", "avg_likes", "avg_comments", "flag"])
        if new_post:
            wp.writerow(["date", "username", "timestamp", "media_type", "likes", "comments", "permalink", "caption"])
        for u in users:
            try:
                bd = graph_get(cfg, cfg["ig_user_id"], {"fields": FIELDS.format(u=u)})["business_discovery"]
            except Exception as e:  # 비공개/개인 계정 등
                print(f"{u}: 실패 {e}")
                continue
            media = bd.get("media", {}).get("data", [])
            likes = [m.get("like_count", 0) for m in media]
            comments = [m.get("comments_count", 0) for m in media]
            f = bd.get("followers_count", 0)
            flag = "급증" if u in prev and prev[u] and (f - prev[u]) / prev[u] >= 0.15 else ""
            wa.writerow([now, u, f, bd.get("media_count", 0),
                         round(sum(likes) / len(likes), 1) if likes else 0,
                         round(sum(comments) / len(comments), 1) if comments else 0, flag])
            for m in media:
                wp.writerow([now, u, m.get("timestamp"), m.get("media_type"), m.get("like_count", 0),
                             m.get("comments_count", 0), m.get("permalink"),
                             (m.get("caption") or "").replace("\n", " ")[:200]])
            print(f"{u}: 팔로워 {f} {flag}")


if __name__ == "__main__":
    main()
