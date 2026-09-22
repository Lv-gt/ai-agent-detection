# Agent 规则清单

> 本文档用于人工查看。机器检测只读取 `config/rules/agents.json`。Author 与正文规则允许重叠。

- Agent：**56**
- Author patterns：**89**
- Text attribution patterns：**156**
- Author/Text 重叠：**62**
- Branch patterns：**13**
- Label patterns：**2**
- Raw message signatures：**2**
- 总可执行规则实例：**262**

## Abacus

**Text attribution**

```regex
Abacus\.AI CLI <agent@abacus\.ai>
```

## Aider

**Author**

```regex
\(aider\)
```

**Text attribution**

```regex
Aider .*<aider@aider\.chat>
Aider
```

## Alibaba Lingma

**Author**

```regex
lingma-agents\[bot\]
```

**Text attribution**

```regex
Lingma
```

## Amazon Q

**Author**

```regex
amazon-q-developer\[bot\]
amazon-q-developer\[bot\] <208079219\+amazon-q-developer\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
Amazon Q Developer
amazon-q-developer\[bot\] <208079219\+amazon-q-developer\[bot\]@users\.noreply\.github\.com>
```

## Amp

**Author**

```regex
ampagent
Amp <amp@ampcode\.com>
```

**Text attribution**

```regex
Amp
Amp <amp@ampcode\.com>
```

## Atlassian Rovo Dev

**Text attribution**

```regex
Rovo Dev
Rovodev
```

**Branch**

```regex
(?:^|/)rovodev/
```

## Augment Code

**Text attribution**

```regex
Augment Code
Augment Agent
Augment Agent <augment@augmentcode\.com>
Augment Agent <agent@augmentcode\.com>
Augment Code <code@augmentcode\.com>
Augment Code <noreply@augmentcode\.com>
```

## Brokk

**Author**

```regex
brokkbot-staging\[bot\]
brokkbot-staging\[bot\] <237331342\+brokkbot-staging\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
Brokk AI
brokk-bot <noreply-brokk-bot@brokk\.ai>
```

## Charlie

**Author**

```regex
CharlieHelps
CharlieHelps <charlie@charlielabs\.ai>
```

**Text attribution**

```regex
CharlieHelps
CharlieHelps <charlie@charlielabs\.ai>
```

## Claude Code

**Author**

```regex
Claude[^<]*<noreply@anthropic\.com>
Claude[^<]*<claude@anthropic\.com>
```

**Text attribution**

```regex
Claude Code
Claude[^<]*<noreply@anthropic\.com>
Claude[^<]*<claude@anthropic\.com>
```

**Branch**

```regex
(?:^|/)claudecode/
(?:^|/)claude/
```

## Cline

**Author**

```regex
cline-cloud\[bot\]
cline-cloud\[bot\] <276134852\+cline-cloud\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
Cline Agent <cline-agent@users\.noreply\.github\.com>
```

## CodeBuddy

**Text attribution**

```regex
CodeBuddy
CodeBuddy Code
CodeBuddy(?: Code)? <noreply@tencent\.com>
CodeBuddy(?: Code)? <noreply@codebuddy\.ai>
CodeBuddy(?: Code)? <noreply@cnb\.cool>
CodeBuddy(?: Code)? <noreply@codebuddy\.dev>
```

## Codegen

**Author**

```regex
codegen-sh\[bot\]
codegen-sh\[bot\] <131295404\+codegen-sh\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
codegen-sh\[bot\]
codegen-sh\[bot\] <131295404\+codegen-sh\[bot\]@users\.noreply\.github\.com>
```

## Codex

**Author**

```regex
Codex <codex@openai\.com>
OpenAI Codex <codex@openai\.com>
```

**Text attribution**

```regex
Codex
codex-cli
OpenAI Codex
Codex <codex@openai\.com>
Codex <noreply@openai\.com>
OpenAI Codex <codex@openai\.com>
OpenAI Codex <noreply@openai\.com>
```

**Branch**

```regex
(?:^|/)codex/
```

**Label**

```regex
^codex$
```

## Continue

**Author**

```regex
Continue <noreply@continue\.dev>
continue\[bot\]
continue\[bot\] <(?:230936708\+)?continue\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
Continue
Continue <noreply@continue\.dev>
continue\[bot\]
continue\[bot\] <(?:230936708\+)?continue\[bot\]@users\.noreply\.github\.com>
```

## Copilot

**Author**

```regex
copilot-swe-agent\[bot\]
copilot-swe-agent\[bot\] <198982749\+Copilot@users\.noreply\.github\.com>
Copilot <[0-9]+\+Copilot@users\.noreply\.github\.com>
Copilot <copilot@github\.com>
GitHub Copilot <copilot@github\.com>
```

**Text attribution**

```regex
copilot-swe-agent\[bot\]
copilot-swe-agent\[bot\] <198982749\+Copilot@users\.noreply\.github\.com>
Copilot <[0-9]+\+Copilot@users\.noreply\.github\.com>
Copilot <noreply@github\.com>
Copilot App <223556219\+Copilot@users\.noreply\.github\.com>
Copilot Workspace
Copilot <copilot@github\.com>
GitHub Copilot <copilot@github\.com>
GitHub Copilot
```

**Branch**

```regex
(?:^|/)copilot/
```

## Crush

**Text attribution**

```regex
Crush
Crush <crush@charm\.land>
```

## Cursor

**Author**

```regex
Cursor Agent <cursoragent@cursor\.com>
Cursor Agent <agent@cursor\.com>
Cursor <cursoragent@cursor\.com>
cursoragent
```

**Text attribution**

```regex
Cursor(?!\s+Bugbot\b)
Cursor Agent <cursoragent@cursor\.com>
Cursor Agent <agent@cursor\.com>
Cursor <cursoragent@cursor\.com>
```

**Branch**

```regex
(?:^|/)cursor/
```

## DeepSeek Harness

**Text attribution**

```regex
DeepSeek Harness
DeepSeek Harness <deepseek-harness@users\.noreply\.github\.com>
```

## Devin

**Author**

```regex
devin-ai-integration\[bot\]
Devin(?: AI)? <158243242\+devin-ai-integration\[bot\]@users\.noreply\.github\.com>
devin-ai-integration\[bot\] <158243242\+devin-ai-integration\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
devin-ai-integration\[bot\]
Devin
Devin(?: AI)? <158243242\+devin-ai-integration\[bot\]@users\.noreply\.github\.com>
devin-ai-integration\[bot\] <158243242\+devin-ai-integration\[bot\]@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)devin/
```

## Factory Droid

**Author**

```regex
factory-droid\[bot\]
factory-droid\[bot\] <138933559\+factory-droid\[bot\]@users\.noreply\.github\.com>
factory-droid <138933559\+factory-droid\[bot\]@users\.noreply\.github\.com>
factory-droid\[bot\] <factory-droid\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
factory-droid\[bot\]
factory-droid\[bot\] <138933559\+factory-droid\[bot\]@users\.noreply\.github\.com>
factory-droid <138933559\+factory-droid\[bot\]@users\.noreply\.github\.com>
factory-droid\[bot\] <factory-droid\[bot\]@users\.noreply\.github\.com>
```

## Gemini

**Author**

```regex
Gemini CLI <gemini-cli@google\.com>
Gemini Code Assist <176961590\+gemini-code-assist\[bot\]@users\.noreply\.github\.com>
gemini-code-assist\[bot\] <176961590\+gemini-code-assist\[bot\]@users\.noreply\.github\.com>
Gemini <176961590\+gemini-code-assist\[bot\]@users\.noreply\.github\.com>
gemini-code-assist\[bot\] <gemini-code-assist\[bot\]@users\.noreply\.github\.com>
Gemini <gemini-code-assist\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
gemini-code-assist(?!\[bot\])
gemini-code-assist <200291788\+gemini-code-assist@users\.noreply\.github\.com>
gemini-code-assist <gemini-code-assist@google\.com>
gemini-code-assist\[bot\]
Gemini Code Assist <176961590\+gemini-code-assist\[bot\]@users\.noreply\.github\.com>
gemini-code-assist\[bot\] <176961590\+gemini-code-assist\[bot\]@users\.noreply\.github\.com>
Gemini <176961590\+gemini-code-assist\[bot\]@users\.noreply\.github\.com>
gemini-code-assist\[bot\] <gemini-code-assist\[bot\]@users\.noreply\.github\.com>
Gemini <gemini-code-assist\[bot\]@users\.noreply\.github\.com>
gemini-code-assist <gemini-code-assist\[bot\]@users\.noreply\.github\.com>
Gemini CLI
Gemini CLI <gemini-cli@google\.com>
```

## Goose

**Text attribution**

```regex
Goose
```

## Gru

**Author**

```regex
gru-agent\[bot\]
gru-agent\[bot\] <185149714\+gru-agent\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
gru-agent\[bot\]
gru-agent\[bot\] <185149714\+gru-agent\[bot\]@users\.noreply\.github\.com>
```

## Huawei CodeArts

**Text attribution**

```regex
CodeArts Agent
```

## iFlow CLI

**Text attribution**

```regex
iFlow CLI
```

## Jules

**Author**

```regex
google-labs-jules\[bot\]
google-labs-jules\[bot\] <161369871\+google-labs-jules\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
google-labs-jules\[bot\]
google-labs-jules\[bot\] <161369871\+google-labs-jules\[bot\]@users\.noreply\.github\.com>
Google Jules
Jules \(Google\)
```

## Junie

**Author**

```regex
jetbrains-junie\[bot\]
jetbrains-junie\[bot\] <(?:201638009\+)?jetbrains-junie\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
Junie <junie@jetbrains\.com>
Junie
```

## Kilo Code

**Author**

```regex
kilo-code-bot\[bot\]
kilo-code-bot\[bot\] <240665456\+kilo-code-bot\[bot\]@users\.noreply\.github\.com>
kiloconnect\[bot\]
kiloconnect\[bot\] <240665456\+kiloconnect\[bot\]@users\.noreply\.github\.com>
kiloconnect\[bot\] <kiloconnect\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
kilo-code-bot\[bot\]
kilo-code-bot\[bot\] <240665456\+kilo-code-bot\[bot\]@users\.noreply\.github\.com>
kiloconnect\[bot\]
kiloconnect\[bot\] <240665456\+kiloconnect\[bot\]@users\.noreply\.github\.com>
kiloconnect\[bot\] <kiloconnect\[bot\]@users\.noreply\.github\.com>
Kilo Code
```

## Kimi Code

**Text attribution**

```regex
Kimi Code
Kimi Code CLI
Kimi(?: Code)? <noreply@moonshot\.(?:cn|ai)>
```

## Kiro

**Author**

```regex
Kiro Agent <244629292\+kiro-agent@users\.noreply\.github\.com>
kiro-agent\[bot\]
kiro-agent\[bot\] <245459735\+kiro-agent\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
Kiro
Kiro CLI
kiro-cli
Kiro Agent <244629292\+kiro-agent@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)kiro/
```

## LangChain Open SWE

**Author**

```regex
open-swe\[bot\]
open-swe-dev\[bot\]
open-swe\[bot\] <215916821\+open-swe\[bot\]@users\.noreply\.github\.com>
open-swe\[bot\] <open-swe@users\.noreply\.github\.com>
open-swe-dev\[bot\] <214404619\+open-swe-dev\[bot\]@users\.noreply\.github\.com>
open-swe-dev\[bot\] <open-swe-dev@users\.noreply\.github\.com>
```

**Text attribution**

```regex
open-swe\[bot\]
open-swe-dev\[bot\]
open-swe\[bot\] <215916821\+open-swe\[bot\]@users\.noreply\.github\.com>
open-swe\[bot\] <open-swe@users\.noreply\.github\.com>
open-swe-dev\[bot\] <214404619\+open-swe-dev\[bot\]@users\.noreply\.github\.com>
open-swe-dev\[bot\] <open-swe-dev@users\.noreply\.github\.com>
Open SWE
```

**Branch**

```regex
(?:^|/)open-swe/
```

**Label**

```regex
^open-swe$
```

## Letta Code

**Text attribution**

```regex
Letta Code
Letta(?: Code)? <noreply@letta\.com>
```

## Lovable

**Author**

```regex
lovable-dev\[bot\]
gpt-engineer-app\[bot\]
gpt-engineer-app\[bot\] <159125892\+gpt-engineer-app\[bot\]@users\.noreply\.github\.com>
Lovable <159125892\+lovable-dev\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
gpt-engineer-app\[bot\]
gpt-engineer-app\[bot\] <159125892\+gpt-engineer-app\[bot\]@users\.noreply\.github\.com>
Lovable <159125892\+lovable-dev\[bot\]@users\.noreply\.github\.com>
```

## Microsoft Amplifier

**Text attribution**

```regex
Amplifier <240397093\+microsoft-amplifier@users\.noreply\.github\.com>
Amplifier
```

## MiMo Code

**Text attribution**

```regex
MiMo Code
MiMo-Code <noreply@mimo\.xiaomi\.com>
```

## MiniMax Code

**Text attribution**

```regex
MiniMax Code
MiniMax Code <noreply@minimax\.io>
```

## Mistral Vibe

**Author**

```regex
mistral-vibe
Vibe Nuage Agent <vibe@mistral\.ai>
```

**Text attribution**

```regex
Mistral Vibe <vibe@mistral\.ai>
Mistral Vibe
```

## Ona

**Text attribution**

```regex
Ona <no-reply@ona\.com>
```

## OpenCode

**Author**

```regex
opencode-agent\[bot\]
opencode-agent\[bot\] <opencode-agent\[bot\]@users\.noreply\.github\.com>
opencode-agent\[bot\] <219766164\+opencode-agent\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
OpenCode
OpenCode <noreply@opencode\.ai>
```

**Branch**

```regex
(?:^|/)opencode/
```

## OpenHands

**Author**

```regex
openhands-agent
OpenHands <openhands@all-hands\.dev>
```

**Text attribution**

```regex
OpenHands <openhands@all-hands\.dev>
OpenHands
```

## Pi

**Text attribution**

```regex
Pi
Pi Coding Agent
pi-coding-agent
```

## Plandex

**Raw message signature**

```regex
(?m)^🤖\s*Plandex\s*→
```

## Qoder

**Text attribution**

```regex
Qoder
Qoder <noreply@qoder\.com>
```

## Qwen Code

**Text attribution**

```regex
Qwen Code
Qwen-Coder <qwen-coder@alibabacloud\.com>
Qwen Code <qwen@tongyi\.aliyun\.com>
```

## Replit Agent

**Author**

```regex
replit-agent
```

**Text attribution**

```regex
Replit
```

**Raw message signature**

```regex
(?mi)^Replit-Commit-Author:\s*Agent\s*$
```

## Roo Code

**Author**

```regex
Roo Code <roomote@roocode\.com>
```

**Text attribution**

```regex
Roo Code <roomote@roocode\.com>
```

## Roomote

**Author**

```regex
roomote-roomote
roomote\[bot\] <219738659\+roomote\[bot\]@users\.noreply\.github\.com>
roomote\[bot\] <263205322\+roomote\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
roomote\[bot\] <219738659\+roomote\[bot\]@users\.noreply\.github\.com>
roomote\[bot\] <263205322\+roomote\[bot\]@users\.noreply\.github\.com>
```

## Sentry Seer

**Author**

```regex
seer-by-sentry\[bot\]
seer-by-sentry\[bot\] <157164994\+seer-by-sentry\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
seer-by-sentry\[bot\] <157164994\+seer-by-sentry\[bot\]@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)seer/fix/
```

## Sketch

**Text attribution**

```regex
Sketch <hello@sketch\.dev>
```

## Sweep

**Author**

```regex
sweep-ai\[bot\]
sweep-ai-deprecated\[bot\]
sweep-ai\[bot\] <128439645\+sweep-ai\[bot\]@users\.noreply\.github\.com>
sweep-ai-deprecated\[bot\] <128439645\+sweep-ai-deprecated\[bot\]@users\.noreply\.github\.com>
```

**Text attribution**

```regex
sweep-ai\[bot\] <128439645\+sweep-ai\[bot\]@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)sweep/
```

## Trae

**Text attribution**

```regex
traeagent <traeagent@users\.noreply\.github\.com>
TRAE CLI <noreply@bytedance\.com>
Trae AI <trae-ai@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)trae/agent-
```

## Verdent

**Text attribution**

```regex
Verdent
Verdent(?: AI)? <(?:verdent|noreply)@verdent\.ai>
```

## Warp

**Author**

```regex
Warp <agent@warp\.dev>
Warp Agent <agent@warp\.dev>
oz-agent
Oz <oz-agent@warp\.dev>
```

**Text attribution**

```regex
Warp <agent@warp\.dev>
Warp Agent <agent@warp\.dev>
Oz <oz-agent@warp\.dev>
```

## Windsurf

**Text attribution**

```regex
Windsurf
windsurf-bot\[bot\] <189301087\+windsurf-bot\[bot\]@users\.noreply\.github\.com>
```

## ZCode

**Text attribution**

```regex
ZCode <noreply@z\.ai>
ZCode
```
