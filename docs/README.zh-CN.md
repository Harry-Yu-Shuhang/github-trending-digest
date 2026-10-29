# GitHub 技术快报

[English](../README.md) · [简体中文](README.zh-CN.md)

每天从 [GitHub Trending](https://github.com/trending?since=daily) 发现值得了解的开源项目。直接阅读各项目 README，简要介绍**这是做什么的**、**有什么亮点**。

通过 `active_language` 选择英文或简体中文，它同时控制 Gradio 界面语言和本次生成的报告语言，每次只生成所选的一种语言。已有历史报告会保留。

<!-- digest:start -->

### 2026-10-29 · 最新一期

[阅读本期](../output/daily/2026/10/2026-10-29.zh-CN.md) · [历史快报](../output/daily/README.zh-CN.md)

- **[JetBrains/thinkrail](https://github.com/JetBrains/thinkrail)** — 围绕 pi 编程智能体构建的 IDE，把代码编辑、隔离工作区和持久化项目知识放进同一个界面。
- **[elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills)** — 面向 AI 编程工具的模块化设计技能集合，适用于能够读取 Markdown 规则的智能体。
- **[obra/superpowers](https://github.com/obra/superpowers)** — 通过可组合技能，为编程智能体提供从澄清需求到审查和交付变更的软件开发流程。

<!-- digest:end -->

## 阅读快报

- **[最新 HTML 报告](../output/reports/index.html)**
- [最新 Markdown 报告](../output/latest.md)
- [快报归档](../output/daily/README.md)

每个项目包含用途概括、最多三项亮点、来源 README 链接，以及简短的编程语言和 Star 数据。默认介绍日榜全部项目，最多 25 个，也可通过 `top_n` 减少数量。

HTML 阅读版包含跳转目录、全文搜索、编程语言筛选、深色模式和打印 / PDF 样式，并适配手机屏幕。每个文件都内嵌样式和脚本，可直接从本地打开。在浏览器中打开 `output/reports/index.html`；GitHub 文件页展示的是 HTML 源码。最新入口和归档页采用当前所选语言，按日期归档的文件保留语言标识；选择中文后不会重写已有英文历史报告。

## 一键启动配置界面

- **Windows：** 双击 `start.bat`。
- **macOS：** 双击 `start.command`，或在终端执行 `sh start.command`。
- **统一入口：** 两个平台的包装脚本准备相同环境，最终运行同一个 `app/start.py`。

启动脚本会在需要时安装 uv，准备 Python 3.12 和可选的界面依赖，并在浏览器打开 `http://127.0.0.1:7860`。首次运行需要联网。关闭终端或按 Ctrl+C 可以停止服务。若下载 ZIP 后 macOS 丢失可执行权限，可直接使用 `sh start.command`。

响应式表单可以编辑 `conf.yaml` 的全部设置。切换语言会立即翻译界面，并保留尚未保存的输入。“保存配置”会验证并保存设置；“抓取并生成报告”会保存表单后重新抓取 Trending 和 README；“用已保存数据生成”会保存表单并使用最近一次采集数据，不发起新的网络请求，来源筛选和采集时间仍沿用原数据。生成后可以在界面中预览并下载 HTML 报告。

默认从 7860 开始寻找可用端口；被占用时自动尝试 7861、7862 等，并打开实际选中的地址。
`--port` 用于指定固定端口；环境变量 `GRADIO_SERVER_PORT` 可修改自动选择的起始端口。

指定其他端口，或不自动打开浏览器：

```sh
uv run --project app --frozen --extra ui --python 3.12 python app/start.py --port 7861 --no-browser
```

## 本地运行

以下命令均在仓库根目录执行。程序与依赖放在 `app/`，生成的报告、归档和快照放在 `output/`。

需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

```sh
uv sync --project app --frozen
uv run --project app python -m trending_digest
```

读取公开 README 不强制要求 Token。可通过环境变量 `GITHUB_TOKEN` 提高 GitHub API 限额；界面启动时也会在可用时复用已有 GitHub CLI 登录。凭据仅在进程内存中使用，只发往 GitHub，不写入配置，也不调用模型服务。

## 配置

统一使用 [conf.yaml](../conf.yaml)，原来的 `config.json` 已替换。

| 配置项 | 说明 |
| --- | --- |
| `active_language` | 界面与报告语言：`en` 或 `zh-CN`；每次只生成这一种语言 |
| `programming_language` | Trending 编程语言筛选，留空表示全部 |
| `spoken_language` | Trending 项目描述语言筛选，留空表示全部 |
| `top_n` | 每期介绍的项目数量，1–25 |
| `timezone` | 快报日期与采集时间的时区 |
| `readme` | 请求超时、抓取并发数和摘录输入长度 |
| `summary.mode` | `curated` 优先使用已整理的双语摘要；`extractive` 只摘录原文 |
| `summary.curated_file` | 保存有版本绑定的项目摘要文件 |
| `summary.highlights` | 每个项目最多展示几条亮点，1–5 |
| `summary.fallback` | 当前为 `extractive`；新增或有变化的 README 使用带标记的原文摘录 |

修改时区不会改变工作流的执行时间。旧的 `default_language` 配置会在读取时迁移，保存后只保留 `active_language`。

## 按工作需求筛选与命名配置

在 `conf.yaml` 中填写 `work_requirements`，GUI 会读取并提供 YAML 编辑框：

```yaml
work_requirements:
  enabled: true
  description: "寻找适用于 Unreal Engine 性能分析与自动化的工具"
  keywords: ["Unreal", "profiling", "performance", "性能分析"]
  exclude_keywords: ["cloud only"]
  min_matches: 1
```

`description` 用来记录工作目标，实际按关键词匹配，不调用模型进行语义分析。
匹配范围包括仓库名称、介绍、编程语言、README 文本（受 `readme.max_chars` 限制）和已有摘要。
忽略大小写；英文单词按边界匹配，中文按子串匹配，中英文同义词请分别填写。
至少命中 `min_matches` 个不同关键词，命中任一排除词则排除。
启用筛选后，新抓取会读取全部 Trending 候选仓库的 README，再按 `top_n` 截取匹配结果，
保留原榜单顺序。HTML 和 Markdown 报告会展示匹配词；没有匹配结果时会明确提示。
设为 `enabled: false` 可恢复完整快报。

“用已保存数据生成”可以离线重新应用工作需求筛选。快照保留全部候选仓库，便于反复切换需求；
只能匹配已保存的文本，旧快照可能缺少部分仓库的 README，重新抓取可获得更完整的匹配依据。
来源的编程语言和描述语言筛选仍需重新抓取才会生效。

GUI 中填写“配置名称”，点击“保存命名配置”，会把完整表单（含工作需求）保存到
`configs/<名称>.yaml`，同时更新 `conf.yaml`。选择已保存的配置后点击“加载配置”，即可填充表单，
再点击保存或生成后应用。同名保存会覆盖原命名配置；名称支持中文、字母、数字、空格、下划线
和连字符，长度为 1–80 个字符。重启后仍可加载。命令行也可用 `--config configs/<名称>.yaml`
直接指定一套配置。

## 摘要如何生成

[summaries.yaml](../summaries.yaml) 中的本期双语内容，由 Codex 阅读项目 README 后整理。每项摘要都绑定原始 README 的 blob SHA，仅在源版本相同时复用。

对新增或 README 已变化的项目，每日任务摘录来源段落并标明**当前语言摘要待补充**，保留原文语言，不冒充自动翻译。README 无法读取时明确标记。Trending 抓取失败时停止发布，保留已有快报。

当前不配置外部模型服务或 API Key，GitHub Actions 也不能直接访问本次 Codex 对话。需要刷新摘要时，可让 Codex 阅读当前 README，同时更新 `summaries.yaml` 中的中英文内容和 `readme_sha`，然后重新生成。配置文件中没有尚未实现的模型参数。

## 每日自动更新

[每日工作流](../.github/workflows/daily.yml) 计划在**北京时间 09:17 / UTC 01:17** 执行，仅提交根目录英文 README 或中文文档中的快报预览更新；`output/` 和旧的根目录 `data/` 已被 Git 忽略，不再提交报告、归档和 JSON 快照。也可以在 **Actions → Daily Trending Digest → Run workflow** 手动运行。仅使用仓库自带的 `GITHUB_TOKEN`，无需模型密钥。云端运行使用仓库里已提交的 `conf.yaml`；本地界面保存配置不会自动推送 Git 变更。

定时任务可能延迟，参见 [GitHub 调度说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。Fork 后需要启用 Actions，发布任务仅允许默认分支运行。

## 开发检查

```sh
uv run --directory app ruff check .
uv run --directory app ruff format --check .
uv run --project app python -m unittest discover -s app/tests -v
```

可选的浏览器检查使用本机 Chrome / Edge，或已安装的 Playwright Chromium：

```sh
uv run --project app --with playwright python app/tests/browser_smoke.py
uv run --project app --extra ui --with playwright python app/tests/ui_browser_smoke.py
```

离线调试可指定 `--html path/to/trending.html --readme-dir path/to/readmes`。README 目录按 `owner/repo/README.md` 组织，同目录的 `metadata.json` 包含 `sha`、`url`、`path`。离线生成仍使用当天日期。

```text
conf.yaml / summaries.yaml       用户配置与人工摘要
start.bat / start.command        一键启动脚本
configs/                        GUI 命名配置（首次保存后创建）
output/reports/                 HTML 报告与归档
output/daily/                   Markdown 快报与归档
output/data/                    JSON 快照
output/latest.md                最新 Markdown 快报
docs/                           中文说明，英文默认展示在根目录 README.md
app/                            程序、测试、依赖清单、运行环境与缓存
```

## 许可证

代码使用 [MIT License](../app/LICENSE)。第三方项目名称、商标和 README 内容归原作者所有，每个项目均附来源链接。
