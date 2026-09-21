# Agent 规则清单

> 本文档用于人工查看。机器检测只读取 `config/rules/agents.json`。

- Agent：**56**
- Identity patterns：**150**
- Branch patterns：**13**
- Label patterns：**2**
- Raw message signatures：**2**
- 总可执行规则：**167**

## Abacus

**Identity**

```regex
Abacus\.AI CLI <agent@abacus\.ai>
```

## Aider

**Identity**

```regex
\(aider\)
Aider .*<aider@aider\.chat>
Aider
```

## Alibaba Lingma

**Identity**

```regex
Lingma
lingma-agents\[bot\]
```

## Amazon Q

**Identity**

```regex
amazon-q-developer\[bot\]
Amazon Q Developer
amazon-q-developer\[bot\] <208079219\+amazon-q-developer\[bot\]@users\.noreply\.github\.com>
```

## Amp

**Identity**

```regex
ampagent
Amp
Amp <amp@ampcode\.com>
```

## Atlassian Rovo Dev

**Identity**

```regex
Rovo Dev
Rovodev
```

**Branch**

```regex
(?:^|/)rovodev/
```

## Augment Code

**Identity**

```regex
Augment Code
Augment Agent
Augment Agent <augment@augmentcode\.com>
Augment Agent <agent@augmentcode\.com>
Augment Code <code@augmentcode\.com>
Augment Code <noreply@augmentcode\.com>
```

## Brokk

**Identity**

```regex
Brokk AI
brokkbot-staging\[bot\]
brokk-bot <noreply-brokk-bot@brokk\.ai>
```

## Charlie

**Identity**

```regex
CharlieHelps
CharlieHelps <charlie@charlielabs\.ai>
```

## Claude Code

**Identity**

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

**Identity**

```regex
cline-cloud\[bot\]
cline-cloud\[bot\] <276134852\+cline-cloud\[bot\]@users\.noreply\.github\.com>
Cline Agent <cline-agent@users\.noreply\.github\.com>
```

## CodeBuddy

**Identity**

```regex
CodeBuddy
CodeBuddy Code
CodeBuddy(?: Code)? <noreply@tencent\.com>
CodeBuddy(?: Code)? <noreply@codebuddy\.ai>
CodeBuddy(?: Code)? <noreply@cnb\.cool>
CodeBuddy(?: Code)? <noreply@codebuddy\.dev>
```

## Codegen

**Identity**

```regex
codegen-sh\[bot\]
codegen-sh\[bot\] <131295404\+codegen-sh\[bot\]@users\.noreply\.github\.com>
```

## Codex

**Identity**

```regex
Codex
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

**Identity**

```regex
Continue
Continue <noreply@continue\.dev>
```

## Copilot

**Identity**

```regex
copilot-swe-agent\[bot\]
Copilot <[0-9]+\+Copilot@users\.noreply\.github\.com>
Copilot <copilot@github\.com>
GitHub Copilot <copilot@github\.com>
GitHub Copilot
```

**Branch**

```regex
(?:^|/)copilot/
```

## Crush

**Identity**

```regex
Crush
Crush <crush@charm\.land>
```

## Cursor

**Identity**

```regex
Cursor
Cursor Agent <cursoragent@cursor\.com>
Cursor <cursoragent@cursor\.com>
cursoragent
```

**Branch**

```regex
(?:^|/)cursor/
```

## DeepSeek Harness

**Identity**

```regex
DeepSeek Harness
DeepSeek Harness <deepseek-harness@users\.noreply\.github\.com>
```

## Devin

**Identity**

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

**Identity**

```regex
factory-droid\[bot\]
factory-droid\[bot\] <138933559\+factory-droid\[bot\]@users\.noreply\.github\.com>
```

## Gemini

**Identity**

```regex
gemini-code-assist\[bot\]
gemini-code-assist\[bot\] <176961590\+gemini-code-assist\[bot\]@users\.noreply\.github\.com>
Gemini CLI
Gemini CLI <gemini-cli@google\.com>
```

## Goose

**Identity**

```regex
Goose
```

## Gru

**Identity**

```regex
gru-agent\[bot\]
gru-agent\[bot\] <185149714\+gru-agent\[bot\]@users\.noreply\.github\.com>
```

## Huawei CodeArts

**Identity**

```regex
CodeArts Agent
```

## iFlow CLI

**Identity**

```regex
iFlow CLI
```

## Jules

**Identity**

```regex
google-labs-jules\[bot\]
google-labs-jules\[bot\] <161369871\+google-labs-jules\[bot\]@users\.noreply\.github\.com>
Google Jules
Jules \(Google\)
```

## Junie

**Identity**

```regex
jetbrains-junie\[bot\]
jetbrains-junie\[bot\] <(?:201638009\+)?jetbrains-junie\[bot\]@users\.noreply\.github\.com>
Junie <junie@jetbrains\.com>
Junie
```

## Kilo Code

**Identity**

```regex
kilo-code-bot\[bot\]
kiloconnect\[bot\]
kiloconnect\[bot\] <240665456\+kiloconnect\[bot\]@users\.noreply\.github\.com>
Kilo Code
```

## Kimi Code

**Identity**

```regex
Kimi Code
Kimi Code CLI
Kimi(?: Code)? <noreply@moonshot\.cn>
```

## Kiro

**Identity**

```regex
Kiro
Kiro CLI
Kiro Agent <244629292\+kiro-agent@users\.noreply\.github\.com>
kiro-agent\[bot\]
kiro-agent\[bot\] <245459735\+kiro-agent\[bot\]@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)kiro/
```

## LangChain Open SWE

**Identity**

```regex
open-swe\[bot\]
open-swe\[bot\] <(?:215916821\+)?open-swe\[bot\]@users\.noreply\.github\.com>
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

**Identity**

```regex
Letta Code
Letta(?: Code)? <noreply@letta\.com>
```

## Lovable

**Identity**

```regex
lovable-dev\[bot\]
gpt-engineer-app\[bot\]
gpt-engineer-app\[bot\] <159125892\+gpt-engineer-app\[bot\]@users\.noreply\.github\.com>
```

## Microsoft Amplifier

**Identity**

```regex
Amplifier <240397093\+microsoft-amplifier@users\.noreply\.github\.com>
Amplifier
```

## MiMo Code

**Identity**

```regex
MiMo Code
MiMo-Code <noreply@mimo\.xiaomi\.com>
```

## MiniMax Code

**Identity**

```regex
MiniMax Code
MiniMax Code <noreply@minimax\.io>
```

## Mistral Vibe

**Identity**

```regex
mistral-vibe
Vibe Nuage Agent <vibe@mistral\.ai>
Mistral Vibe <vibe@mistral\.ai>
Mistral Vibe
```

## Ona

**Identity**

```regex
Ona <no-reply@ona\.com>
```

## OpenCode

**Identity**

```regex
OpenCode
OpenCode <noreply@opencode\.ai>
opencode-agent\[bot\]
opencode-agent\[bot\] <opencode-agent\[bot\]@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)opencode/
```

## OpenHands

**Identity**

```regex
openhands-agent
OpenHands <openhands@all-hands\.dev>
OpenHands
```

## Pi

**Identity**

```regex
Pi
Pi Coding Agent
```

## Plandex

**Raw message signature**

```regex
(?m)^🤖\s*Plandex\s*→
```

## Qoder

**Identity**

```regex
Qoder
Qoder <noreply@qoder\.com>
```

## Qwen Code

**Identity**

```regex
Qwen Code
Qwen-Coder <qwen-coder@alibabacloud\.com>
Qwen Code <qwen@tongyi\.aliyun\.com>
```

## Replit Agent

**Identity**

```regex
replit-agent
Replit
```

**Raw message signature**

```regex
(?mi)^Replit-Commit-Author:\s*Agent\s*$
```

## Roo Code

**Identity**

```regex
Roo Code <roomote@roocode\.com>
```

## Roomote

**Identity**

```regex
roomote-roomote
roomote\[bot\] <219738659\+roomote\[bot\]@users\.noreply\.github\.com>
```

## Sentry Seer

**Identity**

```regex
seer-by-sentry\[bot\]
seer-by-sentry\[bot\] <157164994\+seer-by-sentry\[bot\]@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)seer/fix/
```

## Sketch

**Identity**

```regex
Sketch <hello@sketch\.dev>
```

## Sweep

**Identity**

```regex
sweep-ai\[bot\]
sweep-ai-deprecated\[bot\]
sweep-ai\[bot\] <128439645\+sweep-ai\[bot\]@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)sweep/
```

## Trae

**Identity**

```regex
traeagent <traeagent@users\.noreply\.github\.com>
```

**Branch**

```regex
(?:^|/)trae/agent-
```

## Verdent

**Identity**

```regex
Verdent
Verdent(?: AI)? <(?:verdent|noreply)@verdent\.ai>
```

## Warp

**Identity**

```regex
Warp <agent@warp\.dev>
Warp Agent <agent@warp\.dev>
oz-agent
Oz <oz-agent@warp\.dev>
```

## Windsurf

**Identity**

```regex
Windsurf
windsurf-bot\[bot\] <189301087\+windsurf-bot\[bot\]@users\.noreply\.github\.com>
```

## ZCode

**Identity**

```regex
ZCode <noreply@z\.ai>
ZCode
```
