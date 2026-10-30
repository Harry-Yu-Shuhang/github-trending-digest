# Development

Run these commands from the repository root:

```sh
uv sync --project app --frozen --extra ui --python 3.12
uv run --project app python -m trending_digest
uv run --project app --extra ui python app/start.py --no-browser
uv run --directory app ruff check .
uv run --directory app ruff format --check .
uv run --project app python -m unittest discover -s app/tests -v
uv run --project app --with playwright python app/tests/browser_smoke.py
uv run --project app --extra ui --with playwright python app/tests/ui_browser_smoke.py
```

The package, tests, `pyproject.toml`, `uv.lock`, `.venv`, build artifacts, and caches
live under `app/`. User configuration stays in the repository root. Generated
reports, archives, and snapshots live under `output/`. `--root` chooses another
workspace with the same configuration, `docs/`, and `output/` layout.

For offline generation, add `--html path/to/trending.html --readme-dir path/to/readmes`.
The README directory uses `owner/repo/README.md` and `metadata.json`.
This makes source fetching offline; introductions and relevance still call the configured
model. Configure `llm` in the root `conf.yaml` first. Tests use an offline model fixture.

The GUI shuts down eight seconds after its last browser tab closes. Use `--keep-alive`
with `app/start.py` for a server that should keep running without browser sessions.
