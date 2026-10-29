# GitHub 技术快报

[English](README.md) · [简体中文](README.zh-CN.md)

每天从 [GitHub Trending](https://github.com/trending?since=daily) 发现值得了解的开源项目。直接阅读各项目 README，简要介绍**这是做什么的**、**有什么亮点**。

默认展示英文，同时提供简体中文 README、快报和归档。已移除完整榜单及通用试用建议。

<!-- digest:start -->

### 2026-10-29 · 最新一期

[阅读本期](daily/2026/10/2026-10-29.zh-CN.md) · [历史快报](daily/README.zh-CN.md)

- **[JetBrains/thinkrail](https://github.com/JetBrains/thinkrail)** — 围绕 pi 编程智能体构建的 IDE，把代码编辑、隔离工作区和持久化项目知识放进同一个界面。
- **[elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills)** — 面向 AI 编程工具的模块化设计技能集合，适用于能够读取 Markdown 规则的智能体。
- **[obra/superpowers](https://github.com/obra/superpowers)** — 通过可组合技能，为编程智能体提供从澄清需求到审查和交付变更的软件开发流程。

<!-- digest:end -->

## 阅读快报

- [最新中文快报](latest.zh-CN.md) · [English brief](latest.md)
- [中文归档](daily/README.zh-CN.md) · [English archive](daily/README.md)

每个项目包含用途概括、最多三项亮点、来源 README 链接，以及简短的编程语言和 Star 数据。默认介绍日榜全部项目，最多 25 个，也可通过 `top_n` 减少数量。

## 本地运行

需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

```sh
uv sync --frozen
uv run python -m trending_digest
```

读取公开 README 不强制要求 Token。可通过环境变量 `GITHUB_TOKEN` 提高 GitHub API 限额；此 Token 仅发往 GitHub，不调用模型服务。

## 配置

统一使用 [conf.yaml](conf.yaml)，原来的 `config.json` 已替换。

| 配置项 | 说明 |
| --- | --- |
| `default_language` | 默认 README 和快报文件名对应的语言，当前为 `en` |
| `languages` | 输出语言，当前为 `en` 和 `zh-CN` |
| `programming_language` | Trending 编程语言筛选，留空表示全部 |
| `spoken_language` | Trending 项目描述语言筛选，留空表示全部 |
| `top_n` | 每期介绍的项目数量，1–25 |
| `timezone` | 快报日期与采集时间的时区 |
| `readme` | 请求超时、抓取并发数和摘录输入长度 |
| `summary.mode` | `curated` 优先使用已整理的双语摘要；`extractive` 只摘录原文 |
| `summary.curated_file` | 保存有版本绑定的项目摘要文件 |
| `summary.highlights` | 每个项目最多展示几条亮点，1–5 |
| `summary.fallback` | 当前为 `extractive`；新增或有变化的 README 使用带标记的原文摘录 |

修改时区不会改变工作流的执行时间。

## 摘要如何生成

[summaries.yaml](summaries.yaml) 中的本期双语内容，由 Codex 阅读项目 README 后整理。每项摘要都绑定原始 README 的 blob SHA，仅在源版本相同时复用。

对新增或 README 已变化的项目，每日任务摘录来源段落并标明**中英文概括待补充**，保留原文语言，不冒充自动翻译。README 无法读取时明确标记。Trending 抓取失败时停止发布，保留已有快报。

当前不配置外部模型服务或 API Key，GitHub Actions 也不能直接访问本次 Codex 对话。需要刷新摘要时，可让 Codex 阅读当前 README，同时更新 `summaries.yaml` 中的中英文内容和 `readme_sha`，然后重新生成。配置文件中没有尚未实现的模型参数。

## 每日自动更新

[每日工作流](.github/workflows/daily.yml) 计划在**北京时间 09:17 / UTC 01:17** 执行，并提交中英文快报、归档与 JSON 数据。也可以在 **Actions → Daily Trending Digest → Run workflow** 手动运行。仅使用仓库自带的 `GITHUB_TOKEN`，无需模型密钥。

定时任务可能延迟，参见 [GitHub 调度说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。Fork 后需要启用 Actions，发布任务仅允许默认分支运行。

## 开发检查

```sh
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
```

离线调试可指定 `--html path/to/trending.html --readme-dir path/to/readmes`。README 目录按 `owner/repo/README.md` 组织，同目录的 `metadata.json` 包含 `sha`、`url`、`path`。离线生成仍使用当天日期。

```text
README.md / README.zh-CN.md       英文与中文说明
latest.md / latest.zh-CN.md       最新一期快报
daily/YYYY/MM/                   按日期归档的中英文快报
data/YYYY/MM/YYYY-MM-DD.json      共享来源元数据与双语内容
conf.yaml                        公开配置
summaries.yaml                   绑定 README 版本的项目摘要
trending_digest/                 抓取、摘录、多语言渲染和命令行
```

## 许可证

代码使用 [MIT License](LICENSE)。第三方项目名称、商标和 README 内容归原作者所有，每个项目均附来源链接。
