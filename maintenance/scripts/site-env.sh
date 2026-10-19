#!/usr/bin/env bash
#
# site-env.sh - create the venv the docs-site gates and a local build use: the pinned zensical, installed ONLY
# from the hashed lock (maintenance/site/requirements.txt), with --require-hashes and --only-binary :all: so
# nothing unhashed and nothing built from source gets in. Python 3.12 is the minor the pin was measured on.
#
#   maintenance/scripts/site-env.sh                      # -> ~/.cache/handbook-site/venv
#   HANDBOOK_SITE_VENV=/some/dir maintenance/scripts/site-env.sh
#
# verify-docs.sh reads $HANDBOOK_SITE_PY (default ~/.cache/handbook-site/venv/bin/python) and skips the site
# build, with one WARN, when it is missing. Uses uv when present, else python3.12 -m venv and pip.
# Re-running replaces the venv. On Windows the interpreter is <venv>\Scripts\python.exe.

set -eu
cd "$(dirname "$0")/../.." || exit 2
VENV="${HANDBOOK_SITE_VENV:-$HOME/.cache/handbook-site/venv}"
LOCK=maintenance/site/requirements.txt
[ -f "$LOCK" ] || { echo "site-env.sh: $LOCK not found" >&2; exit 2; }

if command -v uv >/dev/null 2>&1; then
  uv venv --clear --python 3.12 "$VENV"
  uv pip install --python "$VENV/bin/python" --require-hashes --only-binary :all: -r "$LOCK"
else
  command -v python3.12 >/dev/null 2>&1 || { echo "site-env.sh: neither uv nor python3.12 is installed" >&2; exit 2; }
  rm -rf "$VENV"
  python3.12 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --require-hashes --only-binary :all: -r "$LOCK"
fi

want="$(sed -n 's/^zensical==\([0-9][0-9.]*\) .*/\1/p' "$LOCK")"
got="$("$VENV/bin/python" -m zensical --version 2>/dev/null | sed -n 's/^.*[Vv]ersion[: ]*\([0-9][0-9.]*\).*$/\1/p; s/^zensical, version \([0-9.]*\)$/\1/p' | sed -n 1p)"
[ -n "$got" ] || got="$("$VENV/bin/python" -m zensical --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | sed -n 1p)"
if [ "$got" != "$want" ]; then
  echo "site-env.sh: the venv holds zensical '$got', the lock pins '$want'" >&2
  exit 1
fi
echo "zensical $got installed in $VENV"
echo "export HANDBOOK_SITE_PY=$VENV/bin/python"
