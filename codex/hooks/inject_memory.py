"""
UserPromptSubmit Hook 脚本
每次用户提交 prompt 时，读取 item memory.md 并输出记忆摘要，
确保整个会话期间记忆指令始终有效。
"""
import json
import sys
import os
from datetime import datetime


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            print("[memory-prompt-hook] No stdin input", file=sys.stderr)
            return

        hook_input = json.loads(raw)
        cwd = hook_input.get("cwd", os.getcwd())
        memory_path = os.path.join(cwd, "item memory.md")

        if not os.path.exists(memory_path):
            return  # 没有记忆文件，静默跳过

        with open(memory_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取每个模块下的非空记忆条目（去掉模板空行）
        summary = build_summary(content)

        if summary:
            # 输出到 stdout，Claude Code 会将其注入为上下文
            print(summary)

    except Exception as e:
        print(f"[memory-prompt-hook] Error: {e}", file=sys.stderr)


def build_summary(content: str) -> str:
    """从记忆文档中提取非空记忆条目，生成紧凑摘要"""
    lines = content.split("\n")
    sections = []
    current_section = None
    entries = []

    for line in lines:
        line = line.strip()
        if line.startswith("## "):
            # 保存上一个 section
            if current_section and entries:
                sections.append((current_section, entries))
                entries = []
            current_section = line.replace("## ", "").strip()
        elif line.startswith("| ") and not line.startswith("|---") and not line.startswith("| #"):
            # 表格数据行
            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]  # 去掉空元素
            if len(parts) >= 2:
                content_text = parts[0] if parts[0].isdigit() else parts[0]
                # 跳过模板块的空行
                if content_text and content_text.strip() and parts[0].isdigit():
                    memory_text = parts[1] if len(parts) > 1 else ""
                    # "删除记忆模块"的列结构不同
                    if "删除" in current_section and len(parts) >= 2:
                        memory_text = parts[1]
                    if memory_text and memory_text.strip():
                        entries.append(f"  - {memory_text}")

    # 保存最后一个 section
    if current_section and entries:
        sections.append((current_section, entries))

    if not sections:
        return ""

    out = ["", "---", "# 项目记忆（来自 item memory.md）", ""]
    for section_name, section_entries in sections:
        if "删除" in section_name:
            continue  # 不注入删除记忆
        out.append(f"## {section_name}")
        for e in section_entries[:10]:  # 每模块最多10条
            out.append(e)
        out.append("")

    if len(out) <= 4:  # 只有头部，没有实际内容
        return ""

    out.append("*回答时请参考以上项目记忆*")
    out.append("---")
    return "\n".join(out)


if __name__ == "__main__":
    main()
