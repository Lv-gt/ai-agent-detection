# 编码 Agent 规则清单

`config/rules/agents.json` 的可读版本。每个 Agent 只有四条通道的规则，`—` 表示该通道当前没有已登记的规则。

- Agent 总数：**57**
- 至少有一条规则：**49**
- 四条通道均为空、仅保留在清单中：**8**
- 规则总数：**A=35 / T=86 / B=11 / L=1**

四条通道均为空的条目：Baidu Comate、DeepSeek Harness、MiMo Code、MiniMax Code、Plandex、Verdent、Huawei CodeArts、iFlow CLI。

| # | Agent | A — Author identity | T — Text attribution | B — Branch | L — Label |
|---:|---|---|---|---|---|
| 1 | **Abacus** | — | `Abacus\.AI CLI <agent@abacus\.ai>` | — | — |
| 2 | **Aider** | `\(aider\)` | `Aider .*<aider@aider\.chat>` | — | — |
| 3 | **Alibaba Lingma** | — | `Lingma` | — | — |
| 4 | **Amazon Q** | `amazon-q-developer\[bot\]` | `Amazon Q Developer`<br>`amazon-q-developer\[bot\] <208079219\+amazon-q-developer\[bot\]@users\.noreply\.github\.com>` | — | — |
| 5 | **Amp** | `ampagent`<br>`amp@ampcode\.com` | `Amp`<br>`Amp <amp@ampcode\.com>` | — | — |
| 6 | **Atlassian Rovo Dev** | — | `Rovo Dev`<br>`Rovodev` | `(?:^|/)rovodev/` | — |
| 7 | **Augment Code** | — | `Augment Code`<br>`Augment Agent`<br>`Augment (?:Code|Agent) <[^>]+@augmentcode\.com>` | — | — |
| 8 | **Baidu Comate** | — | — | — | — |
| 9 | **Brokk** | — | `Brokk AI` | — | — |
| 10 | **Charlie** | — | `CharlieHelps <charlie@charlielabs\.ai>` | — | — |
| 11 | **Claude Code** | `Claude (?:Opus|Sonnet|Haiku|Fable)[^<]*<noreply@anthropic\.com>`<br>`Claude\s*<noreply@anthropic\.com>`<br>`Claude[^<]*<claude@anthropic\.com>` | `Claude Code`<br>`Claude (?:Opus|Sonnet|Haiku|Fable)[^<]*<noreply@anthropic\.com>`<br>`Claude\s*<noreply@anthropic\.com>` | `(?:^|/)claude/` | — |
| 12 | **Cline** | — | `Cline` | — | — |
| 13 | **CodeBuddy** | — | `CodeBuddy`<br>`CodeBuddy Code`<br>`CodeBuddy(?: Code)? <(?:noreply@tencent\.com|noreply@codebuddy\.ai|noreply@cnb\.cool|noreply@codebuddy\.dev)>` | — | — |
| 14 | **Codegen** | `codegen-sh\[bot\]` | `codegen-sh\[bot\] <131295404\+codegen-sh\[bot\]@users\.noreply\.github\.com>` | — | — |
| 15 | **Codex** | `codex@openai\.com` | `Codex`<br>`OpenAI Codex`<br>`(?:OpenAI )?Codex <(?:codex|noreply)@openai\.com>` | `(?:^|/)codex/` | `^codex$` |
| 16 | **Continue** | `Continue <noreply@continue\.dev>` | `Continue`<br>`Continue <noreply@continue\.dev>` | — | — |
| 17 | **Copilot** | `copilot-swe-agent(?:\[bot\])?`<br>`Copilot <[0-9]+\+Copilot@users\.noreply\.github\.com>`<br>`(?:GitHub )?Copilot <copilot@github\.com>` | `Copilot`<br>`Copilot <[0-9]+\+Copilot@users\.noreply\.github\.com>`<br>`(?:GitHub )?Copilot <copilot@github\.com>` | `(?:^|/)copilot/` | — |
| 18 | **Crush** | — | `Crush`<br>`Crush <crush@charm\.land>` | — | — |
| 19 | **Cursor** | `cursoragent@cursor\.com` | `Cursor(?!\s+Bugbot\b)`<br>`Cursor(?: Agent)? <cursoragent@cursor\.com>` | `(?:^|/)cursor/` | — |
| 20 | **Devin** | `devin-ai-integration\[bot\]` | `Devin(?:[.:]|\s*\([^)]*\))?$`<br>`Devin AI <158243242\+devin-ai-integration\[bot\]@users\.noreply\.github\.com>`<br>`devin-ai-integration\[bot\]` | `(?:^|/)devin/` | — |
| 21 | **DeepSeek Harness** | — | — | — | — |
| 22 | **Factory Droid** | `factory-droid\[bot\]` | `factory-droid\[bot\] <138933559\+factory-droid\[bot\]@users\.noreply\.github\.com>` | — | — |
| 23 | **Gemini** | — | `Gemini CLI`<br>`Gemini Code Assist`<br>`gemini-code-assist`<br>`gemini-code-assist\[bot\] <176961590\+gemini-code-assist\[bot\]@users\.noreply\.github\.com>` | — | — |
| 24 | **Goose** | — | `Goose` | — | — |
| 25 | **Lovable** | `lovable-dev\[bot\]`<br>`gpt-engineer-app\[bot\]` | `gpt-engineer-app\[bot\] <159125892\+gpt-engineer-app\[bot\]@users\.noreply\.github\.com>` | — | — |
| 26 | **Gru** | `gru-agent\[bot\]` | `gru-agent\[bot\] <185149714\+gru-agent\[bot\]@users\.noreply\.github\.com>` | — | — |
| 27 | **Jules** | `google-labs-jules\[bot\]` | `Google Jules`<br>`Jules \(Google\)`<br>`google-labs-jules\[bot\] <161369871\+google-labs-jules\[bot\]@users\.noreply\.github\.com>` | — | — |
| 28 | **Junie** | `jetbrains-junie\[bot\]` | `Junie`<br>`Junie <junie@jetbrains\.com>` | — | — |
| 29 | **Kilo Code** | `kilo-code-bot\[bot\]`<br>`kiloconnect\[bot\]` | `Kilo Code`<br>`kiloconnect\[bot\] <240665456\+kiloconnect\[bot\]@users\.noreply\.github\.com>` | — | — |
| 30 | **Kimi Code** | — | `Kimi Code`<br>`Kimi(?: Code)? <noreply@moonshot\.(?:cn|ai)>` | — | — |
| 31 | **Kiro** | — | `Kiro`<br>`Kiro <kiro-noreply@amazon\.com>`<br>`Kiro Agent <244629292\+kiro-agent@users\.noreply\.github\.com>` | `(?:^|/)kiro/` | — |
| 32 | **LangChain Open SWE** | `open-swe\[bot\]`<br>`open-swe-dev\[bot\]` | `Open SWE`<br>`open-swe\[bot\]`<br>`open-swe-dev\[bot\]` | `(?:^|/)open-swe/` | — |
| 33 | **Letta Code** | — | `Letta Code`<br>`Letta(?: Code)? <noreply@letta\.com>` | — | — |
| 34 | **Microsoft Amplifier** | — | `Amplifier <240397093\+microsoft-amplifier@users\.noreply\.github\.com>` | — | — |
| 35 | **MiMo Code** | — | — | — | — |
| 36 | **MiniMax Code** | — | — | — | — |
| 37 | **Mistral Vibe** | `vibe@mistral\.ai` | `Mistral Vibe`<br>`Mistral Vibe <vibe@mistral\.ai>` | — | — |
| 38 | **Ona** | — | `Ona <no-reply@ona\.com>` | — | — |
| 39 | **OpenCode** | — | `OpenCode`<br>`OpenCode <noreply@opencode\.ai>` | `(?:^|/)opencode/` | — |
| 40 | **OpenHands** | `openhands@all-hands\.dev` | `OpenHands <openhands@all-hands\.dev>` | — | — |
| 41 | **Pi** | — | `Pi`<br>`Pi Coding Agent` | — | — |
| 42 | **Plandex** | — | — | — | — |
| 43 | **Qwen Code** | — | `Qwen Code`<br>`Qwen-Coder <qwen-coder@alibabacloud\.com>`<br>`Qwen Code <qwen@tongyi\.aliyun\.com>` | — | — |
| 44 | **Qoder** | — | `Qoder`<br>`Qoder <noreply@qoder\.com>` | — | — |
| 45 | **Roo Code** | `roomote@roocode\.com` | `Roo Code <roomote@roocode\.com>` | — | — |
| 46 | **Roomote** | `roomote-roomote` | — | — | — |
| 47 | **Sentry Seer** | `seer-by-sentry\[bot\]` | — | `(?:^|/)seer/fix/` | — |
| 48 | **Sketch** | `hello@sketch\.dev` | `Sketch <hello@sketch\.dev>` | — | — |
| 49 | **Sweep** | `sweep-ai\[bot\]` | `sweep-ai\[bot\] <128439645\+sweep-ai\[bot\]@users\.noreply\.github\.com>` | — | — |
| 50 | **Trae** | — | `Trae`<br>`traeagent <traeagent@users\.noreply\.github\.com>` | `(?:^|/)trae/agent-` | — |
| 51 | **Verdent** | — | — | — | — |
| 52 | **Warp** | `Warp Agent <agent@warp\.dev>`<br>`Oz <oz-agent@warp\.dev>` | `Warp <agent@warp\.dev>`<br>`Oz <oz-agent@warp\.dev>` | — | — |
| 53 | **Windsurf** | — | `Windsurf`<br>`windsurf-bot\[bot\] <189301087\+windsurf-bot\[bot\]@users\.noreply\.github\.com>` | — | — |
| 54 | **ZCode** | — | `ZCode` | — | — |
| 55 | **Huawei CodeArts** | — | — | — | — |
| 56 | **Replit Agent** | `replit-agent` | — | — | — |
| 57 | **iFlow CLI** | — | — | — | — |

## 不纳入清单的工具

以下工具不登记为独立编码 Agent：

- `DeepSource Autofix`：确定性修复与 AI 修复混用同一身份，无法可靠区分；
- `Fly`：属于运行平台而非独立编码 Agent，且裸名称存在冲突。

其他辅助或外围对象同样不纳入：`Generic AI`、`ChatGPT`、`Factory`、`CodeRabbit`、`PR-Agent`、`Qodo`、`Sourcery`、`Serena`、`Rulesync`、`SpecKit`、`Taskmaster`、`Superpowers`、`Specstory`、`Tessl`、`Paperclip`。

部分产品名合并到代表条目：`GPT-Engineer` 归入 `Lovable`，`Qwen Coder` 归入 `Qwen Code`。`Roo Code` 与 `Roomote` 分别登记为独立条目。
