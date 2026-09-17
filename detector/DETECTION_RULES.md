# 检测规则

## 1. 总体原则

工具检测 GitHub PR 范围内可直接观察到的编码 Agent 痕迹。任意一条已登记规则命中，该 PR 即记为 `agent_trace_detected`；否则为 `no_trace_detected`。数据本身未完成采集时输出 `unavailable`。

检测只使用已登记的启发式规则；未命中规则的内容直接忽略，不做额外语义判断。

## 2. 检测通道

只有四条通道会产生证据：

| 通道 | 检查对象 |
|---|---|
| `author_patterns` | PR 作者与每个 commit 作者 |
| `text_patterns` | PR body 与 commit message |
| `branch_patterns` | PR head branch |
| `label_patterns` | PR 当前 labels |

不检查仓库文件与配置、URL、issue / comment / review、CI 或 workflow 日志。

## 3. 匹配实现

检测器是有意保持简单的确定性引擎：

- 大小写不敏感正则；
- author / text 的每条 pattern 自动加上 ASCII token 边界，避免命中单词内部；
- 不使用 NLP、LLM、embedding、打分或阈值；
- 不存在 per-Agent 的隐藏 `if/else` 特判；
- 不解析否定语义、checkbox 状态、代码块或引用块；
- 同一处文本命中多条 pattern 时全部记录，不做最长匹配去重。

## 4. 作者身份

PR 作者与 commit 作者共用同一个 matcher。输入身份先渲染为一个字符串：

```text
login | name <email>
```

再用每条 `author_patterns` 对该字符串做查找。login 中的 GitHub `[bot]` 后缀不会被预先删除，因此以 `xxx[bot]` 形式出现的编码 Agent 账号同样可以命中。

## 5. 文本归因

PR body 与 commit message 共用同一个 matcher，逐行处理。

只做一处表示层归一化：

```text
[visible](URL) -> visible (URL)
```

URL 本身保留。原始证据文本不受影响。

一行文本只有在 Agent 名称**紧跟在全局归因语法之后**时才被接受。支持的动词：

```text
generated implemented written created built developed coded authored made produced assisted
```

支持的连接词包括 `with`、`by`、`using`、`via`、`with help from`、`with the help of`、`with assistance from`、`with the assistance of`。

`Co-Authored-By:` 是另一种全局归因前缀，没有专用解析器。`powered` 不是归因动词。

文本 `pattern` 本身决定接受哪些写法。例如：

```text
Generated with Claude Code                 # 命中 Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>   # 命中 Claude Code
Generated with Claude                      # 不命中
Generated with Gemini CLI                  # 命中 Gemini
Generated with Gemini                      # 不命中
Support Kimi Code models                   # 不命中：没有归因短语
```

## 6. branch 与 label

branch 规则是显式正则，路径边界直接写在规则里，例如：

```regex
(?:^|/)codex/
(?:^|/)trae/agent-
```

label 只对 PR 当前 labels 匹配，不追溯历史 label event。

## 7. 行为者归属

作者身份与文本证据会根据数字 actor id 区分：

- `target_author`：目标 PR 作者；
- `other_author`：PR 中其他 commit 作者；
- `unknown`：无法可靠确定行为者。

branch / label 证据单独记为 metadata，不自动归因给目标作者。

因此，`agent_trace_detected=true` 只表示 PR 范围内存在 Agent 痕迹；需要判断 PR 作者本人是否使用 Agent 时，应进一步查看 `target_author_agent_trace`。

## 8. 证据与审计

- 证据片段截断到 240 字符；
- 每条命中的 pattern 单独记录，便于核对重叠与冗余；
- 比对失败的原因不作为证据输出，工具只记录命中项。

## 9. 规则表

`config/rules/agents.json` 为编码 Agent 规则表，每个 Agent 只有四个字段：

- `author_patterns`
- `text_patterns`
- `branch_patterns`
- `label_patterns`

不同 Agent 能留下的公开痕迹并不完全相同，因此规则表中的具体 pattern 组合也不要求一致：有的 Agent 同时具有作者身份、branch 或 label 规则，有的当前主要依赖明确文本归因。检测器不据此给 Agent 分级、打置信度分数或划分类别；所有已登记规则都按同一套命中原则处理。

## 10. 范围边界

规则目录只登记作为编码 Agent 或明确 Agent 模式参与软件开发任务的工具。泛化 AI 标记以及为 Agent 提供配置同步、规格工作流或任务管理的辅助工具不作为 Agent 本体产生阳性。
