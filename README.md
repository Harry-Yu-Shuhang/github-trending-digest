# GitHub 技术快报

每天从 [GitHub Trending 日榜](https://github.com/trending?since=daily) 收集热门开源项目，生成一份可追溯、可归档的技术阅读清单。

无需大模型、付费服务或额外 API Key。Python 3.12+，使用 GitHub Actions 每天自动更新。

<!-- digest:start -->

### 2026-10-29 · 最新一期

[阅读完整快报](daily/2026/10/2026-10-29.md) · [历史归档](daily/README.md)

| 排名 | 项目 | 今日新增 Star |
| --- | --- | ---: |
| 1 | [JetBrains/thinkrail](https://github.com/JetBrains/thinkrail) | +1,068 |
| 2 | [elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills) | +2,139 |
| 3 | [obra/superpowers](https://github.com/obra/superpowers) | +1,095 |
| 4 | [HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor) | +2,371 |
| 5 | [macro-inc/macro](https://github.com/macro-inc/macro) | +117 |

<!-- digest:end -->

## 每期有什么

- 今日技术方向、主要语言和榜内日增 Star 最高项目。
- 前 10 个项目的来源链接、原文说明、Star、Fork、排名变化和试用关注点。
- 全部抓取项目的完整榜单，以及与此前最近一次同源快照的对比。
- 日期归档、最新一期入口和结构化 JSON，便于二次使用。

项目介绍保留原文，页面未提供的信息显示为缺失。技术分类来自关键词规则，试用关注点是通用建议；它们不是人工评测，也不是大模型生成的中文翻译。

## 本地运行

推荐使用 [uv](https://docs.astral.sh/uv/)：

```sh
uv sync --frozen
uv run python -m trending_digest
```

也可以使用普通 Python：

```sh
python -m venv .venv
# 激活虚拟环境后：
python -m pip install .
python -m trending_digest
```

开发检查：

```sh
uv run ruff check .
uv run ruff format --check .
uv run python -m unittest discover -s tests -v
```

## 自动更新

`.github/workflows/daily.yml` 在每天 **北京时间 09:17（UTC 01:17）** 运行，并提交当天 Markdown、JSON、归档索引和 README 摘要。GitHub 的定时任务可能延迟，不保证准点执行。

推送到自己的公开仓库后，在 **Actions → Daily Trending Digest → Run workflow** 可以立即生成一期。工作流仅需仓库自带的 `GITHUB_TOKEN`，已在 YAML 中声明 `contents: write`；无需添加个人 Token。如果仓库策略禁止写入，需要在仓库 Actions 设置中允许工作流写入。

Fork 后需要在 Actions 页面启用工作流。公开仓库长期没有活动时，GitHub 可能停用定时任务；请查看 [官方调度说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。手动运行仅允许默认分支，避免从其他分支提交到 main。

CI 在每次 push 和 pull request 时进行离线测试及代码检查。每日生成失败时工作流返回失败，不提交部分结果；可以从 Actions 日志排查并手动重跑。

## 配置

修改 `config.json`：

```json
{
  "language": "",
  "spoken_language": "",
  "top_n": 10,
  "timezone": "Asia/Shanghai"
}
```

| 字段 | 说明 |
| --- | --- |
| `language` | 编程语言筛选，空字符串表示所有语言，例如 `python`、`rust`、`c++` |
| `spoken_language` | 项目描述语言筛选，空字符串表示全部，例如 `zh`、`en` |
| `top_n` | 展开解读的项目数量，1–25；完整榜单仍保存所有抓取结果 |
| `timezone` | 快报日期和时间的时区；修改此值不会改变工作流的 cron 时间 |

每次读取 GitHub 日榜当前页面。切换语言后，仅与相同来源 URL 的旧快照比较。GitHub 通常返回最多约 25 个项目，以实际页面为准。

调试解析可以使用 `uv run python -m trending_digest --html path/to/trending.html`。该选项仍按当前时间生成文件，不能用于历史日期回填。对同一天重跑会替换当天快照，历史日期保留。

## 文件布局

```text
latest.md                     最新完整快报
daily/README.md               历史索引
daily/YYYY/MM/YYYY-MM-DD.md    每日 Markdown
data/YYYY/MM/YYYY-MM-DD.json   结构化数据、来源和采集时间
trending_digest/              抓取、解析、渲染和命令行
tests/                        离线页面样本和回归测试
.github/workflows/            每日更新及 CI
```

JSON 中 `stars_today` 直接取自 Trending 页面的 `stars today`，不是采样间差值。所有排名按页面顺序保存。“新入榜”只表示相较上一次采集快照未出现，不代表项目首次登榜。缺失数字为 `null`，不会伪造为 0。

## 参与贡献与许可证

欢迎通过 Issue 或 Pull Request 改进解析、分类与快报格式。页面结构发生变化时，请附上最小 HTML 样本，并为解析行为增加离线测试。

代码使用 [MIT License](LICENSE)。仓库中的第三方项目描述、商标和名称归原作者所有；项目说明与数据来源均链接至 GitHub。
