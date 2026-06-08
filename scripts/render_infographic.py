#!/usr/bin/env python3
"""Render selected SVGFlow infographic DSL archetypes deterministically."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


LAYER_TONES = {
    "purple": {"fill": "rgb(60, 52, 137)", "stroke": "rgb(175, 169, 236)", "accent": "rgb(206, 203, 246)"},
    "teal": {"fill": "rgb(8, 80, 65)", "stroke": "rgb(93, 202, 165)", "accent": "rgb(159, 225, 203)"},
    "amber": {"fill": "rgb(99, 56, 6)", "stroke": "rgb(239, 159, 39)", "accent": "rgb(250, 199, 117)"},
    "coral": {"fill": "rgb(113, 43, 19)", "stroke": "rgb(240, 153, 123)", "accent": "rgb(245, 196, 179)"},
    "blue": {"fill": "rgb(25, 66, 125)", "stroke": "rgb(111, 177, 255)", "accent": "rgb(190, 219, 255)"},
    "gray": {"fill": "rgb(55, 55, 50)", "stroke": "rgb(156, 154, 146)", "accent": "rgb(222, 220, 209)"},
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def js_prompt(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def node_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
    if len(cleaned) < 6:
        return "dark-layered-architecture"
    return cleaned


def line_text(text: str, limit: int = 15) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def index_by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("id")): item for item in items if isinstance(item, dict) and item.get("id")}


def render_text(lines: list[str], x: int, y: int, class_name: str, anchor: str = "middle", line_gap: int = 16) -> list[str]:
    out = []
    for index, line in enumerate(lines):
        out.append(f'  <text class="{class_name}" x="{x}" y="{y + index * line_gap}" text-anchor="{anchor}">{esc(line)}</text>')
    return out


def clickable_group_open(node: dict[str, Any], interactions: dict[str, str]) -> str:
    target = str(node.get("id"))
    prompt = interactions.get(target)
    if not prompt:
        return ""
    label = esc(node.get("title", target))
    safe_prompt = esc(js_prompt(prompt))
    return (
        f'  <g role="button" tabindex="0" aria-label="{label}" '
        f'onclick="sendPrompt(\'{safe_prompt}\')" '
        f'onkeydown="if(event.key===\'Enter\'||event.key===\' \'){{sendPrompt(\'{safe_prompt}\')}}">'
    )


def render_chip(node: dict[str, Any], x: int, y: int, width: int, height: int, tone: str, interactions: dict[str, str]) -> list[str]:
    colors = LAYER_TONES.get(tone, LAYER_TONES["gray"])
    title = line_text(str(node.get("title", "")), 14)
    subtitle = line_text(str(node.get("subtitle", "")), 18)
    out: list[str] = []
    group_open = clickable_group_open(node, interactions)
    if group_open:
        out.append(group_open)
        prefix = "    "
    else:
        prefix = "  "
    out.append(f'{prefix}<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="{colors["fill"]}" stroke="{colors["stroke"]}" stroke-width="0.5"/>')
    out.append(f'{prefix}<text class="chip-title" x="{x + width // 2}" y="{y + 20}" text-anchor="middle">{esc(title)}</text>')
    if subtitle and height >= 40:
        out.append(f'{prefix}<text class="chip-sub" x="{x + width // 2}" y="{y + 38}" text-anchor="middle">{esc(subtitle)}</text>')
    if group_open:
        out.append("  </g>")
    return out


def render_dark_layered_architecture(data: dict[str, Any]) -> str:
    meta = data["meta"]
    content = data["content"]
    nodes = index_by_id(content.get("nodes", []))
    groups = content.get("groups", [])
    interactions = {
        str(item.get("target")): str(item.get("prompt"))
        for item in data.get("interactions", [])
        if item.get("action") == "sendPrompt" and item.get("target") and item.get("prompt")
    }
    svg_id = node_id(str(meta.get("title", "dark-layered-architecture")))

    width = 690
    height = 720
    layer_x = 40
    layer_w = 600
    layer_h = [104, 112, 130, 130]
    layer_y = [30, 160, 300, 460]
    layer_subtitles = [
        "AI决策中枢 · 大模型推理 · 业务编排",
        "云端AI训练 · 数据湖 · 服务编排 · 安全管理",
        "本地AI推理 · 实时响应 · 数据预处理 · 协议转换",
        "传感器 · 执行器 · 智能终端 · AI芯片端侧推理",
    ]

    out = [
        f'<svg class="svgflow" data-svgflow-id="{esc(svg_id)}" width="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" xml:lang="{esc(meta.get("locale", "zh-CN"))}" lang="{esc(meta.get("locale", "zh-CN"))}" dir="{esc(meta.get("textDirection", "ltr"))}">',
        f'  <title>{esc(meta.get("title", "Infographic"))}</title>',
        f'  <desc>{esc(meta.get("description", ""))}</desc>',
        "  <defs>",
        f'    <marker id="svgflow-{esc(svg_id)}-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '      <path d="M2 1L8 5L2 9" fill="none" stroke="#c2c0b6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
        "    </marker>",
        "  </defs>",
        "  <style>",
        "    .bg{fill:rgb(20,20,18)}.layer-title{font:600 14px system-ui,-apple-system,\"Segoe UI\",sans-serif;fill:rgb(250,249,245)}.layer-sub{font:400 12px system-ui,-apple-system,\"Segoe UI\",sans-serif;fill:rgb(194,192,182)}.chip-title{font:600 13px system-ui,-apple-system,\"Segoe UI\",sans-serif;fill:rgb(250,249,245)}.chip-sub{font:400 11px system-ui,-apple-system,\"Segoe UI\",sans-serif;fill:rgb(194,192,182)}.rail{font:400 12px system-ui,-apple-system,\"Segoe UI\",sans-serif;fill:rgb(194,192,182)}.legend{font:500 11px system-ui,-apple-system,\"Segoe UI\",sans-serif;fill:rgb(194,192,182)}.flow{fill:none;stroke:#9c9a92;stroke-width:1.2;opacity:.45}.soft{fill:none;stroke:rgba(222, 220, 209, 0.3);stroke-width:1;stroke-dasharray:4 3}",
        "  </style>",
        f'  <rect class="bg" x="0" y="0" width="{width}" height="{height}"/>',
    ]

    for index, group in enumerate(groups[:4]):
        tone = str(group.get("tone", "gray"))
        colors = LAYER_TONES.get(tone, LAYER_TONES["gray"])
        y = layer_y[index]
        h = layer_h[index]
        out.append(f'  <rect x="{layer_x}" y="{y}" width="{layer_w}" height="{h}" rx="14" fill="{colors["fill"]}" stroke="{colors["stroke"]}" stroke-width="0.5"/>')
        out.extend(render_text([str(group.get("title", ""))], 340, y + 30, "layer-title"))
        subtitle = str(group.get("subtitle") or (layer_subtitles[index] if index < len(layer_subtitles) else ""))
        out.extend(render_text([line_text(subtitle, 34)], 340, y + 50, "layer-sub"))

        members = [nodes[item] for item in group.get("members", []) if item in nodes]
        chip_y = y + (64 if h <= 112 else 66)
        gap = 16
        if len(members) <= 3:
            chip_w = [156, 156, 214][: len(members)]
            total = sum(chip_w) + gap * (len(members) - 1)
            cursor = layer_x + (layer_w - total) // 2
        else:
            chip_w = [132, 124, 132, 122][: len(members)]
            total = sum(chip_w) + gap * (len(members) - 1)
            cursor = layer_x + (layer_w - total) // 2
        chip_h = 28 if h <= 112 else 50
        for member_index, node in enumerate(members):
            current_w = chip_w[member_index] if member_index < len(chip_w) else 120
            out.extend(render_chip(node, cursor, chip_y, current_w, chip_h, tone, interactions))
            cursor += current_w + gap
        if index < min(3, len(groups) - 1):
            out.append(f'  <path class="flow" d="M340 {y + h}L340 {layer_y[index + 1] - 2}" marker-end="url(#svgflow-{esc(svg_id)}-arrow)"/>')

    out.append(f'  <path class="soft" d="M24 460L24 130" stroke="rgba(222, 220, 209, 0.3)" marker-end="url(#svgflow-{esc(svg_id)}-arrow)"/>')
    out.append('  <text class="rail" x="22" y="280" text-anchor="middle" transform="rotate(-90 22 280)">数据上行流</text>')
    out.append(f'  <path class="soft" d="M668 130L668 460" stroke="rgba(222, 220, 209, 0.3)" marker-end="url(#svgflow-{esc(svg_id)}-arrow)"/>')
    out.append('  <text class="rail" x="668" y="280" text-anchor="middle" transform="rotate(90 668 280)">AI 决策流</text>')

    legends = content.get("legends", [])
    legend_x = 176
    for legend in legends[:4]:
        tone = str(legend.get("tone", "gray"))
        colors = LAYER_TONES.get(tone, LAYER_TONES["gray"])
        out.append(f'  <rect x="{legend_x}" y="638" width="12" height="12" rx="2" fill="{colors["fill"]}"/>')
        out.append(f'  <text class="legend" x="{legend_x + 18}" y="648">{esc(line_text(str(legend.get("label", "")), 10))}</text>')
        legend_x += 92
    out.append('  <text class="legend" x="340" y="688" text-anchor="middle">点击各组件了解详细设计</text>')
    out.append("</svg>")
    return "\n".join(out)


def render(data: dict[str, Any]) -> str:
    style = data.get("style", {})
    if style.get("archetype") == "dark_layered_architecture":
        return render_dark_layered_architecture(data)
    raise SystemExit("Unsupported infographic archetype. Expected style.archetype='dark_layered_architecture'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render SVGFlow infographic DSL to SVG.")
    parser.add_argument("dsl", help="Path to infographic DSL JSON.")
    parser.add_argument("--output", "-o", help="Output SVG path. Defaults to stdout.")
    args = parser.parse_args()

    data = json.loads(Path(args.dsl).read_text(encoding="utf-8"))
    svg = render(data)
    if args.output:
        Path(args.output).write_text(svg + "\n", encoding="utf-8")
    else:
        print(svg)


if __name__ == "__main__":
    main()
