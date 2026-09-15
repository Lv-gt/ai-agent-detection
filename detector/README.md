# 🤖 PR Agent Detector

离线、可审计的 GitHub Pull Request 编码 Agent 痕迹检测工具。工具只读取已经采集好的 SQLite 数据库。

## 检测范围

主要检测：

- PR 作者与 commit 作者中的已知 Agent 身份；
- PR body 与 commit message 中的 `Co-Authored-By:` Agent；
- PR body 与 commit message 中明确的 Agent 使用声明；自由文本只接受明确的编码 Agent / Agent 模式名称，不把裸模型名、泛化 AI 标记或 Agent 辅助工具自动视为 Agent；
- PR body 与 commit message 中已登记的 Agent 任务链接；
- PR head branch 与当前 labels 中的 Agent 规则。

工具同时区分痕迹属于目标 PR 作者、其他 commit 作者、未知行为者，还是仅来自 branch/label 元数据。


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

检测完成后，可将结果导出为便于分析和人工检查的文件：

```bash
python scripts/cli.py export <output_dir>
```

例如：

```bash
python scripts/cli.py export "F:\data\agent_detection_result"
```

### 可选功能

如只希望在正式运行前检查输入数据库，可以执行：

```bash
python scripts/cli.py preflight <input>
```

如需要在检测完成后重新执行结果一致性审计，可以执行：

```bash
python scripts/cli.py audit <output_dir>
```

检测命令还支持以下可选参数：

* `--workers N`：并行处理进程数，默认值为 `4`。
* `--shard-size N`：每个处理分片包含的 PR 数，默认值为 `500`。
* `--sample-size N`：仅检测前 N 个可处理 PR，可用于快速测试。
* `--deep-check`：在运行前额外执行 SQLite 完整性检查。

例如，使用 8 个并行进程运行：

```bash
python scripts/cli.py detect <input> <output_dir> --workers 8
```

例如，只抽样检测 100 个 PR：

```bash
python scripts/cli.py detect <input> <output_dir> --sample-size 100
```

通常情况下，直接使用默认参数即可：

```bash
python scripts/cli.py detect <input> <output_dir>
python scripts/cli.py export <output_dir>
```

## 输出

- `detection.sqlite3`：PR 结果与逐条证据；
- `audit.json`：结果一致性审计；
- `run_context.json`：本次运行使用的规则快照与输入信息；
- `exports/pr_labels.csv.gz`：PR 级结果；
- `exports/evidence.jsonl.gz`：逐条检测证据；
- `exports/tool_catalog.json`：Agent 规则目录；
- `exports/rule_contributions.json`：各规则命中的 PR 数。

规则配置位于 `config/rules/`。检测规则见 `DETECTION_RULES.md`，输入接口见 `INPUT_SCHEMA.md`。
