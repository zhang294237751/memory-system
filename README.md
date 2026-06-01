# Memory System 插件

会话记忆管理系统 — 自动从对话中提取、分类、归档项目记忆，跨会话积累知识。

支持 **Claude Code** 和 **OpenAI Codex**。

---

## 安装

### Claude Code

```bash
python path/to/memory-system/install.py
```

### OpenAI Codex

```bash
python path/to/memory-system/codex/install.py
```

> Codex 需要启用 `features.codex_hooks = true`

可选参数：
- `--force`：覆盖已存在的文件
- `--dry-run`：仅预览，不实际写入

---

## 安装后文件结构对比

| 文件 | Claude Code | Codex |
|------|:-----------:|:-----:|
| 记忆文档 | `item memory.md` | `item memory.md` |
| 记忆处理指令 | `.claude/skills/memory-skill/SKILL.md` | SessionStart hook 自动输出 |
| Hook 脚本 | `.claude/hooks/` | `.codex/hooks/` |
| Hook 配置 | `.claude/settings.local.json` | `.codex/hooks.json` |
| 会话摘要 | `.claude/session_abstract.md` | `.codex/session_abstract.md` |
| 项目指令 | `CLAUDE.md` | 无需（SessionStart 替代） |

---

## 工作流程

1. **会话结束** — Stop hook 自动将对话摘要保存到 `session_abstract.md`
2. **新会话开始** — 自动处理记忆：
   - 检查 `item memory.md` 备注列，处理删除标记
   - 读取 `session_abstract.md`，提取新知识
   - 按 7 个维度分类更新 `item memory.md`
3. **每次提问** — UserPromptSubmit hook 注入记忆摘要到上下文

---

## Hook 事件对照

| 功能 | Claude Code | Codex |
|------|:-----------:|:-----:|
| 会话启动注入记忆 | SKILL.md + CLAUDE.md 指令 | `SessionStart` hook |
| 每次 prompt 注入记忆 | `UserPromptSubmit` hook | `UserPromptSubmit` hook |
| 会话结束保存摘要 | `Stop` hook | `Stop` hook |

---

## 记忆维度

| 维度 | 说明 |
|------|------|
| 项目及业务背景 | 业务领域、项目目标 |
| 业务规则 | 含算法、业务流程 |
| UI/设计规范 | 色值、字号、间距 |
| 技术栈 | 语言、框架、工具 |
| 架构图及模块划分 | 系统架构、模块关系 |
| 目录结构说明 | 关键路径说明 |
| 删除记忆模块 | 已删除的记忆归档 |

## 手动清理

在 `item memory.md` 任意记忆条目的「备注」列中标注「删除」「不采纳」「作废」后，下次会话会自动将其移至删除记忆模块，且不再注入上下文。

## 依赖

- Python 3.7+
- Claude Code 或 OpenAI Codex CLI
