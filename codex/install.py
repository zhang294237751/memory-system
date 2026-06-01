#!/usr/bin/env python3
"""
Memory System — Codex 版一键安装器
用法: python install.py [--force] [--dry-run]

将此脚本所在目录下的插件文件安装到当前项目（Codex 适配版）。
- 创建 .codex/hooks/
- 配置 SessionStart + UserPromptSubmit + Stop hooks
- 创建 item memory.md 模板
"""
import json
import os
import shutil
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
HOOK_SAVE_SRC = PLUGIN_DIR / "hooks" / "save_session_abstract.py"
HOOK_INJECT_SRC = PLUGIN_DIR / "hooks" / "inject_memory.py"
HOOK_STARTUP_SRC = PLUGIN_DIR / "hooks" / "process_memory_startup.py"
HOOKS_JSON_SRC = PLUGIN_DIR / "hooks.json"

HOOK_SCRIPTS = [
    (HOOK_STARTUP_SRC, "process_memory_startup.py"),
    (HOOK_INJECT_SRC, "inject_memory.py"),
    (HOOK_SAVE_SRC, "save_session_abstract.py"),
]

ITEM_MEMORY_TEMPLATE = """# 项目记忆文档

> 此文档由 memory-system 自动维护。
> 每条记忆的「备注」列供人工定期审核，请勿让 Agent 自动填写。
> 备注中标注「删除」「不采纳」「作废」等词后，下次会话将自动移至删除记忆模块。

---

## 一、项目及业务背景

| # | 记忆内容 | 来源 | 创建日期 | 备注 |
|---|---------|------|---------|------|
| 1 |        |      |         |      |

## 二、业务规则

| # | 记忆内容 | 来源 | 创建日期 | 备注 |
|---|---------|------|---------|------|
| 1 |        |      |         |      |

## 三、UI/设计规范

| # | 记忆内容 | 来源 | 创建日期 | 备注 |
|---|---------|------|---------|------|
| 1 |        |      |         |      |

## 四、技术栈

| # | 记忆内容 | 来源 | 创建日期 | 备注 |
|---|---------|------|---------|------|
| 1 |        |      |         |      |

## 五、架构图及模块划分

| # | 记忆内容 | 来源 | 创建日期 | 备注 |
|---|---------|------|---------|------|
| 1 |        |      |         |      |

## 六、目录结构说明

| # | 记忆内容 | 来源 | 创建日期 | 备注 |
|---|---------|------|---------|------|
| 1 |        |      |         |      |

## 七、删除记忆模块

| # | 原记忆内容 | 原所属模块 | 删除日期 | 删除原因 |
|---|-----------|-----------|---------|---------|
| 1 |           |           |         |         |
"""


def install(force=False, dry_run=False):
    base = Path.cwd()
    python_path = sys.executable

    print(f"\n  Memory System 安装器 (Codex)")
    print(f"  Python: {python_path}")
    print(f"  目标: {base}")
    print()

    # 1. 创建目录
    hooks_dir = base / ".codex" / "hooks"
    dirs = [hooks_dir]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {d.relative_to(base)}")

    # 2. 复制 hook 脚本
    for src, name in HOOK_SCRIPTS:
        dst = hooks_dir / name
        if dst.exists() and not force:
            print(f"  [SKIP] {name} 已存在，跳过")
            continue
        shutil.copy2(src, dst)
        print(f"  [OK] {name}")

    # 3. 配置 hooks.json（使用当前 Python 路径确保 hook 可执行）
    hooks_json_path = base / ".codex" / "hooks.json"
    if hooks_json_path.exists() and not force:
        with open(hooks_json_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {}

    with open(HOOKS_JSON_SRC, "r", encoding="utf-8") as f:
        codex_hooks = json.load(f)

    # 替换 hook 命令中的 python 为绝对路径
    for event in codex_hooks.get("hooks", {}):
        for entry in codex_hooks["hooks"][event]:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                if cmd.startswith("python "):
                    h["command"] = f"{python_path} {cmd[7:]}"

    # 合并 hooks（memory-system 的事件始终用最新模板覆盖）
    existing_hooks = existing.get("hooks", {})
    for event in ["SessionStart", "UserPromptSubmit", "Stop"]:
        existing_hooks[event] = codex_hooks.get(event, [])
    existing["hooks"] = existing_hooks

    if not dry_run:
        with open(hooks_json_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    print(f"  [OK] .codex/hooks.json")

    # 3.5 启用 Codex hooks 功能
    config_path = base / ".codex" / "config.toml"
    config_content = None
    if config_path.exists():
        config_content = config_path.read_text(encoding="utf-8")
    if config_content and "codex_hooks" in config_content:
        print(f"  [SKIP] features.codex_hooks 已启用")
    else:
        if not dry_run:
            with open(config_path, "a", encoding="utf-8") as f:
                f.write("\n[features]\ncodex_hooks = true\n")
        print(f"  [OK] features.codex_hooks = true 已写入 config.toml")

    # 4. item memory.md 模板
    memory_path = base / "item memory.md"
    if not memory_path.exists():
        if not dry_run:
            memory_path.write_text(ITEM_MEMORY_TEMPLATE, encoding="utf-8")
        print(f"  [OK] item memory.md 已创建")
    else:
        print(f"  [SKIP] item memory.md 已存在，保留")

    print()
    print("  安装完成！下次会话开始记忆系统自动生效。")
    print("  工作流程：")
    print("    1. 会话开始 -> SessionStart hook 注入记忆上下文 + 处理指令")
    print("    2. 每次提问 -> UserPromptSubmit hook 注入记忆摘要")
    print("    3. 会话结束 -> Stop hook 保存对话摘要到 .codex/session_abstract.md")
    print()
    print("  提示：在 Codex 中启用 hooks 功能需要确认 features.codex_hooks = true")


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    install(force=force, dry_run=dry_run)
