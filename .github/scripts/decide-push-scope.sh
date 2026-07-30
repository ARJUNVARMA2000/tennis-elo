#!/usr/bin/env bash
# Classify a master push as a cached-data web deploy or a full data refresh.
#
# A web-only change does not need 27-day source sweeps or forecast regeneration: the
# restored data cache has already shipped through the integrity gate, and this run gates
# it again before mirroring. Any unknown path fails closed to `data`.
set -euo pipefail

EVENT_NAME="${EVENT_NAME:-}"
BEFORE_SHA="${BEFORE_SHA:-}"
CURRENT_SHA="${CURRENT_SHA:-${GITHUB_SHA:-HEAD}}"

scope=data
files="${CHANGED_FILES:-}"

if [ "$EVENT_NAME" = "push" ]; then
  if [ -z "$files" ]; then
    if [ -z "$BEFORE_SHA" ] \
       || [[ "$BEFORE_SHA" =~ ^0+$ ]] \
       || ! git cat-file -e "${BEFORE_SHA}^{commit}" 2>/dev/null; then
      files=""
    else
      files="$(git diff --name-only "$BEFORE_SHA" "$CURRENT_SHA")"
    fi
  fi

  if [ -n "$files" ]; then
    scope=web
    while IFS= read -r file; do
      [ -z "$file" ] && continue
      case "$file" in
        web/*|firebase.json|.firebaserc|tasks/*|README.md|tennis_model/README.md|AGENTS.md)
          ;;
        *)
          scope=data
          break
          ;;
      esac
    done <<< "$files"
  fi
fi

[ -n "${GITHUB_OUTPUT:-}" ] && echo "scope=$scope" >> "$GITHUB_OUTPUT"
echo "Selected push scope: $scope (event=$EVENT_NAME)"
