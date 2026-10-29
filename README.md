# GitHub Trending Workspace

[English](README.md) · [简体中文](docs/README.zh-CN.md)

A daily introduction to interesting open-source projects from [GitHub Trending](https://github.com/trending?since=daily). Each project gets a short explanation of **what it does** and **what stands out**, grounded in its actual README.

Choose English or Simplified Chinese with `active_language`. It controls the Gradio interface and the only report language generated on that run. Existing historical editions remain available.

<!-- digest:start -->

### 2026-10-29 · Latest brief

[Read this issue](output/daily/2026/10/2026-10-29.md) · [Previous issues](output/daily/README.md)

- **[JetBrains/thinkrail](https://github.com/JetBrains/thinkrail)** — An agent-focused IDE built around the pi coding agent, combining code editing, isolated workspaces, and durable project knowledge.
- **[elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills)** — A modular collection of design skills for AI coding tools that can read Markdown rules.
- **[obra/superpowers](https://github.com/obra/superpowers)** — A composable skills framework that gives coding agents a software development process, from clarifying requirements to reviewing and finishing changes.

<!-- digest:end -->

## Read the brief

Report links refer to local generated files. Git ignores `output/` and the legacy root `data/`; reports and snapshots are not committed.

- **[Latest HTML report](output/reports/index.html)**
- [Latest Markdown report](output/latest.md)
- [Issue archive](output/daily/README.md)

Project cards contain a concise purpose, up to three highlights, a link to the source README, and a small language / star line. All current Trending projects are covered by default, up to 25; `top_n` can reduce that number.

The HTML edition has a reading directory, full-text search, programming-language filters, a dark mode, and a print / PDF layout. It adapts to mobile screens. Each HTML file embeds all styling and scripts and works directly from your local filesystem. Open `output/reports/index.html` in a browser; GitHub's file viewer shows the HTML source. The latest entry and archive use the active language. Dated filenames retain their language identity; switching to Chinese does not rewrite archived English reports.

## One-click configuration workspace

- **Windows:** double-click `start.bat`.
- **macOS:** double-click `start.command`, or run `sh start.command` from Terminal.
- **Shared entry:** both wrappers prepare the same environment and run `app/start.py`.

The launchers install uv if needed, prepare Python 3.12 and the optional UI dependencies, and open the local Gradio workspace at `http://127.0.0.1:7860`. The first run needs internet access. Close the terminal or press Ctrl+C to stop it. If a ZIP download loses the macOS executable bit, use `sh start.command`.

The responsive form visualizes every setting in `conf.yaml`. Changing the language immediately translates the interface while preserving unsaved values. **Save configuration** persists validated settings. **Fetch & generate report** saves the form and fetches fresh Trending / README data. **Generate from saved data** saves the form and renders the last capture without network requests; source filters and capture timestamps stay those of the saved data. Preview and download the resulting HTML inside the workspace.

To choose another port or skip browser opening:

The GUI automatically tries available ports starting at 7860 (7861, 7862, and so on
if earlier ports are busy). The browser opens the selected address. `--port` requests
a fixed port instead; `GRADIO_SERVER_PORT` sets the starting port for automatic selection.

```sh
uv run --project app --frozen --extra ui --python 3.12 python app/start.py --port 7861 --no-browser
```

## Run locally

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

Run the commands below from the repository root. Implementation and dependencies live in
`app/`; generated reports, archives, and snapshots live in `output/`.

```sh
uv sync --project app --frozen
uv run --project app python -m trending_digest
```

Public READMEs can be fetched without a token. Set `GITHUB_TOKEN` to avoid the lower unauthenticated GitHub API limit. The UI launcher also reuses an existing GitHub CLI login when available. Credentials stay in process memory and are only sent to GitHub; no model API is called.

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

Git ignores named configurations in `configs/`. GUI saves also update the versioned
`conf.yaml`, which scheduled cloud runs use. Only put publicly shareable work requirements
in this file.

Changing the timezone does not change the workflow schedule. Older `default_language` configurations are migrated when loaded; saving writes only `active_language`.

## Filter by work needs and save named configurations

Add `work_requirements` to `conf.yaml`, or edit its YAML field in the GUI:

```yaml
work_requirements:
  enabled: true
  description: "Find tools for Unreal Engine performance analysis and automation"
  keywords: ["Unreal", "profiling", "performance", "性能分析"]
  exclude_keywords: ["cloud only"]
  min_matches: 1
```

`description` records your goal; the filter uses literal keywords rather than AI semantic
analysis. Matching ignores case and checks repository names, descriptions, programming
languages, README text (up to `readme.max_chars`), and available summaries. English words
use word boundaries; Chinese terms use substring matching. List translated terms and synonyms
separately. At least `min_matches` distinct keywords must match, and any exclusion vetoes a
repository. A fresh filtered run reads every Trending candidate before applying `top_n`,
preserves Trending order, and shows matched keywords in HTML and Markdown reports.
No matches produces an empty report with guidance. Set `enabled: false` for the full brief.

Saved-data generation reapplies work filters without network requests and keeps every
candidate in the JSON snapshot so you can change requirements again. It can only use saved
text; older snapshots may lack README text for some candidates. Fetch fresh data for complete
README coverage. Source-language and programming-language capture filters still require a
fresh fetch.

In the GUI, enter a **Configuration name** and click **Save named configuration** to save
the full form, including work requirements, to `configs/<name>.yaml` and `conf.yaml`.
Choose a saved configuration and click **Load configuration** to fill the form; then Save or
Generate to apply it. Reusing a name replaces that named configuration. Names support Chinese,
letters, numbers, spaces, underscores, and hyphens (1–80 characters). Saved configurations
survive restarts. The CLI can also use one directly with `--config configs/<name>.yaml`.

## How summaries work

The current bilingual notes in [summaries.yaml](summaries.yaml) were written by Codex after reading the source READMEs. Each entry is tied to a README blob SHA. It is reused only while that source version still matches.

For a new or changed README, the daily job extracts source passages and labels the selected-language summary as pending. It preserves the original language instead of claiming an automatic translation. Missing READMEs are labelled explicitly. A failed Trending fetch stops publication and preserves the existing brief.

No external model service or API key is configured. GitHub Actions does not have access to this Codex conversation. To refresh curated notes, ask Codex to read the current source README and update both languages and `readme_sha` in `summaries.yaml`; then regenerate. No unsupported model settings are included in the configuration.

## Daily automation

[Daily Trending Digest](.github/workflows/daily.yml) runs at **01:17 UTC / 09:17 Asia/Shanghai** and commits only the brief preview in the root English README or the Chinese documentation. Git ignores `output/` and the legacy root `data/` directory, so reports, archives, and JSON snapshots are no longer committed. You can also use **Actions → Daily Trending Digest → Run workflow**. It uses the repository's built-in `GITHUB_TOKEN` and requires no model secrets. To change the cloud schedule's report language, commit the updated `conf.yaml`; a local UI save does not push Git changes automatically.

Scheduled runs can be delayed; see [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Forks must enable Actions. The workflow publishes only from the default branch.

## Development

```sh
uv run --directory app ruff check .
uv run --directory app ruff format --check .
uv run --project app python -m unittest discover -s app/tests -v
```

Optional browser checks use an installed Chrome / Edge (or Playwright's Chromium):

```sh
uv run --project app --with playwright python app/tests/browser_smoke.py
uv run --project app --extra ui --with playwright python app/tests/ui_browser_smoke.py
```

For offline debugging, pass `--html path/to/trending.html --readme-dir path/to/readmes`. The README directory uses `owner/repo/README.md` plus `metadata.json` containing `sha`, `url`, and `path`. Offline generation still uses today's date.

```text
conf.yaml / summaries.yaml       Editable user configuration and curated summaries
start.bat / start.command        One-click launchers
configs/                        Named configurations (created on save)
output/reports/                 Standalone HTML editions and archive
output/daily/                   Dated Markdown issues and archive
output/data/                    JSON snapshots
output/latest.md                Latest Markdown brief
docs/                           Chinese documentation; English is in this root README
app/                            Application, tests, manifest, lockfile, environment and caches
```

## License

Code is [MIT licensed](app/LICENSE). Project names, trademarks, and third-party README content belong to their respective owners. Source links are included with each project.
