"""공통: 설정 로드, 경로, Graph API 호출(재시도)."""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "content" / "queue"
APPROVALS = ROOT / "content" / "approvals.json"
PUBLISHED = ROOT / "state" / "published.json"
KST = timezone(timedelta(hours=9))


def load_config():
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def today_kst():
    return datetime.now(KST).strftime("%Y-%m-%d")


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _token():
    tok = os.environ.get("ACCESS_TOKEN", "").strip()
    if not tok:
        raise SystemExit("ACCESS_TOKEN 이 비어 있습니다 (GitHub Secret 확인).")
    return tok


def _url(cfg, path):
    return f"https://graph.facebook.com/{cfg['graph_version']}/{path.lstrip('/')}"


def _call(method, cfg, path, params, tries=4):
    params = dict(params or {})
    params["access_token"] = _token()
    last = None
    for i in range(tries):
        try:
            r = requests.request(method, _url(cfg, path), params=params if method == "GET" else None,
                                 data=params if method == "POST" else None, timeout=60)
            body = r.json() if r.content else {}
            if r.status_code < 400:
                return body
            err = body.get("error", {})
            last = f"{r.status_code} {err.get('code')} {err.get('message')}"
            # 일시적 오류만 재시도
            if r.status_code < 500 and err.get("code") not in (1, 2, 4, 17, 341, 9007):
                break
        except requests.RequestException as e:
            last = str(e)
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"Graph API {method} {path} 실패: {last}")


def graph_get(cfg, path, params=None):
    return _call("GET", cfg, path, params)


def graph_post(cfg, path, params=None):
    return _call("POST", cfg, path, params)
