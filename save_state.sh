#!/usr/bin/env bash
# Commit and push posted.json if it changed. Retries so a push race can't
# lose the record of a tweeted game (which would let it be tweeted again).
set -e
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add posted.json
git diff --cached --quiet && exit 0
git commit -q -m "Record posted games"
for i in 1 2 3 4 5; do
  git pull -q --rebase origin main && git push -q origin HEAD:main && exit 0
  sleep $((i * 5))
done
exit 1
