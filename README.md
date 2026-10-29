# GitHub Tech Brief

[English](README.md) · [简体中文](README.zh-CN.md)

A daily introduction to interesting open-source projects from [GitHub Trending](https://github.com/trending?since=daily). Each project gets a short explanation of **what it does** and **what stands out**, grounded in its actual README.

Choose English or Simplified Chinese with `active_language`. It controls the Gradio interface and the only report language generated on that run. Existing historical editions remain available.

<!-- digest:start -->

### 2026-10-29 · Latest brief

[Read this issue](daily/2026/10/2026-10-29.md) · [Previous issues](daily/README.md)

- **[JetBrains/thinkrail](https://github.com/JetBrains/thinkrail)** — An agent-focused IDE built around the pi coding agent, combining code editing, isolated workspaces, and durable project knowledge.
- **[elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills)** — A modular collection of design skills for AI coding tools that can read Markdown rules.
- **[obra/superpowers](https://github.com/obra/superpowers)** — A composable skills framework that gives coding agents a software development process, from clarifying requirements to reviewing and finishing changes.

<!-- digest:end -->

## Read the brief

- **[Latest HTML report](reports/index.html)**
- [Latest Markdown report](latest.md)
- [Issue archive](daily/README.md)

Project cards contain a concise purpose, up to three highlights, a link to the source README, and a small language / star line. All current Trending projects are covered by default, up to 25; `top_n` can reduce that number.

The HTML edition has a reading directory, full-text search, programming-language filters, a dark mode, and a print / PDF layout. It adapts to mobile screens. Each HTML file embeds all styling and scripts and works directly from your local filesystem. Open `reports/index.html` in a browser; GitHub's file viewer shows the HTML source. The latest entry and archive use the active language. Dated filenames retain their language identity; switching to Chinese does not rewrite archived English reports.

## One-click configuration workspace

- **Windows:** double-click `start.bat`.
- **macOS:** double-click `start.command`, or run `sh start.command` from Terminal.
- **Shared entry:** both wrappers prepare the same environment and run `start.py`.

The launchers install uv if needed, prepare Python 3.12 and the optional UI dependencies, and open the local Gradio workspace at `http://127.0.0.1:7860`. The first run needs internet access. Close the terminal or press Ctrl+C to stop it. If a ZIP download loses the macOS executable bit, use `sh start.command`.

The responsive form visualizes every setting in `conf.yaml`. Changing the language immediately translates the interface while preserving unsaved values. **Save configuration** persists validated settings. **Fetch & generate report** saves the form and fetches fresh Trending / README data. **Generate from saved data** saves the form and renders the last capture without network requests; source filters and capture timestamps stay those of the saved data. Preview and download the resulting HTML inside the workspace.

To choose another port or skip browser opening:

```sh
uv run --frozen --extra ui --python 3.12 python start.py --port 7861 --no-browser
```

## Run locally

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --frozen
uv run python -m trending_digest
```

Public READMEs can be fetched without a token. Set `GITHUB_TOKEN` to avoid the lower unauthenticated GitHub API limit. It is only sent to GitHub; no model API is called.

## Configuration

Edit [conf.yaml](conf.yaml). The previous `config.json` has been replaced.

| Setting | Meaning |
| --- | --- |
| `active_language` | Interface and report language: `en` or `zh-CN`; generates just that language |
| `programming_language` | Trending programming-language filter; empty means all |
| `spoken_language` | Trending description-language filter; empty means all |
| `top_n` | Number of project cards, from 1 to 25 |
| `timezone` | Issue date and capture timestamp timezone |
| `readme` | Request timeout, fetch concurrency, and excerpt input limit |
| `summary.mode` | `curated` to prefer saved bilingual summaries, or `extractive` for source excerpts |
| `summary.curated_file` | Path to the versioned summary collection |
| `summary.highlights` | Maximum highlights per project, from 1 to 5 |
| `summary.fallback` | Currently `extractive`; new or changed sources get labelled excerpts |

Changing the timezone does not change the workflow schedule. Older `default_language` configurations are migrated when loaded; saving writes only `active_language`.

## How summaries work

The current bilingual notes in [summaries.yaml](summaries.yaml) were written by Codex after reading the source READMEs. Each entry is tied to a README blob SHA. It is reused only while that source version still matches.

For a new or changed README, the daily job extracts source passages and labels the selected-language summary as pending. It preserves the original language instead of claiming an automatic translation. Missing READMEs are labelled explicitly. A failed Trending fetch stops publication and preserves the existing brief.

No external model service or API key is configured. GitHub Actions does not have access to this Codex conversation. To refresh curated notes, ask Codex to read the current source README and update both languages and `readme_sha` in `summaries.yaml`; then regenerate. No unsupported model settings are included in the configuration.

## Daily automation

[Daily Trending Digest](.github/workflows/daily.yml) runs at **01:17 UTC / 09:17 Asia/Shanghai** and commits the active-language report, archives, and JSON snapshot. You can also use **Actions → Daily Trending Digest → Run workflow**. It uses the repository's built-in `GITHUB_TOKEN` and requires no model secrets. To change the cloud schedule's report language, commit the updated `conf.yaml`; a local UI save does not push Git changes automatically.

Scheduled runs can be delayed; see [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Forks must enable Actions. The workflow publishes only from the default branch.

## Development

```sh
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
```

Optional browser checks use an installed Chrome / Edge (or Playwright's Chromium):

```sh
uv run --with playwright python tests/browser_smoke.py
uv run --extra ui --with playwright python tests/ui_browser_smoke.py
```

For offline debugging, pass `--html path/to/trending.html --readme-dir path/to/readmes`. The README directory uses `owner/repo/README.md` plus `metadata.json` containing `sha`, `url`, and `path`. Offline generation still uses today's date.

```text
README.md / README.zh-CN.md       English and Chinese documentation
latest.md                        Latest report in the active language
reports/index.html               Latest HTML report in the active language
start.py                         Shared local UI entry
start.bat / start.command        Windows / macOS startup wrappers
reports/YYYY/MM/                 Dated, standalone HTML editions
daily/YYYY/MM/                   Dated English / Chinese issues
data/YYYY/MM/YYYY-MM-DD.json      Source metadata and active-language summaries
conf.yaml                        Public configuration
summaries.yaml                   Versioned, curated project summaries
trending_digest/                 Fetching, extraction, localization, and CLI
```

## License

Code is [MIT licensed](LICENSE). Project names, trademarks, and third-party README content belong to their respective owners. Source links are included with each project.
