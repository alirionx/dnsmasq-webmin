#!/usr/bin/env bash
# Local secret scan with gitleaks. Run it before every push:
#
#   scripts/secret-scan.sh
#
# Deliberately local only, this is not part of the GitHub Actions workflows.
#
# Scans everything that could end up on GitHub:
#   1. the git history (all branches and tags)
#   2. the working tree: tracked and new files, without anything in .gitignore
#
# Uses a gitleaks binary from PATH, otherwise the pinned Docker image.
# Findings are printed redacted. False positives go into .gitleaksignore.
#
# Exit codes: 0 = clean, 1 = secrets found, 2 = scan could not run
set -uo pipefail

GITLEAKS_IMAGE="ghcr.io/gitleaks/gitleaks:v8.30.1"
LEAKS_EXIT=3 # distinct from gitleaks' own error exit code 1

die() {
  echo "ERROR: $*" >&2
  exit 2
}

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)" \
  || die "not inside a git repository"

if command -v gitleaks >/dev/null; then
  RUNNER=binary
elif command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  RUNNER=docker
else
  die "neither gitleaks nor a running Docker found, see https://github.com/gitleaks/gitleaks#installing"
fi

# run_gitleaks <dir> <gitleaks args...>: runs gitleaks with <dir> as working directory
run_gitleaks() {
  local dir="$1"
  shift
  local args=("$@" --redact --verbose --no-banner --log-level warn --exit-code "$LEAKS_EXIT")
  if [ "$RUNNER" = binary ]; then
    (cd "$dir" && gitleaks "${args[@]}")
  else
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
      -v "$dir:/scan:ro" -w /scan "$GITLEAKS_IMAGE" "${args[@]}"
  fi
}

STAGING="$(mktemp -d)" || die "could not create a temp directory"
trap 'rm -rf "$STAGING"' EXIT

# Copies all files git would see (tracked + untracked, not ignored) to $STAGING
stage_working_tree() {
  git -C "$ROOT" ls-files -z --cached --others --exclude-standard \
    | while IFS= read -r -d '' file; do
        # tracked files deleted in the working tree are still listed
        if [ -e "$ROOT/$file" ] || [ -L "$ROOT/$file" ]; then printf '%s\0' "$file"; fi
      done \
    | tar -C "$ROOT" --null -T - -cf - \
    | tar -C "$STAGING" -xf -
}

result=0

# scan <label> <dir> <gitleaks args...>
scan() {
  local label="$1"
  shift
  echo ">> $label"
  run_gitleaks "$@"
  local code=$?
  case "$code" in
    0) echo "   clean" ;;
    "$LEAKS_EXIT") result=1 ;;
    *) die "gitleaks failed with exit code $code" ;;
  esac
}

echo "gitleaks via $RUNNER"
scan "git history" "$ROOT" git .
stage_working_tree || die "could not copy the working tree"
scan "working tree" "$STAGING" dir .

if [ "$result" -ne 0 ]; then
  echo
  echo "SECRETS FOUND: do not push." >&2
  echo "A secret that was ever committed counts as burned: rotate it, then clean up the history." >&2
  exit 1
fi
echo
echo "No secrets found."
