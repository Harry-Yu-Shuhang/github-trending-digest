# GitHub Tech Brief

[English](README.md) · [简体中文](README.zh-CN.md)

A daily introduction to interesting open-source projects from [GitHub Trending](https://github.com/trending?since=daily). Each project gets a short explanation of **what it does** and **what stands out**, grounded in its actual README.

English is the default. Every issue and archive has a Simplified Chinese counterpart. There is no full leaderboard or generic advice section.

<!-- digest:start -->

### 2026-10-29 · Latest brief

[Read this issue](daily/2026/10/2026-10-29.md) · [Previous issues](daily/README.md)

- **[JetBrains/thinkrail](https://github.com/JetBrains/thinkrail)** — An agent-focused IDE built around the pi coding agent, combining code editing, isolated workspaces, and durable project knowledge.
- **[elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills)** — A modular collection of design skills for AI coding tools that can read Markdown rules.
- **[obra/superpowers](https://github.com/obra/superpowers)** — A composable skills framework that gives coding agents a software development process, from clarifying requirements to reviewing and finishing changes.

<!-- digest:end -->

## Read the brief

- [Latest issue in English](latest.md) · [中文快报](latest.zh-CN.md)
- [Issue archive](daily/README.md) · [中文归档](daily/README.zh-CN.md)

Project cards contain a concise purpose, up to three highlights, a link to the source README, and a small language / star line. All current Trending projects are covered by default, up to 25; `top_n` can reduce that number.

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
| `default_language` | Default README / report filenames; currently `en` |
| `languages` | Output languages, currently `en` and `zh-CN` |
| `programming_language` | Trending programming-language filter; empty means all |
| `spoken_language` | Trending description-language filter; empty means all |
| `top_n` | Number of project cards, from 1 to 25 |
| `timezone` | Issue date and capture timestamp timezone |
| `readme` | Request timeout, fetch concurrency, and excerpt input limit |
| `summary.mode` | `curated` to prefer saved bilingual summaries, or `extractive` for source excerpts |
| `summary.curated_file` | Path to the versioned summary collection |
| `summary.highlights` | Maximum highlights per project, from 1 to 5 |
| `summary.fallback` | Currently `extractive`; new or changed sources get labelled excerpts |

Changing the timezone does not change the workflow schedule.

## How summaries work

The current bilingual notes in [summaries.yaml](summaries.yaml) were written by Codex after reading the source READMEs. Each entry is tied to a README blob SHA. It is reused only while that source version still matches.

For a new or changed README, the daily job extracts source passages and labels them **bilingual summary pending**. It preserves the original language instead of claiming an automatic translation. Missing READMEs are labelled explicitly. A failed Trending fetch stops publication and preserves the existing brief.

No external model service or API key is configured. GitHub Actions does not have access to this Codex conversation. To refresh curated notes, ask Codex to read the current source README and update both languages and `readme_sha` in `summaries.yaml`; then regenerate. No unsupported model settings are included in the configuration.

## Daily automation

[Daily Trending Digest](.github/workflows/daily.yml) runs at **01:17 UTC / 09:17 Asia/Shanghai** and commits both languages, archives, and JSON snapshots. You can also use **Actions → Daily Trending Digest → Run workflow**. It uses the repository's built-in `GITHUB_TOKEN` and requires no model secrets.

Scheduled runs can be delayed; see [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Forks must enable Actions. The workflow publishes only from the default branch.

## Development

```sh
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
```

For offline debugging, pass `--html path/to/trending.html --readme-dir path/to/readmes`. The README directory uses `owner/repo/README.md` plus `metadata.json` containing `sha`, `url`, and `path`. Offline generation still uses today's date.

```text
README.md / README.zh-CN.md       English and Chinese documentation
latest.md / latest.zh-CN.md       Latest project briefs
daily/YYYY/MM/                   Dated English / Chinese issues
data/YYYY/MM/YYYY-MM-DD.json      Shared source metadata and bilingual summaries
conf.yaml                        Public configuration
summaries.yaml                   Versioned, curated project summaries
trending_digest/                 Fetching, extraction, localization, and CLI
```

## License

Code is [MIT licensed](LICENSE). Project names, trademarks, and third-party README content belong to their respective owners. Source links are included with each project.
