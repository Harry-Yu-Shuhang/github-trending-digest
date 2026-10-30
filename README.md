# GitHub Trending Workspace

[English](README.md) · [简体中文](docs/README.zh-CN.md)

A daily introduction to interesting open-source projects from [GitHub Trending](https://github.com/trending?since=daily). Each project gets a short explanation of **what it does** and **what stands out**, grounded in its actual README.

Choose English or Simplified Chinese with `active_language`. It controls the Gradio interface and the only report language generated on that run. Existing historical editions remain available.

<!-- digest:start -->

### 2026-10-30 · Latest brief

[Read this issue](output/daily/2026/10/2026-10-30.md) · [Previous issues](output/daily/README.md)

- **[HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor)** — An agent-native learning workspace connecting personalized tutoring, problem solving, quizzes, research, and study practice.
- **[obra/superpowers](https://github.com/obra/superpowers)** — A composable skills framework that gives coding agents a software development process, from clarifying requirements to reviewing and finishing changes.
- **[pbakaus/impeccable](https://github.com/pbakaus/impeccable)** — A design vocabulary and review toolkit that helps coding agents improve existing interfaces through targeted visual instructions.

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

The GUI shows only language, work description, **Save config**, **Load config**, and **Generate**. Saving or loading opens a small configuration panel; other settings remain in YAML and are preserved. A generated HTML report opens in your default browser. Closing the last workspace tab shuts down the backend after an 8-second grace period; refreshes and other open workspace tabs keep it alive. Use `--keep-alive` to keep a server running independently of browser tabs.

Generation shows a centered loading dialog and prevents duplicate submissions. Saving,
loading, and generation use consistent success/error dialogs; errors keep your current
description intact so you can correct settings and retry. Keyboard confirmation and Escape
work on completed dialogs; the loading dialog stays open until the operation finishes.

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

Public READMEs can be fetched without a token. Set `GITHUB_TOKEN` to avoid the lower unauthenticated GitHub API limit. The UI launcher also reuses an existing GitHub CLI login when available. GitHub credentials are only sent to GitHub. Model requests use a separate credential configured below.

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
| `summary.highlights` | Maximum model-generated highlights per project, from 1 to 5 |
| `llm` | The shared model, API endpoint, credentials, batching, and timeout |

Git ignores named configurations in `configs/`. GUI saves also update the versioned
`conf.yaml`, which scheduled cloud runs use. Only put publicly shareable work requirements
in this file.

Changing the timezone does not change the workflow schedule. Older `default_language` configurations are migrated when loaded; saving writes only `active_language`.

## Configure the shared model

The default endpoint is local Ollama. Start Ollama, run `ollama list`, and copy an installed
model's full name (including its tag) into `llm.model` in `conf.yaml`:

```yaml
llm:
  base_url: http://127.0.0.1:11434/v1
  model: ""                       # Exact installed name from `ollama list`
  api_key: ""                     # Local Ollama needs no API key
  api_key_env: ""
  timeout_seconds: 600
  batch_size: 1
  readme_max_chars: 4000
  response_format: json_object    # json_schema if supported, or text for plain JSON replies
work_requirements:
  description: ""
```

If Ollama is installed but not running, start its desktop app or run `ollama serve`.
If no models are installed, download your chosen model with `ollama pull <model:tag>` first.
The application does not download models automatically. Local inference uses the same model
for both relevance and introductions through [Ollama's compatible API](https://docs.ollama.com/api/openai-compatibility).
Keep both key fields empty for local Ollama; unrelated cloud API environment variables are ignored.
One repository per request and a longer timeout accommodate model loading and CPU inference.
If you increase `readme_max_chars` or `batch_size`, also increase Ollama's context window
using its [context settings](https://docs.ollama.com/faq#how-can-i-specify-the-context-window-size).

Other Chat Completions-compatible endpoints remain supported: change `base_url` and `model`.
For a service requiring authentication, set `api_key_env: LLM_API_KEY` and define that environment
variable, or fill `api_key`. The named environment variable takes precedence. Never commit a real key.

## Model-generated introductions and work relevance

The same configured model generates each project's introduction and highlights and, when
a work description is present, assesses practical relevance in the same request. It reads
README excerpts and considers direct tools, transferable capabilities, and concrete ways
to apply them to the user's job. Scores rank relevant projects before `top_n` is applied;
equal scores retain Trending order. Reports include the reason and suggested use case.
A score is a model assessment, not an independently verified compatibility guarantee.

Leave the description empty to disable filtering. Introductions still use the model.
Requests are batched and their IDs, scores, explanations, and summaries are validated.
Missing READMEs are marked unavailable rather than invented. API errors or incomplete
responses stop publication and preserve the previous report; there is no keyword fallback.
The description and README excerpts are sent to your configured provider. Neither model
credentials nor the complete configuration are stored in report snapshots.

Click **Save config** to save the current configuration or enter a name for `configs/<name>.yaml`.
Click **Load config** to restore `conf.yaml` or a named configuration. Hidden YAML parameters,
including model settings, stay intact. Older named profiles without `llm` inherit the
current model configuration. The CLI also accepts `--config configs/<name>.yaml`.

## Daily automation

GitHub-hosted runners cannot connect to Ollama on your computer. With the default local
endpoint (or an empty model name), the cloud workflow skips generation and publishing.
For cloud generation, configure a reachable endpoint and model, and enable its API key
environment variable if needed. Local Ollama generation remains available through the GUI or CLI.

[Daily Trending Digest](.github/workflows/daily.yml) runs at **01:17 UTC / 09:17 Asia/Shanghai** and commits only the brief preview in the root English README or the Chinese documentation. Git ignores `output/` and the legacy root `data/` directory, so reports, archives, and JSON snapshots are no longer committed. You can also use **Actions → Daily Trending Digest → Run workflow**. It uses the repository's built-in `GITHUB_TOKEN`; configure `llm.model`, the endpoint, and the repository secret `LLM_API_KEY` before enabling scheduled model generation. To change the cloud schedule's report language, commit the updated `conf.yaml`; a local UI save does not push Git changes automatically.

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
