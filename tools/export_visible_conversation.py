#!/usr/bin/env python3
"""Export user-visible Codex messages from a session JSONL file to Markdown.

System/developer messages, hidden reasoning, tool calls, and injected environment
context are intentionally excluded. Optional prefix substitutions remove
machine-specific path prefixes without changing the substantive conversation.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--stop-after-user-substring",
        help="Stop after exporting the first user message containing this text.",
    )
    parser.add_argument(
        "--replace-prefix",
        action="append",
        default=[],
        metavar="FROM=TO",
        help="Replace a machine-specific prefix; may be supplied repeatedly.",
    )
    return parser.parse_args()


def message_text(payload: dict) -> str:
    parts = []
    for item in payload.get("content", []):
        if item.get("type") in {"input_text", "output_text"}:
            parts.append(item.get("text", ""))
    return html.unescape("".join(parts)).strip()


def main() -> None:
    args = parse_args()
    replacements = []
    for item in args.replace_prefix:
        if "=" not in item:
            raise SystemExit(f"invalid --replace-prefix value: {item!r}")
        replacements.append(item.split("=", 1))

    exported: list[tuple[str, str, str]] = []
    with args.session.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("type") != "response_item":
                continue
            payload = record.get("payload", {})
            if payload.get("type") != "message":
                continue
            role = payload.get("role")
            if role not in {"user", "assistant"}:
                continue
            text = message_text(payload)
            if not text:
                continue
            if role == "user" and text.startswith(
                ("<recommended_plugins>", "<environment_context>")
            ):
                continue
            for old, new in replacements:
                text = text.replace(old, new)
            phase = payload.get("phase", "")
            exported.append((role, phase, text))
            if (
                role == "user"
                and args.stop_after_user_substring
                and args.stop_after_user_substring in text
            ):
                break

    lines = [
        "# 完整对话记录",
        "",
        "> 范围：按时间顺序收录用户与助手可见消息，包括进度更新与最终答复；",
        "> 不包含系统/开发者指令、隐藏推理、工具原始日志和自动注入的环境信息。",
        "> 为适合公开发布，仅将旧回复中的本机绝对路径前缀规范化为仓库相对路径，",
        "> 其余对话正文保持不变。",
        "> 历史文件迁移对应关系见 archive/README.md；旧结论以 V3 报告更正为准。",
        "",
    ]
    counters = {"user": 0, "assistant": 0}
    for role, phase, text in exported:
        counters[role] += 1
        if role == "user":
            heading = f"## 用户 {counters[role]}"
        elif phase == "commentary":
            heading = f"## 助手 {counters[role]} · 进度更新"
        else:
            heading = f"## 助手 {counters[role]} · 最终答复"
        lines.extend([heading, "", text, ""])

    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"exported {len(exported)} visible messages to {args.output}")


if __name__ == "__main__":
    main()
