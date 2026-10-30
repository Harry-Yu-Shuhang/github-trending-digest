# GitHub 技术快报

[English](../README.md) · [简体中文](README.zh-CN.md)

每天从 [GitHub Trending](https://github.com/trending?since=daily) 发现值得了解的开源项目。直接阅读各项目 README，简要介绍**这是做什么的**、**有什么亮点**。

通过 `active_language` 选择英文或简体中文，它同时控制 Gradio 界面语言和本次生成的报告语言，每次只生成所选的一种语言。已有历史报告会保留。

<!-- digest:start -->

### 2026-10-29 · 最新一期

[阅读本期](../output/daily/2026/10/2026-10-29.zh-CN.md) · [历史快报](../output/daily/README.md)

- **[obra/superpowers](https://github.com/obra/superpowers)** — 通过可组合技能，为编程智能体提供从澄清需求到审查和交付变更的软件开发流程。
- **[HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor)** — 以智能体为核心的学习工作区，把个性化辅导、解题、测验、研究和学习练习连接起来。
- **[pbakaus/impeccable](https://github.com/pbakaus/impeccable)** — 为编程智能体提供设计词汇和审查工具，通过明确的视觉指令改进已有界面。

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

主界面只保留语言、工作描述，以及“保存配置”“加载配置”“生成报告”三个按钮。保存、加载时才展开名称或列表；其他参数留在 YAML 中并完整保留。生成成功后在默认浏览器打开 HTML。最后一个工作台标签页关闭后，后端等待 8 秒自动退出；刷新页面或仍有其他工作台标签页时保持运行。可用 `--keep-alive` 让服务独立于浏览器运行。

默认从 7860 开始寻找可用端口；被占用时自动尝试 7861、7862 等，并打开实际选中的地址。
`--port` 用于指定固定端口；环境变量 `GRADIO_SERVER_PORT` 可修改自动选择的起始端口。

生成时立即显示居中的加载弹窗，避免重复提交；保存、加载和生成操作完成后统一显示成功或错误弹窗。
错误不会清空已填写的描述，关闭提示后可修改配置并重试。完成后的弹窗支持键盘确认和 Escape 关闭；
加载弹窗会保持到操作完成。

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

读取公开 README 不强制要求 Token。可通过环境变量 `GITHUB_TOKEN` 提高 GitHub API 限额；界面启动时也会在可用时复用已有 GitHub CLI 登录。GitHub 凭据只发往 GitHub；模型接口使用下面单独配置的密钥。

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
| `summary.highlights` | 每个项目最多展示几条亮点，1–5 |

修改时区不会改变工作流的执行时间。旧的 `default_language` 配置会在读取时迁移，保存后只保留 `active_language`。

## 配置同一个大模型

默认连接本机 Ollama。先启动 Ollama，运行 `ollama list`，将已安装模型的完整名称
（包括标签）填入 `conf.yaml` 的 `llm.model`：

```yaml
llm:
  base_url: http://127.0.0.1:11434/v1
  model: ""                       # `ollama list` 显示的完整模型名称
  api_key: ""                     # 本地 Ollama 不需要密钥
  api_key_env: ""
  timeout_seconds: 600
  batch_size: 1
  readme_max_chars: 4000
  response_format: json_object    # 支持时可用 json_schema，不支持 JSON 模式则填 text
work_requirements:
  description: ""
```

已安装但未启动时，打开 Ollama 桌面应用或运行 `ollama serve`。
尚未安装模型时，先通过 `ollama pull <模型名:标签>` 下载自己选择的模型；
本程序不会自动下载模型。筛选与介绍通过 [Ollama 兼容接口](https://docs.ollama.com/api/openai-compatibility)
调用同一个本地模型。两个密钥字段均留空即可，不会读取其他云端密钥环境变量。
默认每次处理一个仓库，并延长超时，适应模型首次加载和 CPU 推理。
如果增加 `readme_max_chars` 或 `batch_size`，也应通过
[Ollama 上下文设置](https://docs.ollama.com/faq#how-can-i-specify-the-context-window-size)
增加模型的上下文长度。

仍可切换到其他 Chat Completions 兼容服务，修改 `base_url` 和 `model` 即可。
需要认证时，设置 `api_key_env: LLM_API_KEY` 并定义该环境变量，或填写 `api_key`；
指定的环境变量优先。不要把真实密钥提交到受版本管理的 `conf.yaml`。

## 大模型介绍与工作相关性

同一个模型在同次请求中，根据 README 生成仓库介绍、亮点，并结合工作描述判断相关性。
它会考虑直接适用的工具、可迁移的通用能力，以及具体工作中的使用方式，
不要求仓库出现某个固定关键词。报告展示模型评分、适用理由和使用建议；
按评分排序后再按 `top_n` 截取，同分保留 Trending 顺序。
评分是模型判断，不代表已经实测兼容。

工作描述留空自动关闭筛选，但仓库介绍仍调用模型。请求按批次发送，并校验返回的仓库 ID、
分数、理由和摘要。README 缺失时标为不可用，不编造介绍。
接口失败、拒绝或返回不完整时会提示错误，保留原报告，不会偷偷退回关键词筛选。
工作描述和 README 摘录会发送到配置的模型服务；报告快照不保存密钥或整份配置。

点击“保存配置”可保存当前配置，也可命名保存到 `configs/<名称>.yaml`；
点击“加载配置”选择 `conf.yaml` 或命名配置。语言、抓取参数和模型设置等隐藏参数会完整保留。
旧命名配置没有 `llm` 时沿用当前模型配置。命令行也可用 `--config configs/<名称>.yaml`。

## 每日自动更新

GitHub 托管运行器无法访问你电脑上的 Ollama。默认本机地址或模型名称为空时，
云端工作流会跳过生成和发布。需要云端生成时，配置运行器可访问的接口和模型，
如需认证再启用密钥环境变量。本地 Ollama 仍可通过 GUI 或命令行生成报告。

[每日工作流](../.github/workflows/daily.yml) 计划在**北京时间 09:17 / UTC 01:17** 执行，仅提交根目录英文 README 或中文文档中的快报预览更新；`output/` 和旧的根目录 `data/` 已被 Git 忽略，不再提交报告、归档和 JSON 快照。也可以在 **Actions → Daily Trending Digest → Run workflow** 手动运行。抓取使用仓库自带的 `GITHUB_TOKEN`；启用定时生成前需配置模型 ID、接口地址和仓库 Secret `LLM_API_KEY`。云端运行使用仓库里已提交的 `conf.yaml`；本地界面保存配置不会自动推送 Git 变更。

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
