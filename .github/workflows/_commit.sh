#!/usr/bin/env bash
# 변경된 파일이 있으면 커밋·푸시 (없으면 조용히 통과)
set -e
MSG="${1:-bot: update}"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A
if git diff --cached --quiet; then
  echo "변경 없음"
  exit 0
fi
git commit -m "$MSG"
for i in 1 2 3; do
  git pull --rebase origin main && git push origin HEAD:main && exit 0
  sleep 5
done
exit 1
