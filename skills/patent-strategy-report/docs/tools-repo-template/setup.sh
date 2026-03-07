#!/usr/bin/env bash
# 도구 통합 레포에서 실행: skills/ 내용을 Codex 스킬 디렉터리로 복사
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_SKILLS="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$CODEX_SKILLS"

SKILLS_SRC="$REPO_ROOT/skills"
if [ ! -d "$SKILLS_SRC" ]; then echo "No skills/ folder found."; exit 1; fi

for dir in "$SKILLS_SRC"/*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  echo "Deploying skill: $name -> $CODEX_SKILLS/$name"
  rm -rf "$CODEX_SKILLS/$name"
  cp -R "$dir" "$CODEX_SKILLS/$name"
done
echo "Done. Restart Codex to load skills."
