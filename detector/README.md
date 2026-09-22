# 🤖 PR Agent Detector V1.41

离线、可审计的 GitHub Pull Request 编码 Agent 痕迹检测工具。工具只读取已经采集好的 SQLite 数据库，不使用 LLM、embedding、NLP 或置信度打分。

## 检测范围

检测覆盖三类证据：

- **身份声明（Identity）**
  - PR 作者身份；
  - commit 作者身份；
  - PR body 中的 Agent attribution；
  - commit message 中的 Agent attribution；
  - 少量已登记的结构化 commit-message 身份声明。
- **Branch**：PR head branch；
- **Label**：PR 当前 labels。

Author 与正文 attribution 使用两张独立但允许重叠的证据表。PR 作者和 commit 作者仍统一拼成：

```text
login | name <email>
```

随后只使用 Author 侧正则表扫描这个完整字符串。

PR body 与 commit message 不直接全文搜索 Agent 名称，而是先识别 attribution grammar，再在前缀之后、当前句子或分句结束之前的片段中搜索正文侧规则。例如：

```text
Generated with Claude Code
Generated-by: ZCode
Co-authored with Kiro
Co authored by Kiro
Co-developed-by: Qoder <noreply@qoder.com>
Authored with assistance from Codex
Built with the help of Augment Code
```

冒号、辅助短语及其他片段内容不需要单独配置，正文规则可以出现在该有界片段中的任意位置。

另有两类结构化 commit-message 身份声明：

```text
🤖 Plandex → <summary>
Replit-Commit-Author: Agent
```

它们只扫描 commit message，在检测结论中仍属于 Identity 类证据。Aider 的 `(aider)` 形式仍按 Author 规则处理。

任意一类证据命中，该 PR 即记为 `agent_trace_detected`；否则为 `no_trace_detected`；数据本身未完成采集时输出 `unavailable`。

PR 的 `tools` 使用集合语义，同一 Agent 多次命中仍只列出一次。`evidence_count` 仅用于核对证据行，不参与分类、权重或使用强度计算。

工具同时区分 Identity 证据属于目标 PR 作者、其他 commit 作者还是未知行为者；Branch / Label 单独记为 metadata 证据。

## 🚀 使用

Python 3.10+，无第三方运行时依赖。

### 执行检测

传入已经采集好的 SQLite 数据库或包含 `pr_agent_inputs.sqlite3` 的目录，并指定结果输出目录：

```bash
python scripts/cli.py detect <input> <output_dir>
```

例如：

```bash
python scripts/cli.py detect "F:\data\pr_agent_inputs" "F:\data\agent_detection_result"
```

检测过程中会自动完成输入检查、分片处理、结果合并和一致性审计。若运行中断，在输入数据、规则和运行参数未发生变化的情况下，重新执行相同命令即可继续复用已经完成且校验通过的分片。

### 导出结果

```bash
python scripts/cli.py export <output_dir>
```

### 可选功能

```bash
python scripts/cli.py preflight <input>
python scripts/cli.py audit <output_dir>
```

检测命令支持：

- `--workers N`：并行处理进程数，默认 `4`；
- `--shard-size N`：每个分片的 PR 数，默认 `500`；
- `--sample-size N`：仅检测前 N 个可处理 PR；
- `--deep-check`：运行前额外执行 SQLite `quick_check`。

## 输出

- `detection.sqlite3`：PR 结果与逐条证据；
- `audit.json`：结果一致性审计；
- `run_context.json`：本次运行使用的规则快照与输入信息；
- `exports/pr_results.csv.gz`：PR 级结果；
- `exports/evidence.jsonl.gz`：逐条检测证据；
- `exports/tool_catalog.json`：Agent 规则目录；
- `exports/rule_contributions.json`：各检测机制命中的 PR 数；
- `exports/export_summary.json`：导出对应的审计摘要。

## 规则维护

`config/rules/agents.json` 是检测规则的唯一机器事实源，当前包含：

```text
56 Agents
89 Author patterns
156 Text attribution patterns
62 patterns shared by both sides
13 Branch patterns
2 Label patterns
2 Raw message signatures
262 executable pattern instances in total
```

README、`DETECTION_RULES.md`、`AGENT_RULES.md` 只用于说明和交付，不参与规则加载。

修改 `agents.json` 后，执行 `python scripts/render_rule_docs.py` 重新生成 `AGENT_RULES.md`；README 与 `DETECTION_RULES.md` 中的库存数字为手工维护，需一并更新。

输入接口见 `INPUT_SCHEMA.md`。
