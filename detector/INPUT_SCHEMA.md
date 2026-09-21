# Input schema

工具读取 SQLite 数据库。参数既可以直接指向数据库文件，也可以指向包含 `pr_agent_inputs.sqlite3` 的目录。

## 必需表

### `target_prs`

必需字段：

- `pr_id`
- `repo_id`
- `pr_number`
- `expected_author_id`
- `collection_status`

`expected_author_id` 在输出中称为 `target_author_id`，用于判断 commit 痕迹是否属于目标 PR 作者。

支持的 `collection_status`：`completed`、`pending`、`retryable_failure`、`terminal_unavailable`、`identity_conflict`。只有 `completed` 进入检测，其余输出 `unavailable`。

### `pr_details`

必需字段：

- `pr_id`
- `repo_id`
- `pr_number`
- `author_database_id`
- `author_login`
- `author_name`
- `author_email`
- `body_markdown`
- `head_ref_name`

### `pr_commits`

必需字段：

- `pr_id`
- `sha`
- `message`
- `author_name`
- `author_email`
- `author_user_login`
- `author_user_database_id`

可选字段：`committed_date`。存在时写入逐条证据的事件时间；缺失不影响检测。

### `pr_labels`

必需字段：`pr_id`、`name`。

可选字段：`label_node_id`或`ordinal`。存在时用作逐条证据对象编号；均缺失时使用label名称，不影响检测。

历史 label event 不是检测输入要求；即使数据库中存在相应表，它也不参与检测判断。

## 数据完整性与运行保护

检测器以只读方式打开输入数据库。若存在非空 `-wal` 或 `-journal`，会拒绝启动，避免读取正在变化的数据库状态。

运行开始时记录输入文件大小和修改时间；检测完成及结果合并前后会再次检查，发现输入变化则拒绝发布最终数据库。

每个分片有完成标记和文件大小记录，用于断点续跑和损坏检测。最终分片会合并到 `detection.sqlite3`，并执行 SQLite 与结果关系的一致性审计。

`--deep-check` 可额外执行 SQLite `PRAGMA quick_check`。
