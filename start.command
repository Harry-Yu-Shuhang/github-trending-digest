#!/bin/sh
set -eu
brief_dir=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$brief_dir"
PATH="$HOME/.local/bin:$PATH"
export PATH
if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' 'Installing uv from astral.sh...'
  curl -LsSf https://astral.sh/uv/install.sh | UV_NO_MODIFY_PATH=1 sh
fi
exec uv run --project "$brief_dir/app" --frozen --extra ui --python 3.12 python "$brief_dir/app/start.py" "$@"
