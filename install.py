#!/usr/bin/env python3
"""
Memory System 一键安装器
用法: python install.py [--force] [--dry-run]

将此脚本所在目录下的插件文件安装到当前项目。
- 创建 .claude/skills/、.claude/hooks/
- 配置 Stop + UserPromptSubmit hooks
- 创建 CLAUDE.md（或追加记忆指令）
- 创建 item memory.md 模板
- 生成 init-memory 全局命令
"""
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── 常量 ─────────────────────────────────
PLUGIN_DIR = Path(__file__).resolve().parent
SKILL_SRC = PLUGIN_DIR / "skills" / "memory-skill" / "SKILL.md"
HOOK_SAVE_SRC = PLUGIN_DIR / "hooks" / "save_session_abstract.py"
HOOK_INJECT_SRC = PLUGIN_DIR / "hooks" / "inject_memory.py"

CLAUDE_MD_APPEND = """
## 会话启动流程

每次会话启动时，按照 `.claude/skills/memory-skill/SKILL.md` 中的完整流程执行记忆管理。
"""


def install(force=False, dry_run=False):
    base = Path.cwd()
    print(f"\n  Memory System 安装器")
    print(f"  目标: {base}")
    print()

    # 1. 创建目录
    dirs = [
        base / ".claude" / "skills" / "memory-skill",
        base / ".claude" / "hooks",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {d.relative_to(base)}")

    # 2. 复制文件
    copies = [
        (SKILL_SRC, base / ".claude" / "skills" / "memory-skill" / "SKILL.md"),
        (HOOK_SAVE_SRC, base / ".claude" / "hooks" / "save_session_abstract.py"),
        (HOOK_INJECT_SRC, base / ".claude" / "hooks" / "inject_memory.py"),
    ]
    print()
    for src, dst in copies:
        if dst.exists() and not force:
            print(f"  ○ {dst.name} 已存在，跳过")
            continue
        shutil.copy2(src, dst)
        print(f"  ✓ {dst.name}")

    # 3. 配置 settings.local.json
    settings_path = base / ".claude" / "settings.local.json"
    settings = {}
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

    # 添加 hooks
    hooks = settings.get("hooks", {})
    for event, cmd in [("Stop", "python3 .claude/hooks/save_session_abstract.py"),
                        ("UserPromptSubmit", "python3 .claude/hooks/inject_memory.py")]:
        entry = {"matcher": "", "hooks": [{"type": "command", "command": cmd}]}
        existing = hooks.get(event, [])
        if not any(h["hooks"][0]["command"] == cmd for h in existing if h.get("hooks")):
            existing.append(entry)
            hooks[event] = existing
            print(f"  ✓ hooks.{event} 已配置")
        else:
            print(f"  ○ hooks.{event} 已存在")

    settings["hooks"] = hooks

    # 添加权限
    perms = settings.get("permissions", {}).get("allow", [])
    for p in ["Bash(python3 .claude/hooks/save_session_abstract.py)",
              "Bash(python3 .claude/hooks/inject_memory.py)"]:
        if p not in perms:
            perms.append(p)
    if perms != settings.get("permissions", {}).get("allow", []):
        settings.setdefault("permissions", {})["allow"] = perms

    if not dry_run:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    print(f"  ✓ settings.local.json")

    # 4. CLAUDE.md
    claude_path = base / "CLAUDE.md"
    marker = "会话启动流程"
    if not claude_path.exists():
        if not dry_run:
            claude_path.write_text(CLAUDE_MD_APPEND.strip() + "\n", encoding="utf-8")
        print(f"  ✓ CLAUDE.md 已创建")
    elif marker not in claude_path.read_text(encoding="utf-8"):
        if not dry_run:
            with open(claude_path, "a", encoding="utf-8") as f:
                f.write("\n" + CLAUDE_MD_APPEND.strip() + "\n")
        print(f"  ✓ CLAUDE.md 已追加记忆指令")
    else:
        print(f"  ○ CLAUDE.md 已有记忆指令")

    # 5. item memory.md 模板
    memory_path = base / "item memory.md"
    if not memory_path.exists():
        template = PLUGIN_DIR.parent / "item memory.md"
        if template.exists():
            shutil.copy2(template, memory_path)
        print(f"  ✓ item memory.md 已创建")
    else:
        print(f"  ○ item memory.md 已存在，保留")

    # 6. 全局命令
    global_tools = Path.home() / ".claude" / "tools"
    global_tools.mkdir(parents=True, exist_ok=True)
    for script in ["save_session_abstract.py", "inject_memory.py"]:
        src = base / ".claude" / "hooks" / script
        dst = global_tools / script
        if src.exists():
            shutil.copy2(src, dst)
    print(f"  ✓ 全局工具已更新")

    print()
    print("  安装完成！")
    print(f"  下次会话开始时记忆管理自动生效。")


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    install(force=force, dry_run=dry_run)
