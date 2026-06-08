#!/usr/bin/env python3
"""
Validation helper for SVGFlow skill packages and SVG outputs.

This script intentionally avoids external dependencies. It checks XML
well-formedness, package metadata, Flow DSL fixtures, and a few
SVGFlow-specific rendering constraints.
"""

from __future__ import annotations

import re
import sys
import json
import io
import contextlib
import copy
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def ok(message: str) -> None:
    print(f"[OK] {message}")


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")


def contains_forbidden_control_chars(text: str) -> bool:
    return bool(re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text))


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def parse_float_attrs(tag: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for attr, raw_value in re.findall(r'\b([a-zA-Z][a-zA-Z0-9_-]*)="(-?\d+(?:\.\d+)?)"', tag):
        values[attr] = float(raw_value)
    return values


def check_point(path: Path, label: str, x: float, y: float, width: int, height: int) -> None:
    if x < 0 or y < 0:
        fail(f"{path} {label} contains negative coordinate: {x},{y}")
    if x > width:
        fail(f"{path} {label} x coordinate exceeds viewBox width: {x}")
    if y > height:
        fail(f"{path} {label} y coordinate exceeds viewBox height: {y}")


def validate_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")

    if not text.lstrip().startswith("<svg"):
        fail("SVG must start with <svg")

    if not text.rstrip().endswith("</svg>"):
        fail("SVG must end with </svg>")

    if "<?xml" in text:
        fail("XML declaration is not allowed")

    if "```" in text:
        fail("Markdown code fences are not allowed")

    if "{{" in text or "}}" in text:
        fail("Template placeholders must be replaced before validation")

    if "<!--" in text:
        fail("Comments are not allowed")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"XML parse error: {exc}")

    view_box = root.attrib.get("viewBox", "")
    m = re.match(r"0\s+0\s+680\s+(\d+)", view_box)
    if not m:
        fail("viewBox must be '0 0 680 H'")

    height = int(m.group(1))
    if height < 120:
        fail("viewBox height is too small")

    root_class = root.attrib.get("class", "")
    require("svgflow" in root_class.split(), f"{path} root svg missing class='svgflow'")
    diagram_id = root.attrib.get("data-svgflow-id", "")
    require(bool(re.match(r"^[a-z][a-z0-9-]*$", diagram_id)), f"{path} root svg missing valid data-svgflow-id")
    lang = root.attrib.get("lang") or root.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
    require(isinstance(lang, str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", lang), f"{path} root svg missing valid lang/xml:lang")
    require(root.attrib.get("dir") in {"ltr", "rtl", "auto"}, f"{path} root svg dir must be ltr, rtl, or auto")

    require(root.find("{http://www.w3.org/2000/svg}title") is not None, f"{path} missing <title>")
    require(root.find("{http://www.w3.org/2000/svg}desc") is not None, f"{path} missing <desc>")
    require(root.find("{http://www.w3.org/2000/svg}defs") is not None, f"{path} missing <defs>")

    marker_ids = re.findall(r"<marker\b[^>]*\bid=\"([^\"]+)\"", text)
    require(marker_ids, f"{path} missing marker id")
    require(len(marker_ids) == len(set(marker_ids)), f"{path} duplicate marker ids: {marker_ids}")
    for marker_id in marker_ids:
        require(marker_id != "arrow", f"{path} marker id must be diagram-scoped, not 'arrow'")

    node_count = len(re.findall(r'class="[^"]*\bnode\b', text))
    if node_count > 8:
        fail(f"Too many nodes: {node_count}")

    color_classes = set(re.findall(r'class="[^"]*\bc-([a-z]+)\b', text))
    if len(color_classes) > 3:
        fail(f"Too many color classes: {sorted(color_classes)}")

    for match in re.finditer(r"<rect\b[^>]*>", text):
        tag = match.group(0)
        attrs = parse_float_attrs(tag)
        if {"x", "y", "width", "height"}.issubset(attrs):
            right = attrs["x"] + attrs["width"]
            bottom = attrs["y"] + attrs["height"]
            check_point(path, "rect origin", attrs["x"], attrs["y"], 680, height)
            check_point(path, "rect bottom-right", right, bottom, 680, height)

    for match in re.finditer(r"<polygon\b[^>]*\bpoints=\"([^\"]+)\"[^>]*>", text):
        points = match.group(1)
        for raw_point in points.split():
            if "," not in raw_point:
                fail(f"{path} malformed polygon point: {raw_point}")
            raw_x, raw_y = raw_point.split(",", 1)
            check_point(path, "polygon", float(raw_x), float(raw_y), 680, height)

    for match in re.finditer(r"<path\b[^>]*>", text):
        tag = match.group(0)
        if 'fill="none"' not in tag and "fill='none'" not in tag:
            fail(f"path missing fill='none': {tag}")

    for match in re.finditer(r"<text\b[^>]*>", text):
        tag = match.group(0)
        if "class=" not in tag:
            fail(f"text missing class: {tag}")

    for match in re.finditer(r'<g\b[^>]*class="[^"]*\bnode\b[^"]*"[^>]*>(.*?)</g>', text, re.S):
        node_body = match.group(1)
        for text_match in re.finditer(r"<text\b[^>]*>", node_body):
            tag = text_match.group(0)
            if 'dominant-baseline="central"' not in tag:
                fail(f"node text missing dominant-baseline='central': {tag}")

    for attr, raw_value in re.findall(r"\b(x|y|x1|y1|x2|y2|cx|cy)=\"(-?\d+(?:\.\d+)?)\"", text):
        value = float(raw_value)
        if value < 0:
            fail(f"negative coordinate {attr}={raw_value}")
        if attr in {"x", "x1", "x2", "cx"} and value > 680:
            fail(f"x coordinate exceeds viewBox width: {attr}={raw_value}")
        if attr in {"y", "y1", "y2", "cy"} and value > height:
            fail(f"y coordinate exceeds viewBox height: {attr}={raw_value}")

    for path_match in re.finditer(r'<path\b[^>]*\bd="([^"]+)"', text):
        numbers = [float(number) for number in re.findall(r"-?\d+(?:\.\d+)?", path_match.group(1))]
        for number in numbers:
            if number < 0:
                fail(f"path contains negative coordinate: {path_match.group(1)}")
        if len(numbers) % 2 == 0:
            for x, y in zip(numbers[::2], numbers[1::2]):
                check_point(path, "path", x, y, 680, height)

    if re.search(r"<polygon\b[^>]*(fill=|stroke=)", text):
        warn("polygon contains fill or stroke. Prefer class-based styling.")

    ok(f"SVGFlow checks passed: {path}")


def validate_interactive_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    require(text.lstrip().startswith("<svg"), f"{path} must start with <svg")
    require(text.rstrip().endswith("</svg>"), f"{path} must end with </svg>")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")
    view_box = root.attrib.get("viewBox", "")
    require(bool(re.match(r"0\s+0\s+680\s+(\d+)", view_box)), f"{path} viewBox must be '0 0 680 H'")
    height = int(re.match(r"0\s+0\s+680\s+(\d+)", view_box).group(1))
    require(height >= 640, f"{path} interactive SVG height should be at least 640")
    require(root.find("{http://www.w3.org/2000/svg}title") is not None, f"{path} missing <title>")
    require(root.find("{http://www.w3.org/2000/svg}desc") is not None, f"{path} missing <desc>")
    require("sendPrompt(" in text, f"{path} missing sendPrompt interactions")
    require(text.count("onclick=") >= 8, f"{path} should have at least 8 clickable modules")
    require(text.count("<rect") >= 12, f"{path} should include chapter and summary cards")
    for match in re.finditer(r"<rect\b[^>]*>", text):
        attrs = parse_float_attrs(match.group(0))
        if {"x", "y", "width", "height"}.issubset(attrs):
            check_point(path, "rect origin", attrs["x"], attrs["y"], 680, height)
            check_point(path, "rect bottom-right", attrs["x"] + attrs["width"], attrs["y"] + attrs["height"], 680, height)
    ok(f"Interactive SVG checks passed: {path}")


def validate_infographic_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    require(text.lstrip().startswith("<svg"), f"{path} must start with <svg")
    require(text.rstrip().endswith("</svg>"), f"{path} must end with </svg>")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")
    view_box = root.attrib.get("viewBox", "")
    match = re.match(r"0\s+0\s+(680|690)\s+(\d+)", view_box)
    require(bool(match), f"{path} viewBox must be '0 0 680 H' or '0 0 690 H'")
    width = int(match.group(1))
    height = int(match.group(2))
    require(240 <= height <= 1600, f"{path} infographic SVG height is invalid")
    require(root.find("{http://www.w3.org/2000/svg}title") is not None, f"{path} missing <title>")
    require(root.find("{http://www.w3.org/2000/svg}desc") is not None, f"{path} missing <desc>")
    require(root.find("{http://www.w3.org/2000/svg}defs") is not None, f"{path} missing <defs>")
    require(text.count("<rect") >= 6, f"{path} should include groups, nodes, labels, and legends")
    require(text.count("<path") >= 4, f"{path} should include multiple connectors")
    require("sendPrompt(" in text, f"{path} should include sendPrompt interactions when interactions exist")
    require("<mask" in text or "stroke=\"rgba(222, 220, 209, 0.3)\"" in text, f"{path} should protect labels over connectors")
    legend_rects = 0
    for rect in re.finditer(r"<rect\b[^>]*>", text):
        attrs = parse_float_attrs(rect.group(0))
        if {"x", "y", "width", "height"}.issubset(attrs):
            check_point(path, "rect origin", attrs["x"], attrs["y"], width, height)
            check_point(path, "rect bottom-right", attrs["x"] + attrs["width"], attrs["y"] + attrs["height"], width, height)
            if 8 <= attrs["width"] <= 16 and 8 <= attrs["height"] <= 16 and attrs["y"] >= height - 100:
                legend_rects += 1
    require(legend_rects >= 2, f"{path} should include a compact legend")
    ok(f"Infographic SVG checks passed: {path}")


def validate_visual_quality_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")
    view_box = root.attrib.get("viewBox", "")
    match = re.match(r"0\s+0\s+(680|690)\s+(\d+)", view_box)
    require(bool(match), f"{path} visual quality check requires a 680/690-wide viewBox")
    width = int(match.group(1))
    height = int(match.group(2))

    rects: list[dict[str, float]] = []
    for rect in re.finditer(r"<rect\b[^>]*>", text):
        attrs = parse_float_attrs(rect.group(0))
        if {"x", "y", "width", "height"}.issubset(attrs):
            rects.append(attrs)
            check_point(path, "rect origin", attrs["x"], attrs["y"], width, height)
            check_point(path, "rect bottom-right", attrs["x"] + attrs["width"], attrs["y"] + attrs["height"], width, height)

    require(len(rects) >= 6, f"{path} should have enough framed elements for an infographic")
    require("<mask" in text or "rgba(222, 220, 209, 0.3)" in text, f"{path} connector labels need masks or label backgrounds")

    visible_texts = re.findall(r"<text\b[^>]*>([^<]+)</text>", text)
    require(visible_texts, f"{path} should contain visible text")
    for value in visible_texts:
        normalized = value.strip()
        if normalized:
            require(len(normalized) <= 48, f"{path} text is too long for stable SVG layout: {normalized}")

    legend_like_rects = [rect for rect in rects if 8 <= rect["width"] <= 16 and 8 <= rect["height"] <= 16 and rect["y"] >= height - 120]
    require(len(legend_like_rects) >= 2, f"{path} should include compact legend swatches when color semantics repeat")

    fills = set(re.findall(r'fill="rgb\(([^"]+)\)"', text))
    require(len(fills) >= 4, f"{path} palette is too narrow for official-style infographic output")

    clickable_count = text.count("onclick=")
    if "sendPrompt(" in text:
        require(clickable_count >= 1, f"{path} sendPrompt interactions should be attached to clickable groups")

    group_rects = [rect for rect in rects if rect["width"] >= 500 and rect["height"] >= 120]
    if group_rects:
        for group_rect in group_rects:
            contained = 0
            for rect in rects:
                if rect is group_rect:
                    continue
                if (
                    rect["x"] >= group_rect["x"]
                    and rect["y"] >= group_rect["y"]
                    and rect["x"] + rect["width"] <= group_rect["x"] + group_rect["width"]
                    and rect["y"] + rect["height"] <= group_rect["y"] + group_rect["height"]
                ):
                    contained += 1
            require(contained >= 1, f"{path} large group containers should visibly contain child cards")

    ok(f"Visual quality checks passed: {path}")


RTL_RE = re.compile(r"[\u0590-\u05ff\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


def text_fit_signal_set(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")

    lang = root.attrib.get("lang") or root.attrib.get("{http://www.w3.org/XML/1998/namespace}lang") or ""
    direction = root.attrib.get("dir") or ""
    all_visible_text = " ".join(root.itertext())
    signals: set[str] = set()

    if re.search(r"letter-spacing\s*:\s*-\d|letter-spacing=\"-", text):
        fail(f"{path} contains negative letter-spacing")
    signals.add("stableLetterSpacing")

    if CJK_RE.search(all_visible_text):
        require(bool(re.match(r"^zh(-|$)|^ja(-|$)|^ko(-|$)", lang)), f"{path} CJK text requires a matching lang/xml:lang")
        signals.add("cjkLocale")

    if RTL_RE.search(all_visible_text):
        require(direction == "rtl", f"{path} RTL text requires dir='rtl'")
        require(bool(re.match(r"^(ar|he|fa|ur)(-|$)", lang)), f"{path} RTL text requires matching lang/xml:lang")
        signals.add("rtlLocale")

    if re.search(r"font-size\s*:\s*[^;\"']*vw|\bfont-size=\"[^\"]*vw", text):
        fail(f"{path} font-size must not scale with viewport width")

    text_blocks = re.findall(r"<text\b([^>]*)>(.*?)</text>", text, re.S)
    require(text_blocks, f"{path} contains no text blocks to fit")
    for attrs, body in text_blocks:
        has_fit = "data-fit=" in attrs or "textLength=" in attrs or "<tspan" in body
        plain = re.sub(r"<[^>]+>", " ", body)
        plain = re.sub(r"\s+", " ", plain).strip()
        if not plain:
            continue
        if has_fit:
            signals.add("explicitFit")
        if len(plain) > 56:
            require(has_fit, f"{path} text block needs wrapping or fit metadata: {plain}")
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{23,}", plain):
            require(has_fit, f"{path} unbreakable text needs wrapping or fit metadata: {token}")

    return signals


def validate_text_fit_svg(path: Path) -> None:
    text_fit_signal_set(path)
    ok(f"Text-fit checks passed: {path}")


def require_safe_send_prompt_calls(path: Path, handler: str) -> None:
    cursor = 0
    while True:
        call_index = handler.find("sendPrompt", cursor)
        if call_index == -1:
            return
        open_index = handler.find("(", call_index + len("sendPrompt"))
        require(open_index != -1, f"{path} sendPrompt handler must use an escaped prompt string")
        cursor = open_index + 1
        while cursor < len(handler) and handler[cursor].isspace():
            cursor += 1
        require(cursor < len(handler) and handler[cursor] in {"'", '"'}, f"{path} sendPrompt handler must use an escaped prompt string")
        quote = handler[cursor]
        cursor += 1
        escaped = False
        while cursor < len(handler):
            char = handler[cursor]
            if escaped:
                escaped = False
                cursor += 1
                continue
            if char == "\\":
                escaped = True
                cursor += 1
                continue
            if char == quote:
                cursor += 1
                while cursor < len(handler) and handler[cursor].isspace():
                    cursor += 1
                require(cursor < len(handler) and handler[cursor] == ")", f"{path} sendPrompt handler must use an escaped prompt string")
                cursor += 1
                break
            cursor += 1
        else:
            fail(f"{path} sendPrompt handler must use an escaped prompt string")


def interaction_accessibility_signal_set(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")

    if re.search(r"<script\b[^>]*>.*?sendPrompt\s*\(", text, re.S):
        fail(f"{path} must not call sendPrompt from script; attach prompts to visible controls")

    clickable_groups = [
        element
        for element in root.iter()
        if element.tag.split("}")[-1] == "g" and "sendPrompt" in element.attrib.get("onclick", "")
    ]
    require(clickable_groups, f"{path} contains no clickable SVG groups")
    signals = {"safePromptPlacement"}
    named = 0
    keyboard = 0
    escaped_prompt = 0
    for element in clickable_groups:
        attrs = element.attrib
        require(attrs.get("role") == "button", f"{path} clickable SVG groups must declare role='button'")
        require(attrs.get("tabindex") == "0", f"{path} clickable SVG groups must be keyboard focusable with tabindex='0'")
        has_name = bool(attrs.get("aria-label") or attrs.get("aria-labelledby"))
        require(has_name, f"{path} clickable SVG groups need aria-label or aria-labelledby")
        named += 1
        onclick = attrs.get("onclick", "")
        onkeydown = attrs.get("onkeydown", "")
        require_safe_send_prompt_calls(path, onclick)
        if "sendPrompt" in onkeydown:
            require_safe_send_prompt_calls(path, onkeydown)
        escaped_prompt += 1
        has_keyboard_handler = bool(onkeydown) and ("Enter" in onkeydown or " " in onkeydown or "Space" in onkeydown)
        require(has_keyboard_handler, f"{path} clickable SVG groups need a keyboard handler for Enter or Space")
        keyboard += 1
    if named == len(clickable_groups):
        signals.add("namedControls")
    if keyboard == len(clickable_groups):
        signals.add("keyboardAccess")
    if escaped_prompt == len(clickable_groups):
        signals.add("safePromptEscaping")
    return signals


def validate_interaction_accessibility_svg(path: Path) -> None:
    interaction_accessibility_signal_set(path)
    ok(f"Interaction accessibility checks passed: {path}")


HTML_DANGEROUS_TAGS = {"iframe", "object", "embed", "img", "link", "meta"}
HTML_ALLOWED_EVENT_ATTRS = {"onclick", "onkeydown"}
HTML_ALLOWED_HANDLER_PREFIXES = ("sendPrompt(", "move(")


def escaping_safety_signal_set(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    suffix = path.suffix.lower()
    signals: set[str] = set()

    if suffix == ".svg":
        try:
            ET.fromstring(text)
        except ET.ParseError as exc:
            fail(f"{path} XML parse error: {exc}")
        if any(entity in text for entity in ("&amp;", "&lt;", "&gt;", "&quot;", "&apos;")):
            signals.add("xmlEntities")
        if "sendPrompt" in text:
            signals.update(interaction_accessibility_signal_set(path))
            signals.add("safeInlineHandlers")
        return signals

    if suffix == ".html":
        for script_body in re.findall(r"<script\b[^>]*>(.*?)</script>", text, re.S | re.I):
            lowered_script = script_body.lower()
            require("sendprompt" not in lowered_script, f"{path} must not call sendPrompt from script; attach prompts to visible controls")
            require("javascript:" not in lowered_script, f"{path} unsafe javascript URI in script")
            require("document.write" not in lowered_script, f"{path} unsafe script body")
            require("eval(" not in lowered_script and "new function" not in lowered_script, f"{path} unsafe script body")
        for match in re.finditer(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9:-]*)\b([^>]*)>", text):
            tag = match.group(1).lower()
            attrs = match.group(2)
            require(tag not in HTML_DANGEROUS_TAGS, f"{path} unsafe HTML tag: <{tag}>")
            for attr, _quote, raw_value in re.findall(r"\b([a-zA-Z][a-zA-Z0-9:-]*)\s*=\s*([\"'])(.*?)\2", attrs, re.S):
                attr_name = attr.lower()
                value = raw_value.strip()
                require("javascript:" not in value.lower(), f"{path} unsafe javascript URI in {attr_name}")
                if attr_name.startswith("on"):
                    require(attr_name in HTML_ALLOWED_EVENT_ATTRS, f"{path} unsafe event handler attribute: {attr_name}")
                    require(
                        value.startswith(HTML_ALLOWED_HANDLER_PREFIXES),
                        f"{path} unsafe event handler body for {attr_name}",
                    )
                    if "sendPrompt" in value:
                        require_safe_send_prompt_calls(path, value)
                        signals.add("safeInlineHandlers")
        if "&lt;" in text or "&amp;" in text or "&gt;" in text:
            signals.add("safeHtmlText")
        elif not re.search(r"<\s*(script|iframe|object|embed|img)\b", text, re.I):
            signals.add("safeHtmlText")
        return signals

    fail(f"{path} escaping safety fixture must be .svg or .html")


def validate_escaping_safety_asset(path: Path) -> None:
    escaping_safety_signal_set(path)
    ok(f"Escaping safety checks passed: {path}")


def validate_architecture_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    require(text.lstrip().startswith("<svg"), f"{path} must start with <svg")
    require(text.rstrip().endswith("</svg>"), f"{path} must end with </svg>")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")
    view_box = root.attrib.get("viewBox", "")
    require(bool(re.match(r"0\s+0\s+680\s+(\d+)", view_box)), f"{path} viewBox must be '0 0 680 H'")
    height = int(re.match(r"0\s+0\s+680\s+(\d+)", view_box).group(1))
    require(height >= 560, f"{path} architecture SVG height should be at least 560")
    require(root.find("{http://www.w3.org/2000/svg}title") is not None, f"{path} missing <title>")
    require(root.find("{http://www.w3.org/2000/svg}desc") is not None, f"{path} missing <desc>")
    require("sendPrompt(" in text, f"{path} missing sendPrompt interactions")
    require(text.count("onclick=") >= 10, f"{path} should have at least 10 clickable details")
    require(text.count("<rect") >= 15, f"{path} should include layers, zones, and chips")
    large_rects = 0
    nested_rects = 0
    for match in re.finditer(r"<rect\b[^>]*>", text):
        attrs = parse_float_attrs(match.group(0))
        if {"x", "y", "width", "height"}.issubset(attrs):
            check_point(path, "rect origin", attrs["x"], attrs["y"], 680, height)
            check_point(path, "rect bottom-right", attrs["x"] + attrs["width"], attrs["y"] + attrs["height"], 680, height)
            if attrs["width"] >= 500 and attrs["height"] >= 44:
                large_rects += 1
            if 120 <= attrs["width"] <= 220 and attrs["height"] >= 80:
                nested_rects += 1
    require(large_rects >= 3, f"{path} should contain multiple full-width architecture layers")
    require(nested_rects >= 3, f"{path} should contain nested zone or component cards")
    ok(f"Architecture SVG checks passed: {path}")


def validate_walkthrough_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    require("<h2" in text and "sr-only" in text, f"{path} missing accessible hidden heading")
    require("prefers-reduced-motion: no-preference" in text, f"{path} animations must respect reduced-motion")
    require("@keyframes pulse" in text, f"{path} missing pulse animation")
    require("@keyframes travel" in text, f"{path} missing travel animation")
    require("class=\"fl-step active\"" in text, f"{path} missing active first step")
    step_count = len(re.findall(r'class="fl-step', text))
    require(2 <= step_count <= 8, f"{path} should contain 2 to 8 steps")
    require(text.count("<svg") == step_count, f"{path} should contain one SVG per step")
    require("id=\"dots\"" in text, f"{path} missing progress dots")
    require("id=\"btn-prev\"" in text and "id=\"btn-next\"" in text, f"{path} missing navigation buttons")
    require("function render()" in text and "function move(" in text, f"{path} missing walkthrough controls")
    require("labels =" in text and "total =" in text, f"{path} missing step labels")
    require("anim-pulse" in text and "anim-travel" in text, f"{path} missing animated SVG states")
    require("disabled" in text, f"{path} controls should manage disabled state")
    require("aria-label" in text, f"{path} controls need accessible labels")
    for svg_match in re.finditer(r"<svg\b.*?</svg>", text, re.S):
        svg_text = svg_match.group(0)
        try:
            root = ET.fromstring(svg_text)
        except ET.ParseError as exc:
            fail(f"{path} embedded SVG parse error: {exc}")
        view_box = root.attrib.get("viewBox", "")
        require(bool(re.match(r"0\s+0\s+680\s+(\d+)", view_box)), f"{path} embedded SVG viewBox must be '0 0 680 H'")
        height = int(re.match(r"0\s+0\s+680\s+(\d+)", view_box).group(1))
        require(root.find("{http://www.w3.org/2000/svg}title") is not None, f"{path} embedded SVG missing <title>")
        require(root.find("{http://www.w3.org/2000/svg}desc") is not None, f"{path} embedded SVG missing <desc>")
        for rect_match in re.finditer(r"<rect\b[^>]*>", svg_text):
            attrs = parse_float_attrs(rect_match.group(0))
            if {"x", "y", "width", "height"}.issubset(attrs):
                check_point(path, "embedded rect origin", attrs["x"], attrs["y"], 680, height)
                check_point(path, "embedded rect bottom-right", attrs["x"] + attrs["width"], attrs["y"] + attrs["height"], 680, height)
    ok(f"Walkthrough HTML checks passed: {path}")


def validate_system_loop_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    require(text.lstrip().startswith("<svg"), f"{path} must start with <svg")
    require(text.rstrip().endswith("</svg>"), f"{path} must end with </svg>")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")
    view_box = root.attrib.get("viewBox", "")
    require(bool(re.match(r"0\s+0\s+680\s+(\d+)", view_box)), f"{path} viewBox must be '0 0 680 H'")
    height = int(re.match(r"0\s+0\s+680\s+(\d+)", view_box).group(1))
    require(300 <= height <= 620, f"{path} system loop SVG height should be compact")
    require(root.find("{http://www.w3.org/2000/svg}title") is not None, f"{path} missing <title>")
    require(root.find("{http://www.w3.org/2000/svg}desc") is not None, f"{path} missing <desc>")
    require(text.count("onclick=") >= 2, f"{path} should include clickable actors")
    require(text.count("<path") >= 4, f"{path} should include loop signal paths")
    require(text.count("marker-end=") >= 4, f"{path} should include directional signal arrows")
    require("stroke-dasharray" in text, f"{path} should include dashed secondary paths")
    require("<mask" in text or text.count("<rect") >= 6, f"{path} should include label gap masks or label backgrounds")
    label_rects = 0
    actor_rects = 0
    for match in re.finditer(r"<rect\b[^>]*>", text):
        attrs = parse_float_attrs(match.group(0))
        if {"x", "y", "width", "height"}.issubset(attrs):
            check_point(path, "rect origin", attrs["x"], attrs["y"], 680, height)
            check_point(path, "rect bottom-right", attrs["x"] + attrs["width"], attrs["y"] + attrs["height"], 680, height)
            if attrs["width"] >= 160 and attrs["height"] >= 40:
                actor_rects += 1
            if 50 <= attrs["width"] <= 160 and 18 <= attrs["height"] <= 32:
                label_rects += 1
    require(actor_rects >= 3, f"{path} should contain at least three actor/guard cards")
    require(label_rects >= 3, f"{path} should contain labeled signal chips")
    ok(f"System loop SVG checks passed: {path}")


def validate_module_grid_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    require("<h2" in text and "sr-only" in text, f"{path} missing accessible hidden heading")
    require("display:grid" in text, f"{path} missing CSS grid layout")
    require("grid-template-columns" in text, f"{path} missing grid column definition")
    require("@media" in text and "grid-template-columns:1fr" in text, f"{path} missing responsive one-column fallback")
    require("var(--color-" in text, f"{path} should use host color tokens")
    require("var(--border-radius" in text, f"{path} should use host radius tokens")
    card_count = text.count('class="mod-card"')
    require(2 <= card_count <= 8, f"{path} should contain 2 to 8 module cards")
    require(text.count('class="mod-title"') == card_count, f"{path} each card needs a title")
    require(text.count('class="mod-sub"') == card_count, f"{path} each card needs a subtitle")
    require(text.count('class="mod-btn"') == card_count, f"{path} each card needs a CTA button")
    require(text.count("onclick=\"sendPrompt(") == card_count, f"{path} each button should call sendPrompt")
    require(text.count('class="mod-item"') >= card_count * 3, f"{path} each card should include at least 3 detail items")
    require(text.count("mod-label") >= card_count * 3, f"{path} detail items should include labels")
    for tone in ["tone-info", "tone-warn", "tone-ok", "tone-neutral"]:
        require(tone in text, f"{path} missing semantic label tone: {tone}")
    ok(f"Module grid HTML checks passed: {path}")


def production_html_contract_signal_set(path: Path, html_type: str) -> set[str]:
    text = path.read_text(encoding="utf-8")
    signals = set(escaping_safety_signal_set(path))
    signals.add("safeHtml")
    if "<h2" in text and "sr-only" in text:
        signals.add("accessibleHeading")

    if html_type == "walkthrough":
        validate_walkthrough_html(path)
        if "prefers-reduced-motion: no-preference" in text:
            signals.add("reducedMotion")
        if "id=\"btn-prev\"" in text and "id=\"btn-next\"" in text and "aria-label" in text:
            signals.add("responsiveControls")
        embedded_svgs = list(re.finditer(r"<svg\b.*?</svg>", text, re.S))
        if embedded_svgs and all("<title" in match.group(0) and "<desc" in match.group(0) and 'role="img"' in match.group(0) for match in embedded_svgs):
            signals.add("embeddedSvgA11y")
    elif html_type == "module_grid":
        validate_module_grid_html(path)
        if "@media" in text and "grid-template-columns:1fr" in text:
            signals.add("responsiveGrid")
        if "var(--color-" in text and "var(--border-radius" in text:
            signals.add("hostTokens")
        if text.count('class="mod-btn"') >= 1 and text.count("onclick=\"sendPrompt(") == text.count('class="mod-btn"'):
            signals.add("actionButtons")
    else:
        fail(f"{path} production HTML contract type is invalid: {html_type}")
    return signals


def validate_production_html_contract_asset(path: Path, html_type: str) -> None:
    production_html_contract_signal_set(path, html_type)
    ok(f"Production HTML contract checks passed: {path}")


def style_block_text(text: str) -> str:
    return "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", text, re.S | re.I))


def render_surface_signal_set(path: Path, html_type: str) -> set[str]:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    style_text = style_block_text(text)
    compact_style = re.sub(r"\s+", "", style_text.lower())
    signals: set[str] = set(escaping_safety_signal_set(path))

    if "overflow-wrap:anywhere" in compact_style or "word-break:break-word" in compact_style:
        signals.add("overflowProtection")
    else:
        fail(f"{path} missing overflow protection for narrow render surfaces")

    if html_type == "walkthrough":
        validate_walkthrough_html(path)
        svg_tags = re.findall(r"<svg\b[^>]*>", text, re.I)
        require(svg_tags, f"{path} missing embedded SVGs")
        for tag in svg_tags:
            require('width="100%"' in tag or "width='100%'" in tag, f"{path} embedded SVGs must scale with width=\"100%\"")
            require("viewBox=" in tag, f"{path} embedded SVGs need viewBox")
            require("role=\"img\"" in tag or "role='img'" in tag, f"{path} embedded SVGs need role='img'")
        signals.add("scalableSvg")
        require("class=\"fl-step active\"" in text, f"{path} needs deterministic initial active step")
        require("var cur = 0" in text or "let cur = 0" in text or "data-current=\"0\"" in text, f"{path} needs deterministic initial state")
        signals.add("deterministicInitialState")
        require("prefers-reduced-motion" in text, f"{path} missing motion guard")
        signals.add("motionGuard")
        button_tags = re.findall(r"<button\b[^>]*>", text, re.I)
        require(button_tags, f"{path} missing controls")
        for tag in button_tags:
            tag_compact = re.sub(r"\s+", "", tag.lower())
            require("min-height:32px" in tag_compact or "min-width:32px" in tag_compact, f"{path} click targets need stable minimum sizing")
        signals.add("controlTargetSize")
    elif html_type == "module_grid":
        validate_module_grid_html(path)
        require("@media" in text and "grid-template-columns:1fr" in compact_style, f"{path} missing responsive grid fallback")
        signals.add("responsiveGrid")
        require("min-width:0" in compact_style, f"{path} cards need min-width:0 to avoid grid overflow")
        signals.add("stableCards")
        require("var(--color-" in text and "var(--border-radius" in text, f"{path} missing host token usage")
        signals.add("hostTokenFallback")
        require(".mod-btn" in text, f"{path} missing module buttons")
        mod_btn_rule = re.search(r"\.mod-btn\s*\{([^}]*)\}", style_text, re.S)
        require(bool(mod_btn_rule), f"{path} missing .mod-btn rule")
        button_rule = re.sub(r"\s+", "", mod_btn_rule.group(1).lower())
        require("min-height:32px" in button_rule or "padding:6px12px" in button_rule or "padding:6px16px" in button_rule, f"{path} click targets need stable minimum sizing")
        signals.add("controlTargetSize")
    else:
        fail(f"{path} render surface type is invalid: {html_type}")
    return signals


def validate_render_surface_asset(path: Path, html_type: str) -> None:
    render_surface_signal_set(path, html_type)
    ok(f"Render surface checks passed: {path}")


def infer_html_type(path: Path) -> str:
    name = path.name
    if name.endswith(".walkthrough.html"):
        return "walkthrough"
    if name.endswith(".module_grid.html"):
        return "module_grid"
    fail(f"{path} cannot infer HTML artifact type")


def validate_production_html_contract_inferred(path: Path) -> None:
    validate_production_html_contract_asset(path, infer_html_type(path))


def validate_render_surface_inferred(path: Path) -> None:
    validate_render_surface_asset(path, infer_html_type(path))


def validate_agentic_pipeline_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    require(text.lstrip().startswith("<svg"), f"{path} must start with <svg")
    require(text.rstrip().endswith("</svg>"), f"{path} must end with </svg>")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")
    view_box = root.attrib.get("viewBox", "")
    m = re.match(r"0\s+0\s+(680|690)\s+(\d+)", view_box)
    require(bool(m), f"{path} viewBox must be '0 0 680 H' or '0 0 690 H'")
    width = int(m.group(1))
    height = int(m.group(2))
    require(420 <= height <= 900, f"{path} agentic pipeline SVG height is invalid")
    require(root.find("{http://www.w3.org/2000/svg}title") is not None, f"{path} missing <title>")
    require(root.find("{http://www.w3.org/2000/svg}desc") is not None, f"{path} missing <desc>")
    require(text.count("onclick=") >= 8, f"{path} should include clickable pipeline modules")
    require(text.count("<rect") >= 10, f"{path} should include entry, orchestrator, workers, sources, synthesizer, and output")
    require(text.count("stroke-dasharray") >= 5, f"{path} should include fan-out/fan-in dashed connectors and replan loop")
    require("<mask" in text, f"{path} should include label gap mask")
    require("<path" in text and "Q" in text, f"{path} should include a curved replanning loop")
    worker_like = 0
    source_like = 0
    for match in re.finditer(r"<rect\b[^>]*>", text):
        attrs = parse_float_attrs(match.group(0))
        if {"x", "y", "width", "height"}.issubset(attrs):
            check_point(path, "rect origin", attrs["x"], attrs["y"], width, height)
            check_point(path, "rect bottom-right", attrs["x"] + attrs["width"], attrs["y"] + attrs["height"], width, height)
            if 120 <= attrs["width"] <= 160 and 44 <= attrs["height"] <= 70 and 180 <= attrs["y"] <= 290:
                worker_like += 1
            if 120 <= attrs["width"] <= 160 and 44 <= attrs["height"] <= 70 and 300 <= attrs["y"] <= 400:
                source_like += 1
    require(worker_like >= 2, f"{path} should include multiple worker-agent cards")
    require(source_like >= 2, f"{path} should include matching knowledge-source cards")
    ok(f"Agentic pipeline SVG checks passed: {path}")


def validate_phased_pipeline_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(not contains_forbidden_control_chars(text), f"{path} contains forbidden control characters")
    require(text.lstrip().startswith("<svg"), f"{path} must start with <svg")
    require(text.rstrip().endswith("</svg>"), f"{path} must end with </svg>")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")
    view_box = root.attrib.get("viewBox", "")
    m = re.match(r"0\s+0\s+680\s+(\d+)", view_box)
    require(bool(m), f"{path} viewBox must be '0 0 680 H'")
    height = int(m.group(1))
    require(700 <= height <= 1400, f"{path} phased pipeline SVG height should support long vertical pipelines")
    require(root.find("{http://www.w3.org/2000/svg}title") is not None, f"{path} missing <title>")
    require(root.find("{http://www.w3.org/2000/svg}desc") is not None, f"{path} missing <desc>")
    require(text.count("onclick=") >= 8, f"{path} should include clickable pipeline nodes")
    require(text.count("stroke-dasharray") >= 4, f"{path} should include phase containers, side notes, or dashed guides")
    require("<mask" in text, f"{path} should include label gap mask")
    phase_rects = 0
    legend_rects = 0
    node_rects = 0
    for match in re.finditer(r"<rect\b[^>]*>", text):
        attrs = parse_float_attrs(match.group(0))
        if {"x", "y", "width", "height"}.issubset(attrs):
            check_point(path, "rect origin", attrs["x"], attrs["y"], 680, height)
            check_point(path, "rect bottom-right", attrs["x"] + attrs["width"], attrs["y"] + attrs["height"], 680, height)
            if attrs["width"] >= 500 and attrs["height"] >= 100:
                phase_rects += 1
            if 8 <= attrs["width"] <= 16 and 8 <= attrs["height"] <= 16 and attrs["y"] >= height - 160:
                legend_rects += 1
            if attrs["width"] >= 140 and 40 <= attrs["height"] <= 70:
                node_rects += 1
    require(phase_rects >= 2, f"{path} should contain multiple phase containers")
    require(node_rects >= 8, f"{path} should contain main and local pipeline nodes")
    require(legend_rects >= 3, f"{path} should contain a legend")
    ok(f"Phased pipeline SVG checks passed: {path}")


def validate_skill_markdown(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require(text.startswith("---\n"), "SKILL.md must start with YAML frontmatter")
    parts = text.split("---", 2)
    require(len(parts) == 3, "SKILL.md frontmatter must be closed")
    frontmatter = parts[1]
    require(re.search(r"^name:\s*svgflow-response\s*$", frontmatter, re.M), "SKILL.md frontmatter missing name")
    description = re.search(r"^description:\s*(.+)$", frontmatter, re.M)
    require(description is not None, "SKILL.md frontmatter missing description")
    require(description.group(1).startswith("Use when "), "SKILL.md description must start with 'Use when '")
    require("Supporting Files" in text, "SKILL.md must explain supporting files")
    require("scripts/validate_svg.py --package ." in text, "SKILL.md must include package verification command")
    ok(f"Skill metadata checks passed: {path}")


def validate_skill_json(path: Path, changelog_path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    version = data.get("version")
    require(isinstance(version, str) and re.match(r"^\d+\.\d+\.\d+$", version), f"{path} version must be semver")
    changelog = changelog_path.read_text(encoding="utf-8")
    require(f"## {version}" in changelog, f"{changelog_path} missing section for skill.json version {version}")
    ok(f"Skill package metadata checks passed: {path}")


def validate_flow_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    meta_probe = data.get("meta", {})
    if isinstance(meta_probe, dict) and meta_probe.get("diagramType") == "knowledge_map":
        validate_knowledge_map_dsl(path)
        return
    if isinstance(meta_probe, dict) and meta_probe.get("diagramType") == "architecture_map":
        validate_architecture_map_dsl(path)
        return
    if isinstance(meta_probe, dict) and meta_probe.get("diagramType") == "interactive_walkthrough":
        validate_walkthrough_dsl(path)
        return
    if isinstance(meta_probe, dict) and meta_probe.get("diagramType") == "system_loop":
        validate_system_loop_dsl(path)
        return
    if isinstance(meta_probe, dict) and meta_probe.get("diagramType") == "module_grid":
        validate_module_grid_dsl(path)
        return
    if isinstance(meta_probe, dict) and meta_probe.get("diagramType") == "agentic_pipeline":
        validate_agentic_pipeline_dsl(path)
        return
    if isinstance(meta_probe, dict) and meta_probe.get("diagramType") == "phased_pipeline":
        validate_phased_pipeline_dsl(path)
        return
    if isinstance(meta_probe, dict) and meta_probe.get("diagramType") == "infographic":
        validate_infographic_dsl(path)
        return
    require(set(["meta", "style", "nodes", "edges"]).issubset(data), f"{path} missing required top-level fields")

    meta = data["meta"]
    style = data["style"]
    nodes = data["nodes"]
    edges = data["edges"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(isinstance(style, dict), f"{path} style must be an object")
    require(isinstance(nodes, list), f"{path} nodes must be an array")
    require(isinstance(edges, list), f"{path} edges must be an array")
    require(meta.get("diagramType") == "flowchart", f"{path} diagramType must be flowchart")
    require(meta.get("direction") in {"TB", "LR"}, f"{path} direction must be TB or LR")
    require(meta.get("mode") in {"preview_svg", "raw_svg", "html_preview", "component_ready"}, f"{path} mode is invalid")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} textDirection must be ltr, rtl, or auto")
    require(style.get("maxNodes", 8) <= 8, f"{path} style.maxNodes must be <= 8")
    require(style.get("colorLimit", 3) <= 3, f"{path} style.colorLimit must be <= 3")
    require(1 <= len(nodes) <= 8, f"{path} must contain 1 to 8 nodes")

    ids: set[str] = set()
    colors: set[str] = set()
    for node in nodes:
        require(isinstance(node, dict), f"{path} node must be an object")
        node_id = node.get("id")
        require(isinstance(node_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", node_id), f"{path} invalid node id: {node_id}")
        require(node_id not in ids, f"{path} duplicate node id: {node_id}")
        ids.add(node_id)
        require(node.get("type") in {"start", "action", "decision", "end", "error"}, f"{path} invalid node type: {node.get('type')}")
        label = node.get("label")
        require(isinstance(label, str) and label.strip(), f"{path} node label is required")
        require(len(label) <= 16, f"{path} node label too long: {label}")
        if "subtitle" in node:
            require(isinstance(node["subtitle"], str) and len(node["subtitle"]) <= 12, f"{path} subtitle too long: {node['subtitle']}")
        if node.get("type") == "decision":
            require(label.endswith(("?", "؟")), f"{path} decision label must end with '?' or '؟': {label}")
        color = node.get("color")
        require(color in {"gray", "blue", "green", "amber", "coral", "purple", "teal"}, f"{path} invalid color: {color}")
        colors.add(color)

    require(any(node.get("type") == "start" for node in nodes), f"{path} must include a start node")
    require(len(colors) <= style.get("colorLimit", 3), f"{path} uses too many colors: {sorted(colors)}")

    for edge in edges:
        require(isinstance(edge, dict), f"{path} edge must be an object")
        require(edge.get("from") in ids, f"{path} edge.from references missing node: {edge.get('from')}")
        require(edge.get("to") in ids, f"{path} edge.to references missing node: {edge.get('to')}")
        if "label" in edge:
            require(isinstance(edge["label"], str) and 1 <= len(edge["label"]) <= 16, f"{path} edge label must be 1 to 16 characters: {edge['label']}")
        if "branch" in edge:
            require(edge["branch"] in {"main", "left", "right"}, f"{path} invalid branch: {edge['branch']}")
        if "route" in edge:
            require(edge["route"] in {"straight", "l-shape", "loop-left", "loop-right"}, f"{path} invalid route: {edge['route']}")

    ok(f"Flow DSL checks passed: {path}")


def validate_knowledge_map_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(set(["meta", "theme", "sections"]).issubset(data), f"{path} missing required knowledge-map fields")
    meta = data["meta"]
    theme = data["theme"]
    sections = data["sections"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(meta.get("diagramType") == "knowledge_map", f"{path} diagramType must be knowledge_map")
    require(meta.get("mode") in {"preview_svg", "html_preview", "component_ready"}, f"{path} mode is invalid")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} textDirection must be ltr, rtl, or auto")
    view_box = meta.get("viewBox", {})
    require(isinstance(view_box, dict), f"{path} viewBox must be an object")
    require(view_box.get("width") == 680, f"{path} viewBox.width must be 680")
    require(isinstance(view_box.get("height"), int) and 320 <= view_box["height"] <= 1200, f"{path} viewBox.height is invalid")

    require(isinstance(theme, dict), f"{path} theme must be an object")
    palette = theme.get("palette")
    require(isinstance(palette, list) and 4 <= len(palette) <= 12, f"{path} theme.palette must contain 4 to 12 colors")
    palette_ids: set[str] = set()
    for entry in palette:
        require(isinstance(entry, dict), f"{path} palette entry must be an object")
        palette_id = entry.get("id")
        require(isinstance(palette_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", palette_id), f"{path} invalid palette id: {palette_id}")
        require(palette_id not in palette_ids, f"{path} duplicate palette id: {palette_id}")
        palette_ids.add(palette_id)
        for key in ["fill", "stroke", "title", "text"]:
            require(isinstance(entry.get(key), str) and re.match(r"^#[0-9a-fA-F]{6}$", entry[key]), f"{path} invalid palette color {palette_id}.{key}")

    require(isinstance(sections, list) and 3 <= len(sections) <= 8, f"{path} sections must contain 3 to 8 entries")
    section_types: set[str] = set()
    interactive_items = 0
    chapter_items = 0
    summary_items = 0
    for section in sections:
        require(isinstance(section, dict), f"{path} section must be an object")
        section_type = section.get("type")
        require(section_type in {"header", "chapter_grid", "summary_grid", "footer"}, f"{path} invalid section type: {section_type}")
        section_types.add(section_type)
        items = section.get("items")
        require(isinstance(items, list) and items, f"{path} section items must be non-empty")
        for item in items:
            require(isinstance(item, dict), f"{path} item must be an object")
            require(isinstance(item.get("id"), str) and re.match(r"^[a-z][a-z0-9_-]*$", item["id"]), f"{path} invalid item id: {item.get('id')}")
            require(isinstance(item.get("title"), str) and item["title"].strip(), f"{path} item title is required")
            if "palette" in item:
                require(item["palette"] in palette_ids, f"{path} item references missing palette: {item['palette']}")
            if "actionPrompt" in item:
                require(isinstance(item["actionPrompt"], str) and item["actionPrompt"].strip(), f"{path} actionPrompt must be non-empty")
                interactive_items += 1
        if section_type == "chapter_grid":
            chapter_items += len(items)
        if section_type == "summary_grid":
            summary_items += len(items)

    require({"header", "chapter_grid", "summary_grid", "footer"}.issubset(section_types), f"{path} missing required knowledge-map section types")
    require(chapter_items >= 6, f"{path} chapter_grid should contain at least 6 items")
    require(summary_items >= 3, f"{path} summary_grid should contain at least 3 items")
    require(interactive_items >= chapter_items, f"{path} every chapter should be interactive")
    ok(f"Knowledge map DSL checks passed: {path}")


def read_palette_ids(path: Path, theme: object) -> set[str]:
    require(isinstance(theme, dict), f"{path} theme must be an object")
    palette = theme.get("palette")
    require(isinstance(palette, list) and 4 <= len(palette) <= 12, f"{path} theme.palette must contain 4 to 12 colors")
    palette_ids: set[str] = set()
    for entry in palette:
        require(isinstance(entry, dict), f"{path} palette entry must be an object")
        palette_id = entry.get("id")
        require(isinstance(palette_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", palette_id), f"{path} invalid palette id: {palette_id}")
        require(palette_id not in palette_ids, f"{path} duplicate palette id: {palette_id}")
        palette_ids.add(palette_id)
        for key in ["fill", "stroke", "title", "text"]:
            require(isinstance(entry.get(key), str) and re.match(r"^#[0-9a-fA-F]{6}$", entry[key]), f"{path} invalid palette color {palette_id}.{key}")
    return palette_ids


def validate_architecture_map_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(set(["meta", "theme", "layers"]).issubset(data), f"{path} missing required architecture-map fields")
    meta = data["meta"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(meta.get("diagramType") == "architecture_map", f"{path} diagramType must be architecture_map")
    require(meta.get("mode") in {"preview_svg", "html_preview", "component_ready"}, f"{path} mode is invalid")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} textDirection must be ltr, rtl, or auto")
    view_box = meta.get("viewBox", {})
    require(isinstance(view_box, dict), f"{path} viewBox must be an object")
    require(view_box.get("width") == 680, f"{path} viewBox.width must be 680")
    require(isinstance(view_box.get("height"), int) and 480 <= view_box["height"] <= 1200, f"{path} viewBox.height is invalid")

    palette_ids = read_palette_ids(path, data["theme"])
    layers = data["layers"]
    require(isinstance(layers, list) and 3 <= len(layers) <= 8, f"{path} layers must contain 3 to 8 entries")
    interactive_items = 0
    total_items = 0
    storage_zones = 0
    for layer in layers:
        require(isinstance(layer, dict), f"{path} layer must be an object")
        require(isinstance(layer.get("id"), str) and re.match(r"^[a-z][a-z0-9_-]*$", layer["id"]), f"{path} invalid layer id: {layer.get('id')}")
        require(isinstance(layer.get("title"), str) and layer["title"].strip(), f"{path} layer title is required")
        require(layer.get("layout") in {"full", "chip_row", "zone_grid"}, f"{path} invalid layer layout: {layer.get('layout')}")
        if "palette" in layer:
            require(layer["palette"] in palette_ids, f"{path} layer references missing palette: {layer['palette']}")
        items = layer.get("items")
        require(isinstance(items, list) and items, f"{path} layer items must be non-empty")
        total_items += len(items)
        if layer.get("layout") == "zone_grid":
            storage_zones += len(items)
        for item in items:
            require(isinstance(item, dict), f"{path} item must be an object")
            require(isinstance(item.get("id"), str) and re.match(r"^[a-z][a-z0-9_-]*$", item["id"]), f"{path} invalid item id: {item.get('id')}")
            require(isinstance(item.get("title"), str) and item["title"].strip(), f"{path} item title is required")
            if "palette" in item:
                require(item["palette"] in palette_ids, f"{path} item references missing palette: {item['palette']}")
            if "actionPrompt" in item:
                require(isinstance(item["actionPrompt"], str) and item["actionPrompt"].strip(), f"{path} actionPrompt must be non-empty")
                interactive_items += 1

    require(total_items >= 12, f"{path} architecture maps should contain at least 12 items")
    require(storage_zones >= 3, f"{path} architecture maps should support nested storage zones")
    require(interactive_items >= 10, f"{path} architecture maps should include rich clickable details")
    ok(f"Architecture map DSL checks passed: {path}")


def validate_walkthrough_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(set(["meta", "theme", "steps"]).issubset(data), f"{path} missing required walkthrough fields")
    meta = data["meta"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(meta.get("diagramType") == "interactive_walkthrough", f"{path} diagramType must be interactive_walkthrough")
    require(meta.get("mode") == "html_preview", f"{path} walkthrough mode must be html_preview")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} textDirection must be ltr, rtl, or auto")
    read_palette_ids(path, data["theme"])
    steps = data["steps"]
    require(isinstance(steps, list) and 2 <= len(steps) <= 8, f"{path} steps must contain 2 to 8 entries")
    animated_steps = 0
    for index, step in enumerate(steps):
        require(isinstance(step, dict), f"{path} step must be an object")
        require(isinstance(step.get("id"), str) and re.match(r"^s\d+$", step["id"]), f"{path} invalid step id: {step.get('id')}")
        require(isinstance(step.get("title"), str) and step["title"].strip(), f"{path} step title is required")
        require(isinstance(step.get("label"), str) and step["label"].strip(), f"{path} step label is required")
        require(isinstance(step.get("nodes"), list) and len(step["nodes"]) >= 2, f"{path} step {index} needs nodes")
        require(isinstance(step.get("connectors"), list), f"{path} step {index} connectors must be an array")
        if step.get("animation") in {"pulse", "travel", "pulse_travel"}:
            animated_steps += 1
    require(animated_steps >= 2, f"{path} walkthrough should exercise pulse/travel animation states")
    ok(f"Walkthrough DSL checks passed: {path}")


def validate_system_loop_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(set(["meta", "theme", "actors", "signals"]).issubset(data), f"{path} missing required system-loop fields")
    meta = data["meta"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(meta.get("diagramType") == "system_loop", f"{path} diagramType must be system_loop")
    require(meta.get("mode") in {"preview_svg", "html_preview", "component_ready"}, f"{path} mode is invalid")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} textDirection must be ltr, rtl, or auto")
    view_box = meta.get("viewBox", {})
    require(isinstance(view_box, dict), f"{path} viewBox must be an object")
    require(view_box.get("width") == 680, f"{path} viewBox.width must be 680")
    require(isinstance(view_box.get("height"), int) and 300 <= view_box["height"] <= 620, f"{path} viewBox.height is invalid")
    palette_ids = read_palette_ids(path, data["theme"])

    actors = data["actors"]
    signals = data["signals"]
    require(isinstance(actors, list) and 2 <= len(actors) <= 5, f"{path} actors must contain 2 to 5 entries")
    require(isinstance(signals, list) and len(signals) >= 3, f"{path} signals must contain at least 3 entries")
    actor_ids: set[str] = set()
    roles: set[str] = set()
    interactive_actors = 0
    for actor in actors:
        require(isinstance(actor, dict), f"{path} actor must be an object")
        actor_id = actor.get("id")
        require(isinstance(actor_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", actor_id), f"{path} invalid actor id: {actor_id}")
        require(actor_id not in actor_ids, f"{path} duplicate actor id: {actor_id}")
        actor_ids.add(actor_id)
        require(isinstance(actor.get("title"), str) and actor["title"].strip(), f"{path} actor title is required")
        require(actor.get("role") in {"agent", "environment", "device", "service", "human", "system"}, f"{path} invalid actor role: {actor.get('role')}")
        roles.add(actor["role"])
        require(actor.get("palette") in palette_ids, f"{path} actor references missing palette: {actor.get('palette')}")
        if "actionPrompt" in actor:
            require(isinstance(actor["actionPrompt"], str) and actor["actionPrompt"].strip(), f"{path} actionPrompt must be non-empty")
            interactive_actors += 1

    signal_pairs: set[tuple[str, str]] = set()
    dashed_seen = False
    for signal in signals:
        require(isinstance(signal, dict), f"{path} signal must be an object")
        require(signal.get("from") in actor_ids, f"{path} signal.from references missing actor: {signal.get('from')}")
        require(signal.get("to") in actor_ids, f"{path} signal.to references missing actor: {signal.get('to')}")
        require(isinstance(signal.get("label"), str) and signal["label"].strip(), f"{path} signal label is required")
        require(signal.get("kind", "other") in {"action", "state", "reward", "deploy", "feedback", "guarded", "other"}, f"{path} invalid signal kind: {signal.get('kind')}")
        signal_pairs.add((signal["from"], signal["to"]))
        dashed_seen = dashed_seen or bool(signal.get("dashed")) or signal.get("route") == "dashed"

    has_return_pair = any((to_actor, from_actor) in signal_pairs for from_actor, to_actor in signal_pairs)
    require({"agent", "environment"}.issubset(roles) or len(actors) >= 3, f"{path} system loops need agent/environment roles or a three-actor loop")
    require(has_return_pair, f"{path} system loops should contain at least one bidirectional exchange")
    require(dashed_seen, f"{path} system loops should support dashed secondary feedback/deployment paths")
    require(interactive_actors >= 2, f"{path} system loops should include clickable actors")
    ok(f"System loop DSL checks passed: {path}")


def validate_module_grid_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(set(["meta", "modules"]).issubset(data), f"{path} missing required module-grid fields")
    meta = data["meta"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(meta.get("diagramType") == "module_grid", f"{path} diagramType must be module_grid")
    require(meta.get("mode") == "html_preview", f"{path} module_grid mode must be html_preview")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} textDirection must be ltr, rtl, or auto")
    modules = data["modules"]
    require(isinstance(modules, list) and 2 <= len(modules) <= 8, f"{path} modules must contain 2 to 8 entries")
    module_ids: set[str] = set()
    tones: set[str] = set()
    for module in modules:
        require(isinstance(module, dict), f"{path} module must be an object")
        module_id = module.get("id")
        require(isinstance(module_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", module_id), f"{path} invalid module id: {module_id}")
        require(module_id not in module_ids, f"{path} duplicate module id: {module_id}")
        module_ids.add(module_id)
        require(isinstance(module.get("title"), str) and module["title"].strip(), f"{path} module title is required")
        require(isinstance(module.get("subtitle"), str) and module["subtitle"].strip(), f"{path} module subtitle is required")
        items = module.get("items")
        require(isinstance(items, list) and 3 <= len(items) <= 8, f"{path} module items must contain 3 to 8 entries")
        for item in items:
            require(isinstance(item, dict), f"{path} item must be an object")
            require(isinstance(item.get("label"), str) and item["label"].strip(), f"{path} item label is required")
            require(item.get("tone") in {"info", "warn", "ok", "neutral"}, f"{path} invalid item tone: {item.get('tone')}")
            require(isinstance(item.get("text"), str) and item["text"].strip(), f"{path} item text is required")
            tones.add(item["tone"])
        action = module.get("action")
        require(isinstance(action, dict), f"{path} module action is required")
        require(isinstance(action.get("label"), str) and action["label"].strip(), f"{path} action label is required")
        require(isinstance(action.get("prompt"), str) and action["prompt"].strip(), f"{path} action prompt is required")
    require({"info", "warn", "ok", "neutral"}.issubset(tones), f"{path} should cover all module label tones")
    ok(f"Module grid DSL checks passed: {path}")


def validate_agentic_pipeline_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(set(["meta", "entry", "orchestrator", "workers", "synthesizer", "output"]).issubset(data), f"{path} missing required agentic-pipeline fields")
    meta = data["meta"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(meta.get("diagramType") == "agentic_pipeline", f"{path} diagramType must be agentic_pipeline")
    require(meta.get("mode") in {"preview_svg", "html_preview", "component_ready"}, f"{path} mode is invalid")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} textDirection must be ltr, rtl, or auto")
    view_box = meta.get("viewBox", {})
    require(isinstance(view_box, dict), f"{path} viewBox must be an object")
    require(view_box.get("width") in {680, 690}, f"{path} viewBox.width must be 680 or 690")
    require(isinstance(view_box.get("height"), int) and 420 <= view_box["height"] <= 900, f"{path} viewBox.height is invalid")

    def validate_pipeline_node(node: object, label: str) -> str:
        require(isinstance(node, dict), f"{path} {label} must be an object")
        node_id = node.get("id")
        require(isinstance(node_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", node_id), f"{path} invalid {label} id: {node_id}")
        require(isinstance(node.get("title"), str) and node["title"].strip(), f"{path} {label} title is required")
        if "actionPrompt" in node:
            require(isinstance(node["actionPrompt"], str) and node["actionPrompt"].strip(), f"{path} {label} actionPrompt must be non-empty")
        return node_id

    ids: set[str] = set()
    for key in ["entry", "orchestrator", "synthesizer", "output"]:
        ids.add(validate_pipeline_node(data[key], key))

    workers = data["workers"]
    require(isinstance(workers, list) and 2 <= len(workers) <= 6, f"{path} workers must contain 2 to 6 entries")
    for worker in workers:
        require(isinstance(worker, dict), f"{path} worker must be an object")
        worker_id = worker.get("id")
        require(isinstance(worker_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", worker_id), f"{path} invalid worker id: {worker_id}")
        require(worker_id not in ids, f"{path} duplicate worker id: {worker_id}")
        ids.add(worker_id)
        agent_id = validate_pipeline_node(worker.get("agent"), f"{worker_id}.agent")
        source_id = validate_pipeline_node(worker.get("source"), f"{worker_id}.source")
        require(agent_id not in ids and source_id not in ids, f"{path} duplicate worker node id")
        ids.add(agent_id)
        ids.add(source_id)

    loops = data.get("loops", [])
    require(isinstance(loops, list), f"{path} loops must be an array")
    dashed_loop_seen = False
    for loop in loops:
        require(isinstance(loop, dict), f"{path} loop must be an object")
        require(loop.get("from") in ids, f"{path} loop.from references missing node: {loop.get('from')}")
        require(loop.get("to") in ids, f"{path} loop.to references missing node: {loop.get('to')}")
        require(isinstance(loop.get("label"), str) and loop["label"].strip(), f"{path} loop label is required")
        dashed_loop_seen = dashed_loop_seen or bool(loop.get("dashed"))

    require(dashed_loop_seen, f"{path} agentic pipelines should include a dashed replanning or retry loop")
    ok(f"Agentic pipeline DSL checks passed: {path}")


def validate_phased_pipeline_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(set(["meta", "spine", "phases"]).issubset(data), f"{path} missing required phased-pipeline fields")
    meta = data["meta"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(meta.get("diagramType") == "phased_pipeline", f"{path} diagramType must be phased_pipeline")
    require(meta.get("mode") in {"preview_svg", "html_preview", "component_ready"}, f"{path} mode is invalid")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} textDirection must be ltr, rtl, or auto")
    view_box = meta.get("viewBox", {})
    require(isinstance(view_box, dict), f"{path} viewBox must be an object")
    require(view_box.get("width") == 680, f"{path} viewBox.width must be 680")
    require(isinstance(view_box.get("height"), int) and 700 <= view_box["height"] <= 1400, f"{path} viewBox.height is invalid")

    def validate_phase_node(node: object, label: str) -> str:
        require(isinstance(node, dict), f"{path} {label} must be an object")
        node_id = node.get("id")
        require(isinstance(node_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", node_id), f"{path} invalid {label} id: {node_id}")
        require(isinstance(node.get("title"), str) and node["title"].strip(), f"{path} {label} title is required")
        if "actionPrompt" in node:
            require(isinstance(node["actionPrompt"], str) and node["actionPrompt"].strip(), f"{path} {label} actionPrompt must be non-empty")
        return node_id

    ids: set[str] = set()
    spine = data["spine"]
    require(isinstance(spine, list) and 3 <= len(spine) <= 12, f"{path} spine must contain 3 to 12 entries")
    for index, node in enumerate(spine):
        node_id = validate_phase_node(node, f"spine[{index}]")
        require(node_id not in ids, f"{path} duplicate node id: {node_id}")
        ids.add(node_id)

    phases = data["phases"]
    require(isinstance(phases, list) and 2 <= len(phases) <= 8, f"{path} phases must contain 2 to 8 entries")
    local_flow_count = 0
    for phase in phases:
        require(isinstance(phase, dict), f"{path} phase must be an object")
        phase_id = phase.get("id")
        require(isinstance(phase_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", phase_id), f"{path} invalid phase id: {phase_id}")
        require(isinstance(phase.get("title"), str) and phase["title"].strip(), f"{path} phase title is required")
        nodes = phase.get("nodes")
        require(isinstance(nodes, list) and nodes, f"{path} phase nodes must be non-empty")
        phase_node_ids: set[str] = set()
        for index, node in enumerate(nodes):
            node_id = validate_phase_node(node, f"{phase_id}.nodes[{index}]")
            require(node_id not in ids, f"{path} duplicate node id: {node_id}")
            ids.add(node_id)
            phase_node_ids.add(node_id)
        flows = phase.get("localFlows", [])
        require(isinstance(flows, list), f"{path} localFlows must be an array")
        for flow in flows:
            require(isinstance(flow, dict), f"{path} localFlow must be an object")
            require(flow.get("from") in phase_node_ids, f"{path} localFlow.from references missing phase node: {flow.get('from')}")
            require(flow.get("to") in phase_node_ids, f"{path} localFlow.to references missing phase node: {flow.get('to')}")
            local_flow_count += 1

    legend = data.get("legend", [])
    require(isinstance(legend, list), f"{path} legend must be an array")
    require(len(legend) >= 3, f"{path} phased pipelines should include a legend")
    require(local_flow_count >= 2, f"{path} phased pipelines should include local flows inside phases")
    ok(f"Phased pipeline DSL checks passed: {path}")


def validate_infographic_dsl(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    require(set(["meta", "canvas", "content", "layout"]).issubset(data), f"{path} missing required infographic fields")

    meta = data["meta"]
    require(isinstance(meta, dict), f"{path} meta must be an object")
    require(meta.get("diagramType") == "infographic", f"{path} diagramType must be infographic")
    require(isinstance(meta.get("title"), str) and meta["title"].strip(), f"{path} meta.title is required")
    require(isinstance(meta.get("description"), str) and meta["description"].strip(), f"{path} meta.description is required")
    require(meta.get("mode") in {"preview_svg", "raw_svg", "html_preview", "component_ready"}, f"{path} meta.mode is invalid")
    require(isinstance(meta.get("locale"), str) and re.match(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$", meta["locale"]), f"{path} meta.locale is invalid")
    require(meta.get("textDirection") in {"ltr", "rtl", "auto"}, f"{path} meta.textDirection is invalid")

    canvas = data["canvas"]
    require(isinstance(canvas, dict), f"{path} canvas must be an object")
    require(canvas.get("width") in {680, 690}, f"{path} canvas.width must be 680 or 690")
    require(isinstance(canvas.get("height"), int) and 240 <= canvas["height"] <= 1600, f"{path} canvas.height is invalid")

    content = data["content"]
    require(isinstance(content, dict), f"{path} content must be an object")
    nodes = content.get("nodes")
    edges = content.get("edges")
    groups = content.get("groups", [])
    legends = content.get("legends", [])
    labels = content.get("labels", [])
    steps = content.get("steps", [])
    require(isinstance(nodes, list) and 1 <= len(nodes) <= 40, f"{path} content.nodes must contain 1 to 40 nodes")
    require(isinstance(edges, list), f"{path} content.edges must be an array")
    require(isinstance(groups, list), f"{path} content.groups must be an array when present")
    require(isinstance(legends, list), f"{path} content.legends must be an array when present")
    require(isinstance(labels, list), f"{path} content.labels must be an array when present")
    require(isinstance(steps, list), f"{path} content.steps must be an array when present")

    node_ids: set[str] = set()
    for node in nodes:
        require(isinstance(node, dict), f"{path} node must be an object")
        node_id = node.get("id")
        require(isinstance(node_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", node_id), f"{path} node id is invalid")
        require(node_id not in node_ids, f"{path} duplicate node id: {node_id}")
        node_ids.add(node_id)
        require(isinstance(node.get("title"), str) and node["title"].strip(), f"{path} node title is required")
        if "parent" in node:
            require(isinstance(node["parent"], str), f"{path} node parent must be a string")
        if "items" in node:
            require(isinstance(node["items"], list), f"{path} node items must be an array")

    for group in groups:
        require(isinstance(group, dict), f"{path} group must be an object")
        members = group.get("members")
        require(isinstance(members, list) and members, f"{path} group members are required")
        for member in members:
            require(member in node_ids, f"{path} group references unknown node: {member}")

    for edge in edges:
        require(isinstance(edge, dict), f"{path} edge must be an object")
        require(edge.get("from") in node_ids, f"{path} edge.from references unknown node: {edge.get('from')}")
        require(edge.get("to") in node_ids, f"{path} edge.to references unknown node: {edge.get('to')}")
        if "label" in edge:
            require(isinstance(edge["label"], str) and edge["label"].strip(), f"{path} edge label must be non-empty")

    for step in steps:
        require(isinstance(step, dict), f"{path} step must be an object")
        visible_nodes = step.get("visibleNodes")
        require(isinstance(visible_nodes, list) and visible_nodes, f"{path} step visibleNodes are required")
        for node_id in visible_nodes:
            require(node_id in node_ids, f"{path} step references unknown node: {node_id}")

    layout = data["layout"]
    require(isinstance(layout, dict), f"{path} layout must be an object")
    allowed_intents = {"linear", "layered", "loop", "matrix", "hub_spoke", "timeline", "swimlane", "comparison", "hierarchy", "dashboard", "freeform"}
    require(layout.get("intent") in allowed_intents, f"{path} layout.intent is invalid")
    if "nodeLimit" in layout:
        require(isinstance(layout["nodeLimit"], int) and 1 <= layout["nodeLimit"] <= 40, f"{path} layout.nodeLimit is invalid")

    interactions = data.get("interactions", [])
    require(isinstance(interactions, list), f"{path} interactions must be an array when present")
    for interaction in interactions:
        require(isinstance(interaction, dict), f"{path} interaction must be an object")
        require(interaction.get("target") in node_ids, f"{path} interaction target references unknown node: {interaction.get('target')}")
        require(interaction.get("action") in {"sendPrompt", "step", "highlight", "toggle"}, f"{path} interaction action is invalid")
        if interaction.get("action") == "sendPrompt":
            require(isinstance(interaction.get("prompt"), str) and interaction["prompt"].strip(), f"{path} sendPrompt interaction requires prompt")

    require(edges or groups or legends or labels or steps or interactions, f"{path} infographic should include at least one structural enhancement beyond nodes")
    ok(f"Infographic DSL checks passed: {path}")


def collect_flow_dsl_coverage(path: Path) -> dict[str, set[str]]:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    meta = data.get("meta", {})
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    coverage = {
        "directions": set(),
        "modes": set(),
        "node_types": set(),
        "branches": set(),
        "routes": set(),
        "colors": set(),
        "locales": set(),
        "text_directions": set(),
    }
    if isinstance(meta, dict):
        if isinstance(meta.get("direction"), str):
            coverage["directions"].add(meta["direction"])
        if isinstance(meta.get("mode"), str):
            coverage["modes"].add(meta["mode"])
        if isinstance(meta.get("locale"), str):
            coverage["locales"].add(meta["locale"])
        if isinstance(meta.get("textDirection"), str):
            coverage["text_directions"].add(meta["textDirection"])
    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict):
                if isinstance(node.get("type"), str):
                    coverage["node_types"].add(node["type"])
                if isinstance(node.get("color"), str):
                    coverage["colors"].add(node["color"])
    if isinstance(edges, list):
        for edge in edges:
            if isinstance(edge, dict):
                if isinstance(edge.get("branch"), str):
                    coverage["branches"].add(edge["branch"])
                if isinstance(edge.get("route"), str):
                    coverage["routes"].add(edge["route"])
                elif "from" in edge and "to" in edge:
                    coverage["routes"].add("straight")
    return coverage


def validate_coverage(root: Path) -> None:
    example_paths = sorted((root / "examples").glob("*.dsl.json"))
    require(example_paths, "No DSL examples found for coverage validation")
    aggregate = {
        "directions": set(),
        "modes": set(),
        "node_types": set(),
        "branches": set(),
        "routes": set(),
        "colors": set(),
        "locales": set(),
        "text_directions": set(),
    }
    for path in example_paths:
        validate_flow_dsl(path)
        coverage = collect_flow_dsl_coverage(path)
        for key, values in coverage.items():
            aggregate[key].update(values)

    required = {
        "directions": {"TB", "LR"},
        "modes": {"preview_svg", "raw_svg", "html_preview", "component_ready"},
        "node_types": {"start", "action", "decision", "end", "error"},
        "branches": {"main", "left", "right"},
        "routes": {"straight", "l-shape", "loop-left", "loop-right"},
        "colors": {"gray", "blue", "green", "amber", "coral", "purple", "teal"},
        "text_directions": {"ltr", "rtl"},
    }
    for key, expected in required.items():
        missing = sorted(expected - aggregate[key])
        require(not missing, f"Coverage missing {key}: {missing}")

    ok("Coverage checks passed")


def validate_i18n(root: Path) -> None:
    example_paths = sorted((root / "examples").glob("*.dsl.json"))
    require(example_paths, "No DSL examples found for i18n validation")
    locales: set[str] = set()
    directions: set[str] = set()
    latin_seen = False
    cjk_seen = False
    rtl_seen = False
    for path in example_paths:
        validate_flow_dsl(path)
        data = read_json(path)
        require(isinstance(data, dict), f"{path} must contain a JSON object")
        meta = data.get("meta", {})
        if isinstance(meta, dict):
            locales.add(meta.get("locale", ""))
            directions.add(meta.get("textDirection", ""))
        text = json.dumps(data, ensure_ascii=False)
        latin_seen = latin_seen or bool(re.search(r"[A-Za-z]", text))
        cjk_seen = cjk_seen or bool(re.search(r"[\u4e00-\u9fff]", text))
        rtl_seen = rtl_seen or bool(re.search(r"[\u0590-\u05ff\u0600-\u06ff]", text))

    require(any(locale.startswith("en") for locale in locales), "i18n coverage missing English locale")
    require(any(locale.startswith("zh") for locale in locales), "i18n coverage missing Chinese locale")
    require(any(locale.startswith(("ar", "he", "fa", "ur")) for locale in locales), "i18n coverage missing RTL locale")
    require("ltr" in directions, "i18n coverage missing ltr textDirection")
    require("rtl" in directions, "i18n coverage missing rtl textDirection")
    require(latin_seen, "i18n coverage missing Latin text")
    require(cjk_seen, "i18n coverage missing CJK text")
    require(rtl_seen, "i18n coverage missing RTL script text")

    for svg_path in sorted((root / "examples").glob("*.output.svg")):
        validate_svg(svg_path)

    ok("I18n checks passed")


def validate_locale_signals(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    for locale in ["en", "zh-CN", "ar"]:
        section = data.get(locale)
        require(isinstance(section, dict), f"{path} missing locale signals: {locale}")
        for key in ["sequence", "decision", "retry", "edgeLabels"]:
            values = section.get(key)
            require(isinstance(values, list) and values, f"{path} missing {locale}.{key}")
    ok(f"Locale signal checks passed: {path}")


def validate_test_cases(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict) and isinstance(data.get("cases"), list), f"{path} must contain cases[]")
    require(len(data["cases"]) >= 5, f"{path} should cover at least 5 cases")
    seen: set[str] = set()
    for case in data["cases"]:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and case_id, f"{path} case id is required")
        require(case_id not in seen, f"{path} duplicate case id: {case_id}")
        seen.add(case_id)
        require(isinstance(case.get("input"), str) and case["input"].strip(), f"{case_id} input is required")
        require(case.get("input_type") == "assistant_response", f"{case_id} input_type must be assistant_response")
        expected = case.get("expected")
        require(isinstance(expected, dict), f"{case_id} expected is required")
        diagram_type = expected.get("diagramType")
        require(diagram_type in {"flowchart", "knowledge_map", "architecture_map", "interactive_walkthrough", "system_loop", "module_grid", "agentic_pipeline", "phased_pipeline", "infographic"}, f"{case_id} expected diagramType is invalid")
        if diagram_type == "flowchart":
            require(expected.get("maxNodes") == 8, f"{case_id} expected maxNodes must be 8")
            require(isinstance(expected.get("must_include_nodes"), list), f"{case_id} must_include_nodes is required")
            require(isinstance(expected.get("must_include_edge_labels"), list), f"{case_id} must_include_edge_labels is required")
        elif diagram_type == "knowledge_map":
            require(isinstance(expected.get("must_include_sections"), list), f"{case_id} must_include_sections is required")
            require(isinstance(expected.get("minInteractiveItems"), int), f"{case_id} minInteractiveItems is required")
        elif diagram_type == "architecture_map":
            require(isinstance(expected.get("must_include_layers"), list), f"{case_id} must_include_layers is required")
            require(isinstance(expected.get("minInteractiveItems"), int), f"{case_id} minInteractiveItems is required")
        elif diagram_type == "interactive_walkthrough":
            require(isinstance(expected.get("minSteps"), int), f"{case_id} minSteps is required")
            require(expected.get("requiresControls") is True, f"{case_id} requiresControls must be true")
        elif diagram_type == "system_loop":
            require(isinstance(expected.get("must_include_roles"), list), f"{case_id} must_include_roles is required")
            require(isinstance(expected.get("minSignals"), int), f"{case_id} minSignals is required")
            require(expected.get("requiresBidirectionalExchange") is True, f"{case_id} requiresBidirectionalExchange must be true")
        elif diagram_type == "module_grid":
            require(isinstance(expected.get("minModules"), int), f"{case_id} minModules is required")
            require(isinstance(expected.get("minItemsPerModule"), int), f"{case_id} minItemsPerModule is required")
            require(expected.get("requiresSemanticTones") is True, f"{case_id} requiresSemanticTones must be true")
            require(expected.get("requiresCtaButtons") is True, f"{case_id} requiresCtaButtons must be true")
        elif diagram_type == "agentic_pipeline":
            require(isinstance(expected.get("minWorkers"), int), f"{case_id} minWorkers is required")
            require(expected.get("requiresWorkerSourcePairs") is True, f"{case_id} requiresWorkerSourcePairs must be true")
            require(expected.get("requiresFanOut") is True, f"{case_id} requiresFanOut must be true")
            require(expected.get("requiresFanIn") is True, f"{case_id} requiresFanIn must be true")
        elif diagram_type == "phased_pipeline":
            require(isinstance(expected.get("minSpineNodes"), int), f"{case_id} minSpineNodes is required")
            require(isinstance(expected.get("minPhases"), int), f"{case_id} minPhases is required")
            require(expected.get("requiresLocalFlows") is True, f"{case_id} requiresLocalFlows must be true")
            require(expected.get("requiresLegend") is True, f"{case_id} requiresLegend must be true")
        elif diagram_type == "infographic":
            require(isinstance(expected.get("layoutIntents"), list), f"{case_id} layoutIntents is required")
            require(set(expected["layoutIntents"]) == {"linear", "layered", "loop", "matrix", "hub_spoke", "timeline", "swimlane", "comparison", "hierarchy", "dashboard", "freeform"}, f"{case_id} layoutIntents must cover the v2 intent set")
            require(expected.get("requiresNodes") is True, f"{case_id} requiresNodes must be true")
            require(expected.get("requiresEdges") is True, f"{case_id} requiresEdges must be true")
            require(expected.get("supportsGroups") is True, f"{case_id} supportsGroups must be true")
            require(expected.get("supportsInteractions") is True, f"{case_id} supportsInteractions must be true")
    ok(f"Test case checks passed: {path}")


def detect_input_quality_signals(text: str) -> dict[str, object]:
    relationship_patterns = [
        r"\b(after|then|if|when|while|because|but|and|or|to|from|into|through|receives?|sends?|writes?|publishes?|validates?|creates?|notifies?|summariz(?:e|es))\b",
        r"[\u4e00-\u9fff]*(\u63a5\u6536|\u6821\u9a8c|\u521b\u5efa|\u6210\u529f|\u5931\u8d25|\u901a\u77e5|\u53d6\u6d88|\u91cd\u8bd5|\u540e|\u65f6)",
        r"(ثم|إذا|عندما|يرسل|يتحقق|يعرض|ينجح|يفشل|يطلب)",
    ]
    entity_like = re.findall(r"\b[A-Z]?[a-z][A-Za-z0-9_-]{2,}\b", text)
    cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    arabic_terms = re.findall(r"[\u0600-\u06ff]{2,}", text)
    relationships = 0
    for pattern in relationship_patterns:
        relationships += len(re.findall(pattern, text, re.I))
    comparison_terms = len(re.findall(r"\b(cost|speed|risk|fit|tradeoff|compare|comparison|cheap|quick|maintenance|extensibility)\b", text, re.I))
    process_terms = len(re.findall(r"\b(after|then|if|when|receives?|sends?|writes?|validates?|creates?|publishes?)\b", text, re.I))
    process_terms += len(re.findall(r"(\u63a5\u6536|\u6821\u9a8c|\u521b\u5efa|\u6210\u529f|\u5931\u8d25|\u901a\u77e5|\u53d6\u6d88|\u91cd\u8bd5|ثم|إذا|يرسل|يتحقق)", text))
    infographic_terms = len(re.findall(r"\b(metric|metrics|kpi|uptime|latency|alert|incident|hierarchy|organization|org|team|lead|owns|ownership|responsibility|escalation|lane|lanes|workflow|customer|support|engineering|operations|handoff|timeline|roadmap|phase|milestone|layer|architecture|dashboard|snapshot|cluster|clusters|concept|principle|principles|activation|collaboration|monetization|retention|evidence|signal|signals|risk|risks|recommendation|recommendations|confidence|ownership|sequential|prioritize|prioritizes|impact|effort|reliability|observes|fixes|mitigation|mitigations|health|lessons|feedback)\b", text, re.I))
    entity_count = len(set(entity_like)) + len(set(cjk_terms)) + len(set(arabic_terms))
    locale = "en-US"
    direction = "ltr"
    if re.search(r"[\u0600-\u06ff]", text):
        locale = "ar"
        direction = "rtl"
    elif re.search(r"[\u4e00-\u9fff]", text):
        locale = "zh-CN"
    if entity_count < 2 and relationships < 1:
        decision = "reject"
    elif comparison_terms >= 3 and process_terms < 2 and entity_count >= 3:
        decision = "overview"
    elif infographic_terms >= 3 and entity_count >= 3:
        decision = "visualize"
    elif process_terms >= 2 or relationships >= 3:
        decision = "visualize"
    else:
        decision = "reject"
    return {
        "decision": decision,
        "entities": entity_count,
        "relationships": relationships,
        "locale": locale,
        "textDirection": direction,
    }


def validate_input_quality_cases(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 5, f"{path} should include at least 5 input quality cases")
    seen_ids: set[str] = set()
    seen_decisions: set[str] = set()
    seen_locales: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        require(case.get("inputType") == "assistant_response", f"{path} {case_id} inputType must be assistant_response")
        text = case.get("input")
        require(isinstance(text, str) and text.strip(), f"{path} {case_id} input is required")
        expected_decision = case.get("expectedDecision")
        require(expected_decision in {"visualize", "overview", "reject"}, f"{path} {case_id} expectedDecision is invalid")
        require(isinstance(case.get("expectedReason"), str) and case["expectedReason"].strip(), f"{path} {case_id} expectedReason is required")
        signals = detect_input_quality_signals(text)
        require(signals["decision"] == expected_decision, f"{path} {case_id} decision mismatch: {signals['decision']} != {expected_decision}")
        seen_decisions.add(str(expected_decision))
        minimum = case.get("expectedMinimumSignals")
        require(isinstance(minimum, dict), f"{path} {case_id} expectedMinimumSignals is required")
        for key in ["entities", "relationships"]:
            expected_minimum = minimum.get(key)
            require(isinstance(expected_minimum, int), f"{path} {case_id} expectedMinimumSignals.{key} must be an integer")
            require(int(signals[key]) >= expected_minimum, f"{path} {case_id} {key} too low: {signals[key]} < {expected_minimum}")
        expected_locale = case.get("expectedLocale")
        if isinstance(expected_locale, str):
            require(signals["locale"] == expected_locale, f"{path} {case_id} locale mismatch: {signals['locale']} != {expected_locale}")
            seen_locales.add(expected_locale)
        expected_direction = case.get("expectedTextDirection")
        if isinstance(expected_direction, str):
            require(signals["textDirection"] == expected_direction, f"{path} {case_id} textDirection mismatch: {signals['textDirection']} != {expected_direction}")
    require({"visualize", "overview", "reject"}.issubset(seen_decisions), f"{path} must cover visualize, overview, and reject decisions")
    require({"zh-CN", "ar"}.issubset(seen_locales), f"{path} must cover CJK and RTL locale preservation")
    ok(f"Input quality checks passed: {path}")


def count_matches(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


TEMPLATE_SELECTION_RULES = [
    {
        "template": "swimlane_workflow",
        "layoutIntent": "swimlane",
        "terms": ["lane", "lanes", "customer", "support", "engineering", "operations", "handoff", "owner"],
        "threshold": 3,
    },
    {
        "template": "roadmap_timeline",
        "layoutIntent": "timeline",
        "terms": ["q1", "q2", "q3", "q4", "phase", "phases", "milestone", "roadmap", "rollout", "gate"],
        "threshold": 3,
    },
    {
        "template": "architecture_stack",
        "layoutIntent": "layered",
        "terms": ["layer", "layers", "stack", "architecture", "api", "service", "services", "data layer", "observability"],
        "threshold": 3,
    },
    {
        "template": "kpi_dashboard",
        "layoutIntent": "dashboard",
        "terms": ["kpi", "metric", "metrics", "uptime", "latency", "error rate", "alert", "incident", "snapshot"],
        "threshold": 3,
    },
    {
        "template": "org_hierarchy",
        "layoutIntent": "hierarchy",
        "terms": ["hierarchy", "organization", "org", "vp", "team", "lead", "owns", "ownership", "responsibility", "escalation"],
        "threshold": 3,
    },
    {
        "template": "decision_matrix",
        "layoutIntent": "comparison",
        "terms": ["compare", "option", "options", "tradeoff", "tradeoffs", "cost", "speed", "risk", "recommend"],
        "threshold": 3,
    },
    {
        "template": "feedback_loop",
        "layoutIntent": "loop",
        "terms": ["loop", "feedback", "observes", "measure", "measures", "health", "lessons", "back into", "planning"],
        "threshold": 3,
    },
    {
        "template": "cause_effect_map",
        "layoutIntent": "loop",
        "terms": ["because", "cause", "causes", "symptom", "symptoms", "impact", "mitigation", "mitigations", "churn"],
        "threshold": 3,
    },
    {
        "template": "concept_map",
        "layoutIntent": "hub_spoke",
        "terms": ["central concept", "clusters", "cluster", "related", "principles", "around", "topic", "knowledge"],
        "threshold": 3,
    },
]


def select_infographic_template(text: str) -> dict[str, str]:
    signals = detect_input_quality_signals(text)
    if signals["decision"] == "reject":
        return {
            "decision": "reject",
            "template": "none",
            "layoutIntent": "none",
        }

    scored = []
    for index, rule in enumerate(TEMPLATE_SELECTION_RULES):
        score = count_matches(text, rule["terms"])
        if score >= rule["threshold"]:
            scored.append((score, -index, rule))
    if scored:
        _, _, rule = max(scored)
        return {
            "decision": "visualize",
            "template": str(rule["template"]),
            "layoutIntent": str(rule["layoutIntent"]),
        }

    if count_matches(text, ["impact", "effort", "rank", "prioritize", "priority", "two-axis", "axis"]) >= 3:
        return {
            "decision": "visualize",
            "template": "universal_fallback",
            "layoutIntent": "matrix",
        }

    return {
        "decision": "visualize",
        "template": "universal_fallback",
        "layoutIntent": "freeform",
    }


def validate_template_selection_cases(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 10, f"{path} should include at least 10 template selection cases")
    expected_templates = {
        "decision_matrix",
        "kpi_dashboard",
        "org_hierarchy",
        "cause_effect_map",
        "swimlane_workflow",
        "roadmap_timeline",
        "architecture_stack",
        "feedback_loop",
        "concept_map",
        "universal_fallback",
    }
    expected_intents = {"comparison", "dashboard", "hierarchy", "loop", "swimlane", "timeline", "layered", "hub_spoke", "matrix", "freeform"}
    seen_ids: set[str] = set()
    seen_templates: set[str] = set()
    seen_intents: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        require(case.get("inputType") == "assistant_response", f"{path} {case_id} inputType must be assistant_response")
        text = case.get("input")
        require(isinstance(text, str) and text.strip(), f"{path} {case_id} input is required")
        expected_decision = case.get("expectedDecision")
        require(expected_decision in {"visualize", "reject"}, f"{path} {case_id} expectedDecision is invalid")
        expected_template = case.get("expectedTemplate")
        require(expected_template in expected_templates, f"{path} {case_id} expectedTemplate is invalid")
        expected_intent = case.get("expectedLayoutIntent")
        require(expected_intent in expected_intents, f"{path} {case_id} expectedLayoutIntent is invalid")
        selected = select_infographic_template(text)
        require(selected["decision"] == expected_decision, f"{path} {case_id} decision mismatch: {selected['decision']} != {expected_decision}")
        require(selected["template"] == expected_template, f"{path} {case_id} template mismatch: {selected['template']} != {expected_template}")
        require(selected["layoutIntent"] == expected_intent, f"{path} {case_id} layout intent mismatch: {selected['layoutIntent']} != {expected_intent}")
        seen_templates.add(str(expected_template))
        seen_intents.add(str(expected_intent))
    missing_templates = sorted(expected_templates - seen_templates)
    require(not missing_templates, f"{path} missing expected template coverage: {missing_templates}")
    missing_intents = sorted(expected_intents - seen_intents)
    require(not missing_intents, f"{path} missing expected intent coverage: {missing_intents}")
    ok(f"Template selection checks passed: {path}")


def validate_host_css(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required_selectors = [
        ".svgflow .arr",
        ".svgflow .th",
        ".svgflow .ts",
        ".svgflow .label",
        ".svgflow .c-blue",
        ".svgflow .c-amber",
        ".svgflow .c-gray",
    ]
    for selector in required_selectors:
        require(selector in text, f"{path} missing required host CSS selector: {selector}")
    ok(f"Host CSS checks passed: {path}")


def validate_pipeline_helper(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require("run_pipeline_validators" in text, f"{path} must execute validators through the shared pipeline runner")
    require("PIPELINE_VALIDATORS" in text, f"{path} must use the shared pipeline validator registry")
    require("known_validators =" not in text, f"{path} must not duplicate known pipeline validator names")
    require("elif validator_name ==" not in text, f"{path} must dispatch pipeline validators through the shared registry")
    ok(f"Pipeline helper checks passed: {path}")


def validate_validator_maintainability(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    require("COMMAND_HANDLERS" in text, f"{path} must use a command handler registry")
    legacy_dispatch_count = text.count("if len(sys.argv) == 3 and sys.argv[1] ==")
    require(legacy_dispatch_count <= 1, f"{path} has too many ad-hoc CLI branches: {legacy_dispatch_count}")
    require("print_usage()" in text, f"{path} must centralize CLI usage output")
    ok(f"Validator maintainability checks passed: {path}")


def load_pipeline_helper(root: Path) -> object:
    helper_path = root / "scripts/run_pipeline_fixture.py"
    spec = importlib.util.spec_from_file_location("svgflow_run_pipeline_fixture", helper_path)
    require(spec is not None and spec.loader is not None, f"unable to load pipeline helper: {helper_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_prompt_guidance(root: Path) -> None:
    required = {
        "prompts/response_parser.md": ["universal infographic", "layout intent", "comparison", "input quality gate", "overview"],
        "prompts/flow_dsl_builder.md": ["diagramType: infographic", "layout.intent", "dashboard"],
        "prompts/layout_planner.md": ["Universal infographic layout", "hub_spoke", "hierarchy"],
        "prompts/svg_renderer.md": ["Universal infographic SVG", "layout.intent", "Escape prompt text"],
        "prompts/validator_repair.md": [
            "Universal infographic checklist",
            "layout intent",
            "text is too long",
            "compact legend",
            "protect labels",
            "palette is too narrow",
            "clickable groups",
            "escaped prompt string",
            "readability score",
        ],
        "validators/repair_rules.md": [
            "Infographic text is too long",
            "Compact legend is missing",
            "Connector label lacks protection",
            "Palette is too narrow",
            "sendPrompt is detached",
            "prompt string is not escaped",
            "Readability score is too low",
        ],
    }
    for relative, fragments in required.items():
        text = (root / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            require(fragment in text, f"{relative} missing v2 guidance fragment: {fragment}")
    ok("Prompt guidance checks passed")


def validate_production_docs(root: Path) -> None:
    required = {
        "docs/production-checklist.md": [
            "Production Invocation Path",
            "Required Release Command",
            "input quality gate",
            "scripts/run_repair_signal_fixture.py",
            "python3 scripts/validate_svg.py --unknown-infographic .",
            "python3 scripts/validate_svg.py --template-selection .",
            "python3 scripts/validate_svg.py --readability-score .",
            "python3 scripts/validate_svg.py --text-fit .",
            "python3 scripts/validate_svg.py --escaping-safety .",
            "python3 scripts/validate_svg.py --interaction-accessibility .",
            "python3 scripts/validate_svg.py --renderer-contract .",
            "python3 scripts/validate_svg.py --production-svg-contract .",
            "python3 scripts/validate_svg.py --production-html-contract .",
            "python3 scripts/validate_svg.py --render-surface .",
            "node scripts/check_browser_render_metrics.mjs --root . --cases tests/browser_render_metric_cases.json",
            "python3 scripts/validate_svg.py --negative-pipeline .",
            "python3 scripts/validate_svg.py --release-check .",
            "DSL plus the right rendered artifact validators",
            "Failure Triage",
            "Production Readiness Invariants",
            "Publish Checklist",
            "Chinese text appears only in `README.zh-CN.md` or necessary language fixtures.",
        ],
        "README.md": [
            "python3 scripts/validate_svg.py --release-check .",
            "input quality",
            "unknown infographic",
            "template selection",
            "readability score",
            "text-fit",
            "escaping safety",
            "interaction accessibility",
            "renderer contract",
            "production SVG contract",
            "production HTML contract",
            "render surface contract",
            "browser render metrics",
            "node scripts/check_browser_render_metrics.mjs --root . --cases tests/browser_render_metric_cases.json",
            "scripts/run_repair_signal_fixture.py",
            "scripts/run_pipeline_fixture.py",
            "SVG or HTML artifact validators",
            "negative pipeline",
            "text-fit failures, interaction-accessibility failures",
            "prompt escaping failures",
            "docs/production-checklist.md",
        ],
        "SKILL.md": [
            "python3 scripts/validate_svg.py --release-check .",
            "input quality",
            "unknown infographic",
            "template selection",
            "readability score",
            "text-fit",
            "escaping safety",
            "interaction accessibility",
            "renderer contract",
            "production SVG contract",
            "production HTML contract",
            "render surface contract",
            "browser render metrics",
            "node scripts/check_browser_render_metrics.mjs --root . --cases tests/browser_render_metric_cases.json",
            "scripts/run_repair_signal_fixture.py",
            "scripts/run_pipeline_fixture.py",
            "SVG or HTML artifact validators",
            "docs/production-checklist.md",
        ],
    }
    for relative, fragments in required.items():
        text = (root / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            require(fragment in text, f"{relative} missing production guidance fragment: {fragment}")
    ok("Production documentation checks passed")


def validate_legacy_mapping(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    mappings = data.get("mappings")
    require(isinstance(mappings, list), f"{path} mappings must be an array")
    expected_legacy = {
        "flowchart",
        "knowledge_map",
        "architecture_map",
        "interactive_walkthrough",
        "system_loop",
        "module_grid",
        "agentic_pipeline",
        "phased_pipeline",
    }
    allowed_intents = {"linear", "layered", "loop", "matrix", "hub_spoke", "timeline", "swimlane", "comparison", "hierarchy", "dashboard", "freeform"}
    seen_legacy: set[str] = set()
    for mapping in mappings:
        require(isinstance(mapping, dict), f"{path} mapping must be an object")
        legacy = mapping.get("legacyDiagramType")
        require(legacy in expected_legacy, f"{path} invalid legacyDiagramType: {legacy}")
        require(legacy not in seen_legacy, f"{path} duplicate legacyDiagramType: {legacy}")
        seen_legacy.add(legacy)
        require(mapping.get("v2DiagramType") == "infographic", f"{path} {legacy} must map to infographic")
        intents = mapping.get("layoutIntents")
        require(isinstance(intents, list) and intents, f"{path} {legacy} layoutIntents are required")
        for intent in intents:
            require(intent in allowed_intents, f"{path} {legacy} invalid intent: {intent}")
        primitives = mapping.get("contentPrimitives")
        require(isinstance(primitives, list) and primitives, f"{path} {legacy} contentPrimitives are required")
        for primitive in primitives:
            require(primitive in {"nodes", "groups", "edges", "labels", "legends", "steps", "interactions"}, f"{path} {legacy} invalid primitive: {primitive}")
        require(isinstance(mapping.get("compatibilityNote"), str) and mapping["compatibilityNote"].strip(), f"{path} {legacy} compatibilityNote is required")
    missing = sorted(expected_legacy - seen_legacy)
    require(not missing, f"{path} missing legacy mappings: {missing}")
    ok(f"Legacy mapping checks passed: {path}")


def validate_template_catalog(path: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    templates = data.get("templates")
    require(isinstance(templates, list), f"{path} templates must be an array")
    expected_ids = {
        "decision_matrix",
        "kpi_dashboard",
        "org_hierarchy",
        "cause_effect_map",
        "swimlane_workflow",
        "roadmap_timeline",
        "architecture_stack",
        "feedback_loop",
        "concept_map",
        "freeform_insight_map",
    }
    allowed_intents = {"linear", "layered", "loop", "matrix", "hub_spoke", "timeline", "swimlane", "comparison", "hierarchy", "dashboard", "freeform"}
    allowed_primitives = {"nodes", "groups", "edges", "labels", "legends", "steps", "interactions"}
    seen_ids: set[str] = set()
    seen_intents: set[str] = set()
    for template in templates:
        require(isinstance(template, dict), f"{path} template must be an object")
        template_id = template.get("id")
        require(template_id in expected_ids, f"{path} unexpected template id: {template_id}")
        require(template_id not in seen_ids, f"{path} duplicate template id: {template_id}")
        seen_ids.add(template_id)
        require(template.get("diagramType") == "infographic", f"{path} {template_id} must use infographic")
        intent = template.get("layoutIntent")
        require(intent in allowed_intents, f"{path} {template_id} has invalid layoutIntent: {intent}")
        seen_intents.add(intent)
        require(isinstance(template.get("name"), str) and template["name"].strip(), f"{path} {template_id} name is required")
        require(isinstance(template.get("whenToUse"), str) and template["whenToUse"].strip(), f"{path} {template_id} whenToUse is required")
        primitives = template.get("requiredPrimitives")
        require(isinstance(primitives, list) and primitives, f"{path} {template_id} requiredPrimitives are required")
        for primitive in primitives:
            require(primitive in allowed_primitives, f"{path} {template_id} invalid primitive: {primitive}")
        node_kinds = template.get("nodeKinds")
        require(isinstance(node_kinds, list) and node_kinds, f"{path} {template_id} nodeKinds are required")
        edge_kinds = template.get("edgeKinds", [])
        require(isinstance(edge_kinds, list), f"{path} {template_id} edgeKinds must be an array")
        require(isinstance(template.get("rendererNotes"), list) and template["rendererNotes"], f"{path} {template_id} rendererNotes are required")
    missing = sorted(expected_ids - seen_ids)
    require(not missing, f"{path} missing templates: {missing}")
    require({"comparison", "dashboard", "hierarchy", "loop", "swimlane", "timeline", "layered", "hub_spoke", "freeform"}.issubset(seen_intents), f"{path} template catalog missing core layout intent coverage")
    ok(f"Template catalog checks passed: {path}")


def validate_e2e_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 7, f"{path} should include at least 7 v2 e2e cases")
    expected_templates = {
        "decision_matrix",
        "architecture_stack",
        "swimlane_workflow",
        "roadmap_timeline",
        "cause_effect_map",
        "feedback_loop",
        "freeform_insight_map",
    }
    seen_templates: set[str] = set()
    seen_input_file = False
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case.get("inputType") == "assistant_response", f"{path} {case_id} inputType must be assistant_response")
        inline_input = case.get("input")
        input_file = case.get("inputFile")
        if isinstance(input_file, str):
            seen_input_file = True
            input_path = root / input_file
            require(input_path.exists(), f"{path} {case_id} missing input file: {input_path}")
            input_text = input_path.read_text(encoding="utf-8")
            require(input_text.strip(), f"{path} {case_id} input file is empty: {input_path}")
            require(len(input_text.strip()) >= 400, f"{path} {case_id} input file should be a realistic assistant response: {input_path}")
        else:
            require(isinstance(inline_input, str) and inline_input.strip(), f"{path} {case_id} input is required")
        template_id = case.get("expectedTemplate")
        require(template_id in expected_templates, f"{path} {case_id} unexpected template: {template_id}")
        seen_templates.add(template_id)
        require(case.get("expectedDiagramType") == "infographic", f"{path} {case_id} must expect infographic")
        require(isinstance(case.get("expectedLayoutIntent"), str) and case["expectedLayoutIntent"], f"{path} {case_id} expectedLayoutIntent is required")
        dsl_path = root / str(case.get("dsl"))
        svg_path = root / str(case.get("svg"))
        require(dsl_path.exists(), f"{path} {case_id} missing DSL fixture: {dsl_path}")
        require(svg_path.exists(), f"{path} {case_id} missing SVG fixture: {svg_path}")
        validate_infographic_dsl(dsl_path)
        dsl = read_json(dsl_path)
        require(isinstance(dsl, dict), f"{dsl_path} must contain a JSON object")
        layout = dsl.get("layout", {})
        require(isinstance(layout, dict) and layout.get("intent") == case["expectedLayoutIntent"], f"{path} {case_id} DSL layout intent mismatch")
        validate_infographic_svg(svg_path)
        validate_visual_quality_svg(svg_path)
    missing = sorted(expected_templates - seen_templates)
    require(not missing, f"{path} missing e2e template cases: {missing}")
    require(seen_input_file, f"{path} should include at least one real-response inputFile case")
    ok(f"E2E case checks passed: {path}")


def validate_unknown_infographic_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 2, f"{path} should include at least 2 unknown infographic fallback cases")

    catalog = read_json(root / "templates/infographic-templates.json")
    require(isinstance(catalog, dict), "template catalog must contain a JSON object")
    templates = catalog.get("templates")
    require(isinstance(templates, list), "template catalog templates must be an array")
    known_templates = {template.get("id") for template in templates if isinstance(template, dict)}
    allowed_intents = {"linear", "layered", "loop", "matrix", "hub_spoke", "timeline", "swimlane", "comparison", "hierarchy", "dashboard", "freeform"}
    expected_validators = {"infographic_dsl", "infographic_svg", "visual_quality", "readability_score"}
    legacy_types = {"flowchart", "knowledge_map", "architecture_map", "interactive_walkthrough", "system_loop", "module_grid", "agentic_pipeline", "phased_pipeline"}

    seen_ids: set[str] = set()
    seen_intents: set[str] = set()
    seen_fixtures: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        require(case.get("inputType") == "assistant_response", f"{path} {case_id} inputType must be assistant_response")
        source_input = case.get("input")
        require(isinstance(source_input, str) and len(source_input.strip()) >= 120, f"{path} {case_id} input should be a realistic assistant response")
        expected_template = case.get("expectedTemplate")
        require(expected_template == "universal_fallback", f"{path} {case_id} expectedTemplate must be universal_fallback")
        require(expected_template not in known_templates, f"{path} {case_id} fallback must not be a catalog template")
        require(case.get("expectedDiagramType") == "infographic", f"{path} {case_id} must expect infographic")
        disallowed = case.get("disallowedDiagramTypes")
        require(isinstance(disallowed, list), f"{path} {case_id} disallowedDiagramTypes must be an array")
        require(legacy_types.issubset(set(disallowed)), f"{path} {case_id} should explicitly reject legacy diagram families")
        layout_intent = case.get("expectedLayoutIntent")
        require(layout_intent in allowed_intents, f"{path} {case_id} expectedLayoutIntent is invalid")
        seen_intents.add(str(layout_intent))
        validators = case.get("validators")
        require(isinstance(validators, list), f"{path} {case_id} validators must be an array")
        require(set(validators) == expected_validators, f"{path} {case_id} validators must cover DSL, SVG, visual quality, and readability")

        dsl_path = root / str(case.get("dsl"))
        svg_path = root / str(case.get("svg"))
        require(dsl_path.exists(), f"{path} {case_id} missing DSL fixture: {dsl_path}")
        require(svg_path.exists(), f"{path} {case_id} missing SVG fixture: {svg_path}")
        require(str(dsl_path) not in seen_fixtures, f"{path} {case_id} reuses a DSL fixture")
        require(str(svg_path) not in seen_fixtures, f"{path} {case_id} reuses an SVG fixture")
        seen_fixtures.add(str(dsl_path))
        seen_fixtures.add(str(svg_path))

        validate_infographic_dsl(dsl_path)
        dsl = read_json(dsl_path)
        require(isinstance(dsl, dict), f"{dsl_path} must contain a JSON object")
        meta = dsl.get("meta", {})
        require(isinstance(meta, dict) and meta.get("diagramType") == "infographic", f"{dsl_path} must remain a universal infographic")
        layout = dsl.get("layout", {})
        require(isinstance(layout, dict) and layout.get("intent") == layout_intent, f"{path} {case_id} DSL layout intent mismatch")
        validate_infographic_svg(svg_path)
        validate_visual_quality_svg(svg_path)
        score = score_readability_svg(svg_path)
        require(isinstance(score.get("score"), int) and score["score"] >= 75, f"{svg_path} readability score is too low: {score}")

    require({"matrix", "freeform"}.issubset(seen_intents), f"{path} should cover matrix and freeform fallback intents")
    ok(f"Unknown infographic fallback checks passed: {path}")


def require_dsl_primitive_condition(dsl: dict[str, object], condition: str, expected: object, source: Path) -> None:
    content = dsl.get("content", {})
    require(isinstance(content, dict), f"{source} content must be an object")
    layout = dsl.get("layout", {})
    require(isinstance(layout, dict), f"{source} layout must be an object")
    nodes = content.get("nodes", [])
    groups = content.get("groups", [])
    edges = content.get("edges", [])
    steps = content.get("steps", [])
    require(isinstance(nodes, list), f"{source} content.nodes must be an array")
    require(isinstance(groups, list), f"{source} content.groups must be an array")
    require(isinstance(edges, list), f"{source} content.edges must be an array")
    require(isinstance(steps, list), f"{source} content.steps must be an array")

    if condition == "layout.intent":
        require(layout.get("intent") == expected, f"{source} layout.intent must be {expected}")
    elif condition == "content.groups.min":
        require(isinstance(expected, int), f"{source} content.groups.min expectation must be an integer")
        require(len(groups) >= expected, f"{source} must include at least {expected} groups")
    elif condition == "content.nodes.min":
        require(isinstance(expected, int), f"{source} content.nodes.min expectation must be an integer")
        require(len(nodes) >= expected, f"{source} must include at least {expected} nodes")
    elif condition == "content.steps.min":
        require(isinstance(expected, int), f"{source} content.steps.min expectation must be an integer")
        require(len(steps) >= expected, f"{source} must include at least {expected} steps")
    elif condition == "node.parent.present":
        require(expected is True, f"{source} node.parent.present expectation must be true")
        require(
            any(isinstance(node, dict) and isinstance(node.get("parent"), str) and node["parent"].strip() for node in nodes),
            f"{source} must include nested node parent membership",
        )
    elif condition == "node.kind.includes":
        require(
            any(isinstance(node, dict) and node.get("kind") == expected for node in nodes),
            f"{source} must include node kind: {expected}",
        )
    elif condition == "edge.route.includes":
        require(
            any(isinstance(edge, dict) and edge.get("route") == expected for edge in edges),
            f"{source} must include edge route: {expected}",
        )
    elif condition == "edge.kind.includes":
        require(
            any(isinstance(edge, dict) and edge.get("kind") == expected for edge in edges),
            f"{source} must include edge kind: {expected}",
        )
    elif condition == "graph.fanout.min":
        require(isinstance(expected, int), f"{source} graph.fanout.min expectation must be an integer")
        outgoing: dict[str, int] = {}
        for edge in edges:
            if isinstance(edge, dict) and isinstance(edge.get("from"), str):
                outgoing[edge["from"]] = outgoing.get(edge["from"], 0) + 1
        require(any(count >= expected for count in outgoing.values()), f"{source} must include fan-out of at least {expected}")
    elif condition == "graph.fanin.min":
        require(isinstance(expected, int), f"{source} graph.fanin.min expectation must be an integer")
        incoming: dict[str, int] = {}
        for edge in edges:
            if isinstance(edge, dict) and isinstance(edge.get("to"), str):
                incoming[edge["to"]] = incoming.get(edge["to"], 0) + 1
        require(any(count >= expected for count in incoming.values()), f"{source} must include fan-in of at least {expected}")
    else:
        fail(f"{source} unknown DSL primitive condition: {condition}")


def require_svg_primitive_condition(text: str, condition: str, expected: object, source: Path) -> None:
    if condition == "svg.mask.present":
        require(expected is True, f"{source} svg.mask.present expectation must be true")
        require("<mask" in text and "mask=" in text, f"{source} must include label gap masks")
    elif condition == "svg.label_backgrounds.min":
        require(isinstance(expected, int), f"{source} svg.label_backgrounds.min expectation must be an integer")
        count = len(re.findall(r"<rect[^>]+rgba\(222,\s*220,\s*209,\s*0\.3\)", text))
        require(count >= expected, f"{source} must include at least {expected} protected label backgrounds")
    elif condition == "svg.legend_swatches.min":
        require(isinstance(expected, int), f"{source} svg.legend_swatches.min expectation must be an integer")
        count = len(re.findall(r"<rect[^>]+width=\"12\"[^>]+height=\"12\"", text))
        require(count >= expected, f"{source} must include at least {expected} legend swatches")
    elif condition == "svg.onclick.min":
        require(isinstance(expected, int), f"{source} svg.onclick.min expectation must be an integer")
        count = text.count("onclick=")
        require(count >= expected, f"{source} must include at least {expected} clickable modules")
    else:
        fail(f"{source} unknown SVG primitive condition: {condition}")


def validate_primitive_coverage_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("requiredPrimitives")
    require(isinstance(cases, list), f"{path} requiredPrimitives must be an array")
    required_ids = {
        "group_containers",
        "lane_groups",
        "nested_membership",
        "feedback_loop_edges",
        "fanout_and_fanin",
        "phase_steps",
        "protected_connector_labels",
        "legend_swatches",
        "card_grid",
        "clickable_modules",
    }
    seen_ids: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} primitive case must be an object")
        case_id = case.get("id")
        require(case_id in required_ids, f"{path} unknown primitive id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate primitive id: {case_id}")
        seen_ids.add(str(case_id))
        evidence = case.get("evidence")
        require(isinstance(evidence, list) and evidence, f"{path} {case_id} evidence must be a non-empty array")
        for item in evidence:
            require(isinstance(item, dict), f"{path} {case_id} evidence item must be an object")
            requires = item.get("requires")
            require(isinstance(requires, dict) and requires, f"{path} {case_id} evidence requires must be an object")
            dsl_file = item.get("dsl")
            svg_file = item.get("svg")
            require(isinstance(dsl_file, str) != isinstance(svg_file, str), f"{path} {case_id} evidence must reference exactly one DSL or SVG")
            if isinstance(dsl_file, str):
                dsl_path = root / dsl_file
                require(dsl_path.exists(), f"{path} {case_id} missing DSL evidence: {dsl_path}")
                validate_infographic_dsl(dsl_path)
                dsl = read_json(dsl_path)
                require(isinstance(dsl, dict), f"{dsl_path} must contain a JSON object")
                for condition, expected in requires.items():
                    require_dsl_primitive_condition(dsl, condition, expected, dsl_path)
            else:
                svg_path = root / str(svg_file)
                require(svg_path.exists(), f"{path} {case_id} missing SVG evidence: {svg_path}")
                validate_infographic_svg(svg_path)
                text = svg_path.read_text(encoding="utf-8")
                for condition, expected in requires.items():
                    require_svg_primitive_condition(text, condition, expected, svg_path)
    missing = sorted(required_ids - seen_ids)
    require(not missing, f"{path} missing primitive coverage ids: {missing}")
    ok(f"Primitive coverage checks passed: {path}")


def validate_production_pipeline_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    expected_pipeline = [
        "response_parser",
        "dsl_builder",
        "layout_planner",
        "svg_renderer",
        "validator",
        "repair",
    ]
    require(data.get("pipeline") == expected_pipeline, f"{path} pipeline must describe the production invocation order")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 4, f"{path} should include at least 4 production pipeline cases")
    seen_ids: set[str] = set()
    seen_input_file = False
    seen_fallback = False
    seen_readability = False
    seen_html = False
    svg_required_validators = {"infographic_dsl", "infographic_svg", "visual_quality", "readability_score", "text_fit", "escaping_safety", "interaction_accessibility"}
    html_required_validators = {
        "interactive_walkthrough": {"walkthrough_dsl", "walkthrough_html", "production_html_contract", "render_surface", "escaping_safety"},
        "module_grid": {"module_grid_dsl", "module_grid_html", "production_html_contract", "render_surface", "escaping_safety"},
    }
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        require(case.get("inputType") == "assistant_response", f"{path} {case_id} inputType must be assistant_response")
        input_file = case.get("inputFile")
        inline_input = case.get("input")
        if isinstance(input_file, str):
            seen_input_file = True
            input_path = root / input_file
            require(input_path.exists(), f"{path} {case_id} missing input file: {input_path}")
            require(input_path.read_text(encoding="utf-8").strip(), f"{path} {case_id} input file is empty")
        else:
            require(isinstance(inline_input, str) and inline_input.strip(), f"{path} {case_id} input is required")
        require(isinstance(case.get("expectedTemplate"), str) and case["expectedTemplate"].strip(), f"{path} {case_id} expectedTemplate is required")
        diagram_type = case.get("expectedDiagramType")
        require(diagram_type in {"infographic", "interactive_walkthrough", "module_grid"}, f"{path} {case_id} expectedDiagramType is invalid")
        if case.get("expectedTemplate") == "universal_fallback":
            seen_fallback = True
        require(case.get("repairPolicy") == "single_pass", f"{path} {case_id} repairPolicy must be single_pass")
        validators = case.get("validators")
        require(isinstance(validators, list), f"{path} {case_id} validators must be an array")
        dsl_path = root / str(case.get("dsl"))
        require(dsl_path.exists(), f"{path} {case_id} missing DSL fixture: {dsl_path}")
        if diagram_type == "infographic":
            require(isinstance(case.get("expectedLayoutIntent"), str) and case["expectedLayoutIntent"].strip(), f"{path} {case_id} expectedLayoutIntent is required")
            require(set(validators) == svg_required_validators, f"{path} {case_id} validators must cover DSL, SVG, and visual quality")
            svg_path = root / str(case.get("svg"))
            require(svg_path.exists(), f"{path} {case_id} missing SVG fixture: {svg_path}")
            run_pipeline_validators(validators, dsl_path, svg_path=svg_path)
            dsl = read_json(dsl_path)
            require(isinstance(dsl, dict), f"{dsl_path} must contain a JSON object")
            layout = dsl.get("layout", {})
            require(isinstance(layout, dict) and layout.get("intent") == case["expectedLayoutIntent"], f"{path} {case_id} DSL layout intent mismatch")
            if "readability_score" in validators:
                seen_readability = True
        else:
            require("expectedLayoutIntent" not in case, f"{path} {case_id} HTML pipeline cases must not require layout intent")
            expected = html_required_validators[str(diagram_type)]
            require(set(validators) == expected, f"{path} {case_id} validators must cover DSL, HTML, production contract, render surface, and escaping")
            html_path = root / str(case.get("html"))
            require(html_path.exists(), f"{path} {case_id} missing HTML fixture: {html_path}")
            html_type = case.get("htmlType")
            require(html_type in {"walkthrough", "module_grid"}, f"{path} {case_id} htmlType is invalid")
            require(infer_html_type(html_path) == html_type, f"{path} {case_id} HTML filename does not match htmlType")
            run_pipeline_validators(validators, dsl_path, html_path=html_path)
            dsl = read_json(dsl_path)
            require(isinstance(dsl, dict), f"{dsl_path} must contain a JSON object")
            meta = dsl.get("meta", {})
            require(isinstance(meta, dict) and meta.get("diagramType") == diagram_type, f"{path} {case_id} DSL diagram type mismatch")
            seen_html = True
    require(seen_input_file, f"{path} should include at least one real assistant response inputFile case")
    require(seen_fallback, f"{path} should include at least one universal_fallback production case")
    require(seen_readability, f"{path} should run readability_score in production validators")
    require(seen_html, f"{path} should include at least one production HTML pipeline case")
    ok(f"Production pipeline case checks passed: {path}")


def run_pipeline_case_expect_failure(root: Path, case: dict[str, object]) -> str:
    helper = load_pipeline_helper(root)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            helper.validate_case(root, case)
    except SystemExit as exc:
        output = buffer.getvalue()
        require(exc.code != 0, "negative pipeline case exited successfully when failure was expected")
        require("[FAIL]" in output, "negative pipeline case did not emit a failure")
        return output
    fail("negative pipeline case passed; expected failure")


def validate_negative_pipeline_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 3, f"{path} should include at least 3 negative pipeline cases")

    production = read_json(root / "tests/production_pipeline_cases.json")
    require(isinstance(production, dict), "production pipeline cases must contain a JSON object")
    production_cases = production.get("cases")
    require(isinstance(production_cases, list), "production pipeline cases must contain cases[]")
    production_by_id = {case.get("id"): case for case in production_cases if isinstance(case, dict)}

    seen_ids: set[str] = set()
    seen_failures: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        source_case = case.get("sourceCase")
        require(source_case in production_by_id, f"{path} {case_id} sourceCase must reference a production pipeline case")
        override = case.get("override")
        require(isinstance(override, dict) and override, f"{path} {case_id} override is required")
        expected = case.get("expectedFailure")
        require(isinstance(expected, str) and expected.strip(), f"{path} {case_id} expectedFailure is required")
        merged_case = copy.deepcopy(production_by_id[source_case])
        require(isinstance(merged_case, dict), f"{path} {case_id} source production case must be an object")
        merged_case.update(override)
        output = run_pipeline_case_expect_failure(root, merged_case)
        require(expected in output, f"{path} {case_id} expected failure not found: {expected}")
        seen_failures.add(expected)

    required_failures = {
        "unknown pipeline validator",
        "text is too long",
        "layout intent does not match pipeline case",
        "unbreakable text",
        "keyboard handler",
        "escaped prompt string",
    }
    missing = sorted(required_failures - seen_failures)
    require(not missing, f"{path} missing negative pipeline failure coverage: {missing}")
    ok(f"Negative pipeline checks passed: {path}")


def validate_visual_quality(root: Path) -> None:
    paths = sorted((root / "examples").glob("*infographic.interactive.svg"))
    require(paths, "No infographic SVG examples found for visual quality validation")
    for path in paths:
        validate_visual_quality_svg(path)
    ok("Visual quality checks passed")


def validate_production_svg_contract(root: Path) -> None:
    paths = sorted((root / "examples").glob("*infographic.interactive.svg"))
    require(paths, "No infographic SVG examples found for production SVG contract validation")
    for path in paths:
        validate_infographic_svg(path)
        validate_visual_quality_svg(path)
        validate_text_fit_svg(path)
        validate_escaping_safety_asset(path)
        validate_interaction_accessibility_svg(path)
    ok("Production SVG contract checks passed")


def run_validator_expect_failure(validator_name: str, fixture_path: Path) -> str:
    validators = {
        "infographic_svg": validate_infographic_svg,
        "visual_quality": validate_visual_quality_svg,
    }
    validator = validators.get(validator_name)
    require(validator is not None, f"unknown negative validator: {validator_name}")
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            validator(fixture_path)
    except SystemExit as exc:
        output = buffer.getvalue()
        require(exc.code != 0, f"{fixture_path} validator exited successfully when failure was expected")
        require("[FAIL]" in output, f"{fixture_path} negative validator did not emit a failure")
        return output
    fail(f"{fixture_path} passed {validator_name}; expected a negative visual-quality failure")


def validate_negative_visual_quality(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 5, f"{path} should include at least 5 negative visual-quality cases")
    seen_ids: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith(".svg"), f"{path} {case_id} fixture must be an SVG path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        validator_name = case.get("validator")
        require(isinstance(validator_name, str), f"{path} {case_id} validator is required")
        expected = case.get("expectedFailure")
        require(isinstance(expected, str) and expected.strip(), f"{path} {case_id} expectedFailure is required")
        output = run_validator_expect_failure(validator_name, fixture_path)
        require(expected in output, f"{path} {case_id} expected failure not found: {expected}")
    ok(f"Negative visual quality checks passed: {path}")


def run_text_fit_expect_failure(fixture_path: Path) -> str:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            validate_text_fit_svg(fixture_path)
    except SystemExit as exc:
        output = buffer.getvalue()
        require(exc.code != 0, f"{fixture_path} text-fit validator exited successfully when failure was expected")
        require("[FAIL]" in output, f"{fixture_path} text-fit validator did not emit a failure")
        return output
    fail(f"{fixture_path} passed text-fit validation; expected failure")


def validate_text_fit_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    valid_cases = data.get("valid")
    invalid_cases = data.get("invalid")
    require(isinstance(valid_cases, list) and len(valid_cases) >= 3, f"{path} valid cases must include at least 3 fixtures")
    require(isinstance(invalid_cases, list) and len(invalid_cases) >= 3, f"{path} invalid cases must include at least 3 fixtures")
    seen_ids: set[str] = set()
    seen_signals: set[str] = set()
    for case in valid_cases:
        require(isinstance(case, dict), f"{path} valid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid valid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith(".svg"), f"{path} {case_id} fixture must be an SVG path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        required_signals = case.get("signals")
        require(isinstance(required_signals, list) and required_signals, f"{path} {case_id} signals are required")
        actual_signals = text_fit_signal_set(fixture_path)
        for signal in required_signals:
            require(isinstance(signal, str) and signal, f"{path} {case_id} invalid signal")
            require(signal in actual_signals, f"{fixture_path} missing text-fit signal: {signal}")
            seen_signals.add(signal)
    for case in invalid_cases:
        require(isinstance(case, dict), f"{path} invalid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid invalid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith(".svg"), f"{path} {case_id} fixture must be an SVG path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        expected = case.get("expectedFailure")
        require(isinstance(expected, str) and expected.strip(), f"{path} {case_id} expectedFailure is required")
        output = run_text_fit_expect_failure(fixture_path)
        require(expected in output, f"{path} {case_id} expected failure not found: {expected}")
    missing_signals = sorted({"explicitFit", "stableLetterSpacing", "cjkLocale", "rtlLocale"} - seen_signals)
    require(not missing_signals, f"{path} missing text-fit signal coverage: {missing_signals}")
    ok(f"Text-fit case checks passed: {path}")


def run_interaction_accessibility_expect_failure(fixture_path: Path) -> str:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            validate_interaction_accessibility_svg(fixture_path)
    except SystemExit as exc:
        output = buffer.getvalue()
        require(exc.code != 0, f"{fixture_path} interaction-accessibility validator exited successfully when failure was expected")
        require("[FAIL]" in output, f"{fixture_path} interaction-accessibility validator did not emit a failure")
        return output
    fail(f"{fixture_path} passed interaction-accessibility validation; expected failure")


def validate_interaction_accessibility_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    valid_cases = data.get("valid")
    invalid_cases = data.get("invalid")
    require(isinstance(valid_cases, list) and valid_cases, f"{path} valid cases are required")
    require(isinstance(invalid_cases, list) and len(invalid_cases) >= 3, f"{path} invalid cases must include at least 3 fixtures")
    seen_ids: set[str] = set()
    seen_signals: set[str] = set()
    for case in valid_cases:
        require(isinstance(case, dict), f"{path} valid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid valid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith(".svg"), f"{path} {case_id} fixture must be an SVG path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        required_signals = case.get("signals")
        require(isinstance(required_signals, list) and required_signals, f"{path} {case_id} signals are required")
        actual_signals = interaction_accessibility_signal_set(fixture_path)
        for signal in required_signals:
            require(isinstance(signal, str) and signal, f"{path} {case_id} invalid signal")
            require(signal in actual_signals, f"{fixture_path} missing interaction accessibility signal: {signal}")
            seen_signals.add(signal)
    for case in invalid_cases:
        require(isinstance(case, dict), f"{path} invalid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid invalid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith(".svg"), f"{path} {case_id} fixture must be an SVG path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        expected = case.get("expectedFailure")
        require(isinstance(expected, str) and expected.strip(), f"{path} {case_id} expectedFailure is required")
        output = run_interaction_accessibility_expect_failure(fixture_path)
        require(expected in output, f"{path} {case_id} expected failure not found: {expected}")
    missing_signals = sorted({"namedControls", "keyboardAccess", "safePromptPlacement", "safePromptEscaping"} - seen_signals)
    require(not missing_signals, f"{path} missing interaction accessibility signal coverage: {missing_signals}")
    ok(f"Interaction accessibility case checks passed: {path}")


def run_escaping_safety_expect_failure(fixture_path: Path) -> str:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            validate_escaping_safety_asset(fixture_path)
    except SystemExit as exc:
        output = buffer.getvalue()
        require(exc.code != 0, f"{fixture_path} escaping-safety validator exited successfully when failure was expected")
        require("[FAIL]" in output, f"{fixture_path} escaping-safety validator did not emit a failure")
        return output
    fail(f"{fixture_path} passed escaping-safety validation; expected failure")


def validate_escaping_safety_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    valid_cases = data.get("valid")
    invalid_cases = data.get("invalid")
    require(isinstance(valid_cases, list) and valid_cases, f"{path} valid cases are required")
    require(isinstance(invalid_cases, list) and len(invalid_cases) >= 3, f"{path} invalid cases must include at least 3 fixtures")
    seen_ids: set[str] = set()
    seen_signals: set[str] = set()
    for case in valid_cases:
        require(isinstance(case, dict), f"{path} valid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid valid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith((".svg", ".html")), f"{path} {case_id} fixture must be an SVG or HTML path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        required_signals = case.get("signals")
        require(isinstance(required_signals, list) and required_signals, f"{path} {case_id} signals are required")
        actual_signals = escaping_safety_signal_set(fixture_path)
        for signal in required_signals:
            require(isinstance(signal, str) and signal, f"{path} {case_id} invalid signal")
            require(signal in actual_signals, f"{fixture_path} missing escaping safety signal: {signal}")
            seen_signals.add(signal)
    for case in invalid_cases:
        require(isinstance(case, dict), f"{path} invalid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid invalid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith((".svg", ".html")), f"{path} {case_id} fixture must be an SVG or HTML path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        expected = case.get("expectedFailure")
        require(isinstance(expected, str) and expected.strip(), f"{path} {case_id} expectedFailure is required")
        output = run_escaping_safety_expect_failure(fixture_path)
        require(expected in output, f"{path} {case_id} expected failure not found: {expected}")
    missing_signals = sorted({"xmlEntities", "safeHtmlText", "safeInlineHandlers"} - seen_signals)
    require(not missing_signals, f"{path} missing escaping safety signal coverage: {missing_signals}")
    ok(f"Escaping safety case checks passed: {path}")


def run_production_html_contract_expect_failure(fixture_path: Path, html_type: str) -> str:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            validate_production_html_contract_asset(fixture_path, html_type)
    except SystemExit as exc:
        output = buffer.getvalue()
        require(exc.code != 0, f"{fixture_path} production-html validator exited successfully when failure was expected")
        require("[FAIL]" in output, f"{fixture_path} production-html validator did not emit a failure")
        return output
    fail(f"{fixture_path} passed production HTML contract validation; expected failure")


def validate_production_html_contract_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    valid_cases = data.get("valid")
    invalid_cases = data.get("invalid")
    require(isinstance(valid_cases, list) and valid_cases, f"{path} valid cases are required")
    require(isinstance(invalid_cases, list) and len(invalid_cases) >= 3, f"{path} invalid cases must include at least 3 fixtures")
    seen_ids: set[str] = set()
    seen_types: set[str] = set()
    seen_signals: set[str] = set()
    for case in valid_cases:
        require(isinstance(case, dict), f"{path} valid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid valid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        html_type = case.get("type")
        require(html_type in {"walkthrough", "module_grid"}, f"{path} {case_id} invalid type: {html_type}")
        seen_types.add(str(html_type))
        require(isinstance(fixture, str) and fixture.endswith(".html"), f"{path} {case_id} fixture must be an HTML path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        required_signals = case.get("signals")
        require(isinstance(required_signals, list) and required_signals, f"{path} {case_id} signals are required")
        actual_signals = production_html_contract_signal_set(fixture_path, str(html_type))
        for signal in required_signals:
            require(isinstance(signal, str) and signal, f"{path} {case_id} invalid signal")
            require(signal in actual_signals, f"{fixture_path} missing production HTML contract signal: {signal}")
            seen_signals.add(signal)
    for case in invalid_cases:
        require(isinstance(case, dict), f"{path} invalid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid invalid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        html_type = case.get("type")
        require(html_type in {"walkthrough", "module_grid"}, f"{path} {case_id} invalid type: {html_type}")
        require(isinstance(fixture, str) and fixture.endswith(".html"), f"{path} {case_id} fixture must be an HTML path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        expected = case.get("expectedFailure")
        require(isinstance(expected, str) and expected.strip(), f"{path} {case_id} expectedFailure is required")
        output = run_production_html_contract_expect_failure(fixture_path, str(html_type))
        require(expected in output, f"{path} {case_id} expected failure not found: {expected}")
    require(seen_types == {"walkthrough", "module_grid"}, f"{path} must cover walkthrough and module_grid production HTML")
    required_signals = {"accessibleHeading", "safeHtml", "reducedMotion", "responsiveControls", "embeddedSvgA11y", "responsiveGrid", "hostTokens", "actionButtons"}
    missing_signals = sorted(required_signals - seen_signals)
    require(not missing_signals, f"{path} missing production HTML contract signal coverage: {missing_signals}")
    ok(f"Production HTML contract case checks passed: {path}")


def run_render_surface_expect_failure(fixture_path: Path, html_type: str) -> str:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            validate_render_surface_asset(fixture_path, html_type)
    except SystemExit as exc:
        output = buffer.getvalue()
        require(exc.code != 0, f"{fixture_path} render-surface validator exited successfully when failure was expected")
        require("[FAIL]" in output, f"{fixture_path} render-surface validator did not emit a failure")
        return output
    fail(f"{fixture_path} passed render surface validation; expected failure")


def validate_render_surface_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    valid_cases = data.get("valid")
    invalid_cases = data.get("invalid")
    require(isinstance(valid_cases, list) and valid_cases, f"{path} valid cases are required")
    require(isinstance(invalid_cases, list) and len(invalid_cases) >= 3, f"{path} invalid cases must include at least 3 fixtures")
    seen_ids: set[str] = set()
    seen_types: set[str] = set()
    seen_signals: set[str] = set()
    for case in valid_cases:
        require(isinstance(case, dict), f"{path} valid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid valid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        html_type = case.get("type")
        require(html_type in {"walkthrough", "module_grid"}, f"{path} {case_id} invalid type: {html_type}")
        seen_types.add(str(html_type))
        require(isinstance(fixture, str) and fixture.endswith(".html"), f"{path} {case_id} fixture must be an HTML path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        required_signals = case.get("signals")
        require(isinstance(required_signals, list) and required_signals, f"{path} {case_id} signals are required")
        actual_signals = render_surface_signal_set(fixture_path, str(html_type))
        for signal in required_signals:
            require(isinstance(signal, str) and signal, f"{path} {case_id} invalid signal")
            require(signal in actual_signals, f"{fixture_path} missing render surface signal: {signal}")
            seen_signals.add(signal)
    for case in invalid_cases:
        require(isinstance(case, dict), f"{path} invalid case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid invalid-case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        html_type = case.get("type")
        require(html_type in {"walkthrough", "module_grid"}, f"{path} {case_id} invalid type: {html_type}")
        require(isinstance(fixture, str) and fixture.endswith(".html"), f"{path} {case_id} fixture must be an HTML path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        expected = case.get("expectedFailure")
        require(isinstance(expected, str) and expected.strip(), f"{path} {case_id} expectedFailure is required")
        output = run_render_surface_expect_failure(fixture_path, str(html_type))
        require(expected in output, f"{path} {case_id} expected failure not found: {expected}")
    require(seen_types == {"walkthrough", "module_grid"}, f"{path} must cover walkthrough and module_grid render surfaces")
    required_signals = {"scalableSvg", "responsiveGrid", "controlTargetSize", "overflowProtection", "stableCards", "hostTokenFallback", "deterministicInitialState", "motionGuard"}
    missing_signals = sorted(required_signals - seen_signals)
    require(not missing_signals, f"{path} missing render surface signal coverage: {missing_signals}")
    ok(f"Render surface case checks passed: {path}")


def validate_renderer_contract_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list) and len(cases) >= 5, f"{path} cases must include at least 5 renderer contract checks")
    seen_ids: set[str] = set()
    checked_files: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        relative = case.get("file")
        require(isinstance(relative, str) and relative.strip(), f"{path} {case_id} file is required")
        target = root / relative
        require(target.exists(), f"{path} {case_id} missing contract file: {target}")
        checked_files.add(relative)
        fragments = case.get("requiredFragments")
        require(isinstance(fragments, list) and fragments, f"{path} {case_id} requiredFragments are required")
        text = target.read_text(encoding="utf-8")
        for fragment in fragments:
            require(isinstance(fragment, str) and fragment, f"{path} {case_id} invalid fragment")
            require(fragment in text, f"{relative} missing renderer contract fragment: {fragment}")
    require("prompts/svg_renderer.md" in checked_files, f"{path} must check renderer prompt contract")
    require("validators/repair_rules.md" in checked_files, f"{path} must check repair rules contract")
    require("templates/preview_svg.template.svg" in checked_files, f"{path} must check preview template contract")
    ok(f"Renderer contract checks passed: {path}")


def validate_repair_signal_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 5, f"{path} should include at least 5 repair-signal cases")

    negative = read_json(root / "tests/negative_visual_quality_cases.json")
    require(isinstance(negative, dict), "negative visual-quality cases must contain a JSON object")
    negative_cases = negative.get("cases")
    require(isinstance(negative_cases, list), "negative visual-quality cases must contain cases[]")
    negative_by_id = {case.get("id"): case for case in negative_cases if isinstance(case, dict)}

    repair_rules = (root / "validators/repair_rules.md").read_text(encoding="utf-8")
    repair_prompt = (root / "prompts/validator_repair.md").read_text(encoding="utf-8")
    seen_ids: set[str] = set()
    seen_source_cases: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        source_case = case.get("sourceCase")
        require(source_case in negative_by_id, f"{path} {case_id} sourceCase must reference a negative visual-quality case")
        seen_source_cases.add(str(source_case))
        negative_case = negative_by_id[source_case]
        for key in ["validator", "fixture"]:
            require(case.get(key) == negative_case.get(key), f"{path} {case_id} {key} must match negative visual-quality case")
        failure_signal = case.get("failureSignal")
        require(isinstance(failure_signal, str) and failure_signal.strip(), f"{path} {case_id} failureSignal is required")
        require(failure_signal == negative_case.get("expectedFailure"), f"{path} {case_id} failureSignal must match expectedFailure")
        repair_rule = case.get("repairRule")
        require(isinstance(repair_rule, str) and repair_rule.strip(), f"{path} {case_id} repairRule is required")
        require(repair_rule in repair_rules, f"{path} {case_id} repairRule missing from validators/repair_rules.md")
        require(failure_signal in repair_prompt, f"{path} {case_id} failureSignal missing from prompts/validator_repair.md")
        actions = case.get("repairActions")
        require(isinstance(actions, list) and len(actions) >= 2, f"{path} {case_id} needs at least two repairActions")
        for action in actions:
            require(isinstance(action, str) and action.strip(), f"{path} {case_id} repairAction must be non-empty")
        fixture_path = root / str(case.get("fixture"))
        output = run_validator_expect_failure(str(case.get("validator")), fixture_path)
        require(failure_signal in output, f"{path} {case_id} expected repair signal not emitted by validator")
    missing_sources = sorted(set(negative_by_id) - seen_source_cases)
    require(not missing_sources, f"{path} missing repair signal mappings for negative cases: {missing_sources}")
    ok(f"Repair signal checks passed: {path}")


def count_legend_swatches(text: str, height: int) -> int:
    count = 0
    for rect in re.finditer(r"<rect\b[^>]*>", text):
        attrs = parse_float_attrs(rect.group(0))
        if {"y", "width", "height"}.issubset(attrs):
            if 8 <= attrs["width"] <= 16 and 8 <= attrs["height"] <= 16 and attrs["y"] >= height - 120:
                count += 1
    return count


def score_readability_svg(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    try:
        svg = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"{path} XML parse error: {exc}")

    view_box = svg.attrib.get("viewBox", "")
    match = re.match(r"0\s+0\s+(680|690)\s+(\d+)", view_box)
    require(bool(match), f"{path} readability score requires a 680/690-wide viewBox")
    width = int(match.group(1))
    height = int(match.group(2))
    area = width * height

    visible_texts = [value.strip() for value in re.findall(r"<text\b[^>]*>([^<]+)</text>", text) if value.strip()]
    text_count = len(visible_texts)
    max_text_length = max((len(value) for value in visible_texts), default=0)
    avg_text_length = sum(len(value) for value in visible_texts) / text_count if text_count else 0.0
    rect_count = text.count("<rect")
    path_count = text.count("<path")
    clickable_count = text.count("onclick=")
    legend_swatches = count_legend_swatches(text, height)
    distinct_fills = len(set(re.findall(r'fill="rgb\(([^"]+)\)"', text)))
    has_label_protection = "<mask" in text or "rgba(222, 220, 209, 0.3)" in text
    has_interactions = "sendPrompt(" in text and clickable_count >= 1
    connector_ratio = path_count / max(text_count, 1)
    area_per_text = area / max(text_count, 1)

    score = 100
    penalties: list[str] = []

    def penalize(points: int, signal: str) -> None:
        nonlocal score
        score -= points
        penalties.append(signal)

    if text_count < 10:
        penalize(10, "too few text anchors for an infographic")
    if max_text_length > 48:
        penalize(30, "visible text exceeds stable SVG budget")
    elif max_text_length > 42:
        penalize(8, "visible text is close to the wrapping limit")
    if avg_text_length > 30:
        penalize(10, "average text length is too high")
    elif avg_text_length > 24:
        penalize(5, "average text length is high")
    if legend_swatches < 3:
        penalize(14, "legend coverage is weak")
    if distinct_fills < 4:
        penalize(14, "palette diversity is too narrow")
    if not has_label_protection:
        penalize(18, "connector labels lack protection")
    if not has_interactions:
        penalize(8, "interactive affordances are missing")
    if connector_ratio > 1.1:
        penalize(16, "connectors overwhelm text")
    elif connector_ratio > 0.75:
        penalize(8, "connector density is high")
    if area_per_text < 8000:
        penalize(10, "text density is too high for the canvas")
    elif area_per_text < 10000:
        penalize(5, "text density is high")
    if rect_count > 38 and height < 720:
        penalize(6, "framed element density is high")

    score = max(score, 0)
    signals = {
        "labelProtection": has_label_protection,
        "legend": legend_swatches >= 3,
        "palette": distinct_fills >= 4,
        "interactions": has_interactions,
        "textBudget": max_text_length <= 48 and avg_text_length <= 30,
        "balancedDensity": area_per_text >= 8000 and connector_ratio <= 1.1,
    }
    return {
        "score": score,
        "penalties": penalties,
        "signals": signals,
        "metrics": {
            "rects": rect_count,
            "paths": path_count,
            "texts": text_count,
            "maxTextLength": max_text_length,
            "avgTextLength": round(avg_text_length, 2),
            "legendSwatches": legend_swatches,
            "clickable": clickable_count,
            "distinctFills": distinct_fills,
            "connectorRatio": round(connector_ratio, 2),
            "areaPerText": round(area_per_text, 2),
        },
    }


def validate_readability_score_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    cases = data.get("cases")
    require(isinstance(cases, list), f"{path} cases must be an array")
    require(len(cases) >= 6, f"{path} should include at least 6 readability score cases")
    seen_ids: set[str] = set()
    seen_intents: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{path} case must be an object")
        case_id = case.get("id")
        require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
        require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
        seen_ids.add(case_id)
        fixture = case.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith(".svg"), f"{path} {case_id} fixture must be an SVG path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {case_id} missing fixture: {fixture_path}")
        layout_intent = case.get("layoutIntent")
        require(isinstance(layout_intent, str) and layout_intent.strip(), f"{path} {case_id} layoutIntent is required")
        seen_intents.add(layout_intent)
        min_score = case.get("minScore")
        require(isinstance(min_score, int) and 70 <= min_score <= 100, f"{path} {case_id} minScore must be 70 to 100")
        required_signals = case.get("requiredSignals")
        require(isinstance(required_signals, list) and required_signals, f"{path} {case_id} requiredSignals are required")

        validate_infographic_svg(fixture_path)
        validate_visual_quality_svg(fixture_path)
        result = score_readability_svg(fixture_path)
        score = result["score"]
        require(isinstance(score, int), f"{path} {case_id} score must be an integer")
        require(score >= min_score, f"{fixture_path} readability score is too low: {score} < {min_score}; penalties={result['penalties']}")
        signals = result.get("signals")
        require(isinstance(signals, dict), f"{path} {case_id} readability signals must be an object")
        for signal in required_signals:
            require(isinstance(signal, str) and signal, f"{path} {case_id} invalid required signal")
            require(signals.get(signal) is True, f"{fixture_path} missing readability signal: {signal}; metrics={result['metrics']}")

    require(len(seen_intents) >= 6, f"{path} should cover at least 6 layout intents for readability scoring")
    ok(f"Readability score checks passed: {path}")


def validate_pipeline_readability_score(path: Path) -> None:
    score = score_readability_svg(path)
    require(
        isinstance(score.get("score"), int) and score["score"] >= 75,
        f"{path} readability score is too low: {score}",
    )


PIPELINE_VALIDATORS = {
    "infographic_dsl": {"artifact": "dsl", "run": validate_infographic_dsl},
    "infographic_svg": {"artifact": "svg", "run": validate_infographic_svg},
    "visual_quality": {"artifact": "svg", "run": validate_visual_quality_svg},
    "readability_score": {"artifact": "svg", "run": validate_pipeline_readability_score},
    "text_fit": {"artifact": "svg", "run": validate_text_fit_svg},
    "escaping_safety": {"artifact": "rendered", "run": validate_escaping_safety_asset},
    "interaction_accessibility": {"artifact": "svg", "run": validate_interaction_accessibility_svg},
    "walkthrough_dsl": {"artifact": "dsl", "run": validate_walkthrough_dsl},
    "walkthrough_html": {"artifact": "html", "run": validate_walkthrough_html},
    "module_grid_dsl": {"artifact": "dsl", "run": validate_module_grid_dsl},
    "module_grid_html": {"artifact": "html", "run": validate_module_grid_html},
    "production_html_contract": {"artifact": "html", "run": validate_production_html_contract_inferred},
    "render_surface": {"artifact": "html", "run": validate_render_surface_inferred},
}


def run_pipeline_validators(validators: list[object], dsl_path: Path, svg_path: Path | None = None, html_path: Path | None = None) -> None:
    for validator_name in validators:
        require(isinstance(validator_name, str), "pipeline validator name must be a string")
    unknown_validators = sorted({name for name in validators if name not in PIPELINE_VALIDATORS})
    require(not unknown_validators, f"unknown pipeline validator: {unknown_validators}")
    for validator_name in validators:
        entry = PIPELINE_VALIDATORS[validator_name]
        artifact = entry["artifact"]
        if artifact == "dsl":
            target = dsl_path
        elif artifact == "svg":
            require(svg_path is not None, f"pipeline validator {validator_name} requires an SVG artifact")
            target = svg_path
        elif artifact == "html":
            require(html_path is not None, f"pipeline validator {validator_name} requires an HTML artifact")
            target = html_path
        elif artifact == "rendered":
            target = html_path if html_path is not None else svg_path
            require(target is not None, f"pipeline validator {validator_name} requires a rendered SVG or HTML artifact")
        else:
            fail(f"unknown pipeline validator artifact: {artifact}")
        entry["run"](target)


def validate_visual_snapshots(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    snapshots = data.get("snapshots")
    require(isinstance(snapshots, list), f"{path} snapshots must be an array")
    require(len(snapshots) >= 6, f"{path} should include at least 6 visual snapshots")
    seen_ids: set[str] = set()
    for snapshot in snapshots:
        require(isinstance(snapshot, dict), f"{path} snapshot must be an object")
        snapshot_id = snapshot.get("id")
        require(isinstance(snapshot_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", snapshot_id), f"{path} invalid snapshot id: {snapshot_id}")
        require(snapshot_id not in seen_ids, f"{path} duplicate snapshot id: {snapshot_id}")
        seen_ids.add(snapshot_id)
        fixture = snapshot.get("fixture")
        require(isinstance(fixture, str) and fixture.endswith(".svg"), f"{path} {snapshot_id} fixture must be an SVG path")
        fixture_path = root / fixture
        require(fixture_path.exists(), f"{path} {snapshot_id} missing fixture: {fixture_path}")
        text = fixture_path.read_text(encoding="utf-8")
        try:
            svg = ET.fromstring(text)
        except ET.ParseError as exc:
            fail(f"{fixture_path} XML parse error: {exc}")
        view_box = svg.attrib.get("viewBox", "")
        match = re.match(r"0\s+0\s+(680|690)\s+(\d+)", view_box)
        require(bool(match), f"{fixture_path} snapshot requires 680/690-wide viewBox")
        height = int(match.group(2))

        metrics = {
            "minRects": text.count("<rect"),
            "minPaths": text.count("<path"),
            "minTexts": text.count("<text"),
            "minLegendSwatches": count_legend_swatches(text, height),
            "minClickable": text.count("onclick="),
            "minDistinctFills": len(set(re.findall(r'fill="rgb\(([^"]+)\)"', text))),
        }
        for metric, actual in metrics.items():
            expected = snapshot.get(metric)
            require(isinstance(expected, int), f"{path} {snapshot_id} {metric} must be an integer")
            require(actual >= expected, f"{fixture_path} {metric} regressed: {actual} < {expected}")
        fragments = snapshot.get("requiredFragments")
        require(isinstance(fragments, list) and fragments, f"{path} {snapshot_id} requiredFragments are required")
        for fragment in fragments:
            require(isinstance(fragment, str) and fragment, f"{path} {snapshot_id} invalid fragment")
            require(fragment in text, f"{fixture_path} missing required visual fragment: {fragment}")
    ok(f"Visual snapshot checks passed: {path}")


def validate_browser_render_metric_cases(path: Path, root: Path) -> None:
    data = read_json(path)
    require(isinstance(data, dict), f"{path} must contain a JSON object")
    valid_cases = data.get("valid")
    invalid_cases = data.get("invalid")
    require(isinstance(valid_cases, list) and len(valid_cases) >= 2, f"{path} valid cases must include walkthrough and module grid")
    require(isinstance(invalid_cases, list) and len(invalid_cases) >= 3, f"{path} invalid cases must include at least 3 browser metric fixtures")
    seen_ids: set[str] = set()
    seen_types: set[str] = set()
    seen_assertions: set[str] = set()
    for group_name, cases in [("valid", valid_cases), ("invalid", invalid_cases)]:
        for case in cases:
            require(isinstance(case, dict), f"{path} {group_name} case must be an object")
            case_id = case.get("id")
            require(isinstance(case_id, str) and re.match(r"^[a-z][a-z0-9_-]*$", case_id), f"{path} invalid case id: {case_id}")
            require(case_id not in seen_ids, f"{path} duplicate case id: {case_id}")
            seen_ids.add(case_id)
            html_type = case.get("type")
            require(html_type in {"walkthrough", "module_grid"}, f"{path} {case_id} invalid type: {html_type}")
            seen_types.add(str(html_type))
            fixture = case.get("fixture")
            require(isinstance(fixture, str) and fixture.endswith(".html"), f"{path} {case_id} fixture must be an HTML path")
            require((root / fixture).exists(), f"{path} {case_id} missing fixture: {fixture}")
            viewports = case.get("viewports")
            require(isinstance(viewports, list) and viewports, f"{path} {case_id} viewports are required")
            for viewport in viewports:
                require(isinstance(viewport, int) and 320 <= viewport <= 1200, f"{path} {case_id} viewport is invalid: {viewport}")
            assertions = case.get("assertions", [])
            if assertions:
                require(isinstance(assertions, list), f"{path} {case_id} assertions must be an array")
                for assertion in assertions:
                    require(isinstance(assertion, str) and assertion, f"{path} {case_id} invalid assertion")
                    seen_assertions.add(assertion)
            if group_name == "invalid":
                expected = case.get("expectedFailure")
                require(isinstance(expected, str) and expected.strip(), f"{path} {case_id} expectedFailure is required")
    require(seen_types == {"walkthrough", "module_grid"}, f"{path} must cover walkthrough and module_grid browser metrics")
    required_assertions = {"noHorizontalOverflow", "svgVisible", "singleActiveStep", "clickTargets", "cardsVisible"}
    missing_assertions = sorted(required_assertions - seen_assertions)
    require(not missing_assertions, f"{path} missing browser metric assertion coverage: {missing_assertions}")
    ok(f"Browser render metric case checks passed: {path}")


def validate_browser_render_metric_script(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required_fragments = [
        "remote-debugging-port",
        "webSocketDebuggerUrl",
        "Runtime.evaluate",
        "Emulation.setDeviceMetricsOverride",
        "getBoundingClientRect",
        "scrollWidth",
        "click target",
        "horizontal overflow",
        "single active step",
        "CHROME_PATH",
    ]
    for fragment in required_fragments:
        require(fragment in text, f"{path} missing browser metric script fragment: {fragment}")
    require("playwright" not in text.lower() and "puppeteer" not in text.lower(), f"{path} should not require browser automation packages")
    ok(f"Browser render metric script checks passed: {path}")


def validate_manifest(root: Path, required_paths: list[str]) -> None:
    manifest_path = root / "MANIFEST.txt"
    lines = [
        line.strip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    entries = set(lines)
    require(len(lines) == len(entries), "MANIFEST.txt contains duplicate entries")
    expected_entries = set(required_paths) | {
        "CHANGELOG.md",
        "README.zh-CN.md",
        "MANIFEST.txt",
        "tests/invalid_rect_overflow.svg",
    }
    for relative in sorted(expected_entries):
        require(relative in entries, f"MANIFEST.txt missing required entry: {relative}")
    for relative in lines:
        require((root / relative).exists(), f"MANIFEST.txt lists missing file: {relative}")
    ok("Manifest checks passed")


def validate_package(root: Path) -> None:
    required_paths = [
        "SKILL.md",
        "README.md",
        "docs/production-checklist.md",
        "skill.json",
        "schemas/flow-dsl.schema.json",
        "schemas/architecture-map.schema.json",
        "schemas/agentic-pipeline.schema.json",
        "schemas/infographic.schema.json",
        "schemas/knowledge-map.schema.json",
        "schemas/legacy-to-infographic-map.json",
        "schemas/module-grid.schema.json",
        "schemas/phased-pipeline.schema.json",
        "schemas/system-loop.schema.json",
        "schemas/walkthrough.schema.json",
        "schemas/layout.schema.json",
        "scripts/run_repair_signal_fixture.py",
        "scripts/run_pipeline_fixture.py",
        "scripts/check_browser_render_metrics.mjs",
        "scripts/validate_svg.py",
        "locales/signals.json",
        "templates/embedded_svg.template.svg",
        "templates/host_css.template.css",
        "templates/html_preview.template.html",
        "templates/infographic-templates.json",
        "templates/preview_svg.template.svg",
        "tests/browser_render_metric_cases.json",
        "tests/input_quality_cases.json",
        "tests/escaping_safety_cases.json",
        "tests/interaction_accessibility_cases.json",
        "tests/test_cases.json",
        "tests/unknown_infographic_cases.json",
        "tests/v2_e2e_cases.json",
        "tests/negative_visual_quality_cases.json",
        "tests/production_html_contract_cases.json",
        "tests/render_surface_cases.json",
        "tests/negative_pipeline_cases.json",
        "tests/production_pipeline_cases.json",
        "tests/primitive_coverage_cases.json",
        "tests/readability_score_cases.json",
        "tests/repair_signal_cases.json",
        "tests/renderer_contract_cases.json",
        "tests/template_selection_cases.json",
        "tests/text_fit_cases.json",
        "tests/visual_snapshot_baselines.json",
        "examples/arabic_text_fit.svg",
        "examples/chinese_text_fit.svg",
        "examples/search_flow.dsl.json",
        "examples/search_flow.output.svg",
    ]
    for relative in required_paths:
        require((root / relative).exists(), f"missing required file: {relative}")

    validate_manifest(root, required_paths)
    validate_skill_markdown(root / "SKILL.md")
    validate_skill_json(root / "skill.json", root / "CHANGELOG.md")
    read_json(root / "schemas/flow-dsl.schema.json")
    read_json(root / "schemas/architecture-map.schema.json")
    read_json(root / "schemas/agentic-pipeline.schema.json")
    read_json(root / "schemas/infographic.schema.json")
    read_json(root / "schemas/knowledge-map.schema.json")
    validate_legacy_mapping(root / "schemas/legacy-to-infographic-map.json")
    validate_template_catalog(root / "templates/infographic-templates.json")
    read_json(root / "schemas/module-grid.schema.json")
    read_json(root / "schemas/phased-pipeline.schema.json")
    read_json(root / "schemas/system-loop.schema.json")
    read_json(root / "schemas/walkthrough.schema.json")
    read_json(root / "schemas/layout.schema.json")
    validate_locale_signals(root / "locales/signals.json")
    validate_input_quality_cases(root / "tests/input_quality_cases.json")
    validate_escaping_safety_cases(root / "tests/escaping_safety_cases.json", root)
    validate_interaction_accessibility_cases(root / "tests/interaction_accessibility_cases.json", root)
    validate_test_cases(root / "tests/test_cases.json")
    validate_unknown_infographic_cases(root / "tests/unknown_infographic_cases.json", root)
    validate_e2e_cases(root / "tests/v2_e2e_cases.json", root)
    validate_production_pipeline_cases(root / "tests/production_pipeline_cases.json", root)
    validate_primitive_coverage_cases(root / "tests/primitive_coverage_cases.json", root)
    validate_production_html_contract_cases(root / "tests/production_html_contract_cases.json", root)
    validate_render_surface_cases(root / "tests/render_surface_cases.json", root)
    validate_negative_pipeline_cases(root / "tests/negative_pipeline_cases.json", root)
    validate_negative_visual_quality(root / "tests/negative_visual_quality_cases.json", root)
    validate_repair_signal_cases(root / "tests/repair_signal_cases.json", root)
    validate_renderer_contract_cases(root / "tests/renderer_contract_cases.json", root)
    validate_template_selection_cases(root / "tests/template_selection_cases.json")
    validate_text_fit_cases(root / "tests/text_fit_cases.json", root)
    validate_readability_score_cases(root / "tests/readability_score_cases.json", root)
    validate_visual_snapshots(root / "tests/visual_snapshot_baselines.json", root)
    validate_browser_render_metric_cases(root / "tests/browser_render_metric_cases.json", root)
    validate_host_css(root / "templates/host_css.template.css")
    validate_browser_render_metric_script(root / "scripts/check_browser_render_metrics.mjs")
    validate_pipeline_helper(root / "scripts/run_pipeline_fixture.py")
    validate_validator_maintainability(root / "scripts/validate_svg.py")
    validate_prompt_guidance(root)
    validate_production_docs(root)
    validate_production_svg_contract(root)
    validate_visual_quality(root)
    validate_coverage(root)
    validate_i18n(root)
    for dsl_path in sorted((root / "examples").glob("*.dsl.json")):
        validate_flow_dsl(dsl_path)
    for svg_path in sorted((root / "examples").glob("*.output.svg")):
        validate_svg(svg_path)
    for svg_path in sorted((root / "examples").glob("*.interactive.svg")):
        if "infographic" in svg_path.name:
            validate_infographic_svg(svg_path)
        elif "architecture" in svg_path.name:
            validate_architecture_svg(svg_path)
        elif "phased_pipeline" in svg_path.name:
            validate_phased_pipeline_svg(svg_path)
        elif "agentic" in svg_path.name:
            validate_agentic_pipeline_svg(svg_path)
        elif "system_loop" in svg_path.name:
            validate_system_loop_svg(svg_path)
        else:
            validate_interactive_svg(svg_path)
    for html_path in sorted((root / "examples").glob("*.walkthrough.html")):
        validate_walkthrough_html(html_path)
    for html_path in sorted((root / "examples").glob("*.module_grid.html")):
        validate_module_grid_html(html_path)
    ok(f"Package checks passed: {root}")


def validate_release_check(root: Path) -> None:
    validate_package(root)
    ok(f"Release checks passed: {root}")


def command_knowledge_map(root: Path) -> None:
    for path in sorted((root / "examples").glob("*knowledge_map.dsl.json")):
        validate_knowledge_map_dsl(path)
    for path in sorted((root / "examples").glob("*knowledge_map.interactive.svg")):
        validate_interactive_svg(path)
    ok("Knowledge map checks passed")


def command_architecture_map(root: Path) -> None:
    for path in sorted((root / "examples").glob("*architecture.dsl.json")):
        validate_architecture_map_dsl(path)
    for path in sorted((root / "examples").glob("*architecture.interactive.svg")):
        validate_architecture_svg(path)
    ok("Architecture map checks passed")


def command_walkthrough(root: Path) -> None:
    for path in sorted((root / "examples").glob("*walkthrough.dsl.json")):
        validate_walkthrough_dsl(path)
    for path in sorted((root / "examples").glob("*.walkthrough.html")):
        validate_walkthrough_html(path)
    ok("Walkthrough checks passed")


def command_system_loop(root: Path) -> None:
    for path in sorted((root / "examples").glob("*system_loop.dsl.json")):
        validate_system_loop_dsl(path)
    for path in sorted((root / "examples").glob("*system_loop.interactive.svg")):
        validate_system_loop_svg(path)
    ok("System loop checks passed")


def command_module_grid(root: Path) -> None:
    for path in sorted((root / "examples").glob("*module_grid.dsl.json")):
        validate_module_grid_dsl(path)
    for path in sorted((root / "examples").glob("*.module_grid.html")):
        validate_module_grid_html(path)
    ok("Module grid checks passed")


def command_agentic_pipeline(root: Path) -> None:
    for path in sorted((root / "examples").glob("*agentic*.dsl.json")):
        validate_agentic_pipeline_dsl(path)
    for path in sorted((root / "examples").glob("*agentic*.interactive.svg")):
        validate_agentic_pipeline_svg(path)
    ok("Agentic pipeline checks passed")


def command_phased_pipeline(root: Path) -> None:
    for path in sorted((root / "examples").glob("*phased_pipeline.dsl.json")):
        validate_phased_pipeline_dsl(path)
    for path in sorted((root / "examples").glob("*phased_pipeline.interactive.svg")):
        validate_phased_pipeline_svg(path)
    ok("Phased pipeline checks passed")


def command_infographic(root: Path) -> None:
    seen_intents: set[str] = set()
    for path in sorted((root / "examples").glob("*infographic.dsl.json")):
        validate_infographic_dsl(path)
        data = read_json(path)
        if isinstance(data, dict) and isinstance(data.get("layout"), dict):
            intent = data["layout"].get("intent")
            if isinstance(intent, str):
                seen_intents.add(intent)
    for path in sorted((root / "examples").glob("*infographic.interactive.svg")):
        validate_infographic_svg(path)
    missing_intents = sorted({"hub_spoke", "comparison", "hierarchy", "dashboard"} - seen_intents)
    require(not missing_intents, f"Infographic examples missing key layout intents: {missing_intents}")
    ok("Infographic checks passed")


def command_negative_visual_quality(root: Path) -> None:
    validate_negative_visual_quality(root / "tests/negative_visual_quality_cases.json", root)


def command_input_quality(root: Path) -> None:
    validate_input_quality_cases(root / "tests/input_quality_cases.json")


def command_unknown_infographic(root: Path) -> None:
    validate_unknown_infographic_cases(root / "tests/unknown_infographic_cases.json", root)


def command_pipeline_fixtures(root: Path) -> None:
    validate_production_pipeline_cases(root / "tests/production_pipeline_cases.json", root)


def command_primitive_coverage(root: Path) -> None:
    validate_primitive_coverage_cases(root / "tests/primitive_coverage_cases.json", root)


def command_template_selection(root: Path) -> None:
    validate_template_selection_cases(root / "tests/template_selection_cases.json")


def command_text_fit(root: Path) -> None:
    validate_text_fit_cases(root / "tests/text_fit_cases.json", root)


def command_interaction_accessibility(root: Path) -> None:
    validate_interaction_accessibility_cases(root / "tests/interaction_accessibility_cases.json", root)


def command_escaping_safety(root: Path) -> None:
    validate_escaping_safety_cases(root / "tests/escaping_safety_cases.json", root)


def command_renderer_contract(root: Path) -> None:
    validate_renderer_contract_cases(root / "tests/renderer_contract_cases.json", root)


def command_production_svg_contract(root: Path) -> None:
    validate_production_svg_contract(root)


def command_production_html_contract(root: Path) -> None:
    validate_production_html_contract_cases(root / "tests/production_html_contract_cases.json", root)


def command_render_surface(root: Path) -> None:
    validate_render_surface_cases(root / "tests/render_surface_cases.json", root)


def command_negative_pipeline(root: Path) -> None:
    validate_negative_pipeline_cases(root / "tests/negative_pipeline_cases.json", root)


def command_repair_signals(root: Path) -> None:
    validate_repair_signal_cases(root / "tests/repair_signal_cases.json", root)


def command_readability_score(root: Path) -> None:
    validate_readability_score_cases(root / "tests/readability_score_cases.json", root)


def command_visual_snapshots(root: Path) -> None:
    validate_visual_snapshots(root / "tests/visual_snapshot_baselines.json", root)


COMMAND_HANDLERS = {
    "--knowledge-map": command_knowledge_map,
    "--architecture-map": command_architecture_map,
    "--walkthrough": command_walkthrough,
    "--system-loop": command_system_loop,
    "--module-grid": command_module_grid,
    "--agentic-pipeline": command_agentic_pipeline,
    "--phased-pipeline": command_phased_pipeline,
    "--infographic": command_infographic,
    "--visual-quality": validate_visual_quality,
    "--negative-visual-quality": command_negative_visual_quality,
    "--input-quality": command_input_quality,
    "--unknown-infographic": command_unknown_infographic,
    "--pipeline-fixtures": command_pipeline_fixtures,
    "--primitive-coverage": command_primitive_coverage,
    "--template-selection": command_template_selection,
    "--text-fit": command_text_fit,
    "--escaping-safety": command_escaping_safety,
    "--interaction-accessibility": command_interaction_accessibility,
    "--renderer-contract": command_renderer_contract,
    "--production-svg-contract": command_production_svg_contract,
    "--production-html-contract": command_production_html_contract,
    "--render-surface": command_render_surface,
    "--negative-pipeline": command_negative_pipeline,
    "--repair-signals": command_repair_signals,
    "--readability-score": command_readability_score,
    "--visual-snapshots": command_visual_snapshots,
    "--release-check": validate_release_check,
    "--i18n": validate_i18n,
    "--coverage": validate_coverage,
    "--package": validate_package,
}


def print_usage() -> None:
    print("Usage: validate_svg.py path/to/file.svg")
    print("       validate_svg.py path/to/flow.dsl.json")
    for command in COMMAND_HANDLERS:
        print(f"       validate_svg.py {command} path/to/skill")


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] in COMMAND_HANDLERS:
        COMMAND_HANDLERS[sys.argv[1]](Path(sys.argv[2]))
        return

    if len(sys.argv) == 2 and sys.argv[1].endswith(".json"):
        validate_flow_dsl(Path(sys.argv[1]))
        return

    if len(sys.argv) == 2:
        validate_svg(Path(sys.argv[1]))
        return

    print_usage()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
