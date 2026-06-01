"""
SessionEnd Hook 脚本
在每次会话结束时自动保存对话摘要到 .codex/session_abstract.md
"""
import json
import sys
import os
from datetime import datetime


def main():
    cwd = os.getcwd()
    debug_path = os.path.join(cwd, ".codex", "hooks", "debug.log")
    raw_path = os.path.join(cwd, ".codex", "hooks", "raw_input.txt")

    def log(msg):
        try:
            os.makedirs(os.path.dirname(debug_path), exist_ok=True)
            with open(debug_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] {msg}\n")
        except Exception:
            pass

    log("=== Hook triggered ===")

    try:
        # 读取 stdin 原始内容
        raw = sys.stdin.read()

        # 保存原始输入供调试（处理可能的 surrogate 字符）
        try:
            with open(raw_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(raw)
            log(f"Raw input saved ({len(raw)} chars)")
        except Exception as e:
            log(f"Failed to save raw input: {e}")

        raw = raw.strip()
        if not raw:
            log("ERROR: No stdin input after strip")
            return

        # 解析 JSON：先尝试直接解析，失败则修复 Windows 路径
        hook_input = None
        try:
            hook_input = json.loads(raw)
            log("JSON parsed directly")
        except json.JSONDecodeError as e1:
            log(f"Direct parse failed: {e1}")
            # 策略：逐个替换非法转义为合法形式
            # 找出所有非法的反斜杠序列并替换
            fixed = fix_json_escapes(raw)
            try:
                hook_input = json.loads(fixed)
                log("JSON parsed after escape fix")
            except json.JSONDecodeError as e2:
                log(f"Escape fix also failed: {e2}")
                log(f"Fixed JSON (first 300 chars): {fixed[:300]}")
                return

        if hook_input is None:
            return

        # 获取关键信息
        transcript_path = hook_input.get("transcript_path", "")
        session_id = hook_input.get("session_id", "unknown")
        hook_cwd = hook_input.get("cwd", cwd)

        log(f"transcript_path={transcript_path}")
        log(f"session_id={session_id}")
        log(f"cwd={hook_cwd}")

        if not transcript_path or not os.path.exists(transcript_path):
            log(f"ERROR: Transcript not found: {transcript_path}")
            return

        # 读取 transcript
        with open(transcript_path, "r", encoding="utf-8") as f:
            raw_t = f.read()

        # 兼容 JSON 和 JSONL 格式
        messages = []
        try:
            transcript = json.loads(raw_t)
            messages = extract_messages(transcript)
            log(f"Parsed as single JSON, {len(messages)} msgs")
        except json.JSONDecodeError:
            for line in raw_t.strip().split("\n"):
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        normalized = normalize_message(obj)
                        if normalized:
                            messages.append(normalized)
                    except json.JSONDecodeError:
                        pass
            log(f"Parsed as JSONL, {len(messages)} user/assistant msgs")

        if not messages:
            log("ERROR: No messages extracted")
            return

        log(f"Total {len(messages)} messages")

        last_exchanges = get_last_exchanges(messages, n=3)
        log(f"Last exchanges: {len(last_exchanges)} messages")

        abstract = format_abstract(last_exchanges, session_id)

        output_path = os.path.join(cwd, ".codex", "session_abstract.md")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(abstract)

        log(f"SUCCESS: Saved to {output_path}")
        print(f"[memory-hook] Saved to {output_path}", file=sys.stderr)

    except Exception as e:
        log(f"FATAL EXCEPTION: {e}")
        import traceback
        log(traceback.format_exc())


def fix_json_escapes(raw: str) -> str:
    r"""
    修复 JSON 中非法的反斜杠转义序列。
    JSON 只允许: \\, \", \/, \b, \f, \n, \r, \t, \uXXXX
    Windows 路径中的 \C, \U, \. 等都是非法的。
    """
    result = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == '\\' and i + 1 < len(raw):
            next_c = raw[i + 1]
            # 检查是否已经是合法的 JSON 转义序列
            if next_c in '"\\/bfnrtu':
                result.append(c)
                result.append(next_c)
                i += 2
            else:
                # 非法转义，在反斜杠前再加一个反斜杠
                result.append('\\')
                result.append('\\')
                i += 1
        else:
            result.append(c)
            i += 1
    return ''.join(result)


def normalize_message(obj: dict) -> dict | None:
    """将 JSONL 行对象标准化为 {'role': str, 'content': str}"""
    t = obj.get("type", "")
    if t not in ("user", "assistant"):
        return None
    inner = obj.get("message", {})
    if not isinstance(inner, dict):
        return None
    role = t
    content = inner.get("content", "")
    # 处理 content 数组（assistant 消息常见）
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                bt = block.get("type", "")
                if bt == "text":
                    texts.append(block.get("text", ""))
                elif bt == "tool_use":
                    texts.append(f"[工具调用: {block.get('name', '?')}]")
                elif bt == "tool_result":
                    txt = str(block.get("content", ""))[:200]
                    texts.append(f"[工具结果: {txt}]")
        content = "\n".join(texts)
    elif not isinstance(content, str):
        content = str(content)
    if not content.strip() and role == "assistant":
        return None  # 跳过只有 thinking 块的空消息
    return {"role": role, "content": content}


def extract_messages(transcript: dict) -> list:
    """从旧格式（单 JSON）中提取消息列表"""
    if isinstance(transcript, list):
        return transcript
    if isinstance(transcript, dict):
        for key in ["messages", "conversation", "history", "data"]:
            if key in transcript:
                data = transcript[key]
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    for sub_key in ["messages", "conversation"]:
                        if sub_key in data and isinstance(data[sub_key], list):
                            return data[sub_key]
    return []


def get_last_exchanges(messages: list, n: int = 3) -> list:
    """获取最后 N 轮对话（用户+助手配对）"""
    result = []
    user_count = 0
    for msg in reversed(messages):
        role = msg.get("role", msg.get("type", ""))
        if role in ("user", "human"):
            result.insert(0, msg)
            user_count += 1
            if user_count >= n:
                break
        elif role in ("assistant", "ai", "model"):
            if user_count > 0:
                result.insert(0, msg)
    return result


def format_abstract(messages: list, session_id: str) -> str:
    """格式化为 Markdown 摘要"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 上一轮对话摘要",
        "",
        f"> 自动生成时间: {now}",
        f"> 来源会话: {session_id}",
        "",
        "---",
        "",
    ]
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (已截断)"
        if role in ("user", "human"):
            lines.append("## 用户提问\n")
            lines.append(content + "\n")
        elif role in ("assistant", "ai", "model"):
            lines.append("## Agent 回答\n")
            lines.append(content + "\n")
    lines.append("---")
    lines.append("*此文件由 SessionEnd hook 自动生成*")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
