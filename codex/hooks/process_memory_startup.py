"""
Codex SessionStart Hook — 会话启动时处理记忆并注入上下文
读取 item memory.md + session_abstract.md，输出记忆处理指令和当前记忆摘要。
"""
import json
import os
import sys


def main():
    try:
        raw = sys.stdin.read().strip()
        hook_input = {}
        if raw:
            hook_input = json.loads(raw)
        cwd = hook_input.get("cwd", os.getcwd())

        memory_path = os.path.join(cwd, "item memory.md")
        abstract_path = os.path.join(cwd, ".codex", "session_abstract.md")

        # 1. 读取当前记忆
        memory_content = ""
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                memory_content = f.read()

        # 2. 检查是否有待处理的会话摘要
        has_abstract = os.path.exists(abstract_path)
        abstract_note = ""
        if has_abstract:
            with open(abstract_path, "r", encoding="utf-8") as f:
                abstract_text = f.read()
            if abstract_text.strip():
                abstract_note = (
                    "\n**注意：存在未处理的会话摘要** `.codex/session_abstract.md`，"
                    "请在回答用户问题之前先从中提取新知识并更新 item memory.md。\n"
                )

        # 3. 检查备注列是否有待删除项
        deletion_note = check_deletion_markers(memory_content)

        # 4. 构建记忆摘要
        summary = build_summary(memory_content)

        # 5. 输���综合上下文
        output_parts = []
        if summary:
            output_parts.append(summary)
        if deletion_note:
            output_parts.append(deletion_note)
        if abstract_note:
            output_parts.append(abstract_note)

        if output_parts:
            output_parts.insert(0, "---")
            output_parts.insert(0, "# 项目记忆系统（Codex SessionStart）")
            output_parts.append("---")
            print("\n".join(output_parts))

    except Exception as e:
        print(f"[memory-sessionstart-hook] Error: {e}", file=sys.stderr)


def check_deletion_markers(content: str) -> str:
    """检查备注列是否有「删除」「不采纳」「作废」标记"""
    if not content:
        return ""
    lines = content.split("\n")
    pending = []
    current_section = ""
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("## "):
            current_section = line_stripped.replace("## ", "").strip()
        if "删除" in current_section:
            continue
        if line_stripped.startswith("| ") and not line_stripped.startswith("|---") and not line_stripped.startswith("| #"):
            parts = [p.strip() for p in line_stripped.split("|")]
            parts = [p for p in parts if p]
            if len(parts) >= 4:
                note = parts[3] if len(parts) > 3 else ""
                memory_text = parts[1] if len(parts) > 1 else ""
                if note and any(kw in note for kw in ["删除", "不采纳", "作废"]):
                    pending.append(f"  - [{current_section}] {memory_text}（备注: {note}）")

    if pending:
        return (
            "\n**注意：以下记忆条目的备注列标记为删除，请将其移至「删除记忆模块」：**\n"
            + "\n".join(pending)
            + "\n"
        )
    return ""


def build_summary(content: str) -> str:
    """从记忆文档中提取非空记忆条目，生成紧凑摘要"""
    if not content:
        return ""
    lines = content.split("\n")
    sections = []
    current_section = None
    entries = []

    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("## "):
            if current_section and entries:
                sections.append((current_section, entries))
                entries = []
            current_section = line_stripped.replace("## ", "").strip()
        elif line_stripped.startswith("| ") and not line_stripped.startswith("|---") and not line_stripped.startswith("| #"):
            parts = [p.strip() for p in line_stripped.split("|")]
            parts = [p for p in parts if p]
            if len(parts) >= 2 and parts[0].isdigit():
                memory_text = parts[1] if len(parts) > 1 else ""
                if memory_text and memory_text.strip():
                    entries.append(f"  - {memory_text}")

    if current_section and entries:
        sections.append((current_section, entries))

    if not sections:
        return ""

    out = ["# 项目记忆（来自 item memory.md）", ""]
    for section_name, section_entries in sections:
        if "删除" in section_name:
            continue
        out.append(f"## {section_name}")
        for e in section_entries[:10]:
            out.append(e)
        out.append("")

    if len(out) <= 2:
        return ""

    out.append("*回答时请参考以上项目记忆*")
    return "\n".join(out)


if __name__ == "__main__":
    main()
