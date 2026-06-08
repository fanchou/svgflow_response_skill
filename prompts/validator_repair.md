# Validator & Repair

Check SVG or HTML output and repair once before final output.

Universal infographic checklist:

1. The DSL uses `diagramType: infographic` unless a legacy renderer is required.
2. The DSL includes `canvas`, `content.nodes`, `content.edges`, and `layout.intent`.
3. `layout intent` is one of `linear`, `layered`, `loop`, `matrix`, `hub_spoke`, `timeline`, `swimlane`, `comparison`, `hierarchy`, `dashboard`, or `freeform`.
4. Every group, edge, step, and interaction references existing node ids.
5. Groups render behind member nodes.
6. Edge labels do not sit directly on top of connector strokes without a mask or label background.
7. Legends are present when colors, tones, line styles, or symbols carry repeated meaning.
8. Interactions are optional but must target existing nodes when present.
9. Source-language text and text direction are preserved.
10. Visible text snippets stay short enough for stable SVG cards.
11. Palette uses enough semantic tones for scanability.
12. Large group containers visibly contain child cards.
13. The output maintains a passing readability score across text budget, label protection, legend coverage, palette diversity, interaction affordances, and connector density.

Universal infographic repair signals:

| Failure signal | Required repair |
| --- | --- |
| `text is too long` | Replace prose with a short label, move details into subtitle, legend, or `sendPrompt`, and keep every visible `<text>` snippet short enough for a stable SVG card. |
| `compact legend` | Add at least two 8-16 px legend swatches near the bottom of the viewBox when color, tone, line style, or symbol semantics repeat. |
| `protect labels` | Add a mask gap around connector labels or place each label on a small background rect with `stroke="rgba(222, 220, 209, 0.3)"`. |
| `palette is too narrow` | Assign semantic tones by role and use at least four distinct official-style fill colors across nodes, labels, and legend swatches. |
| `clickable groups` | Move `sendPrompt(...)` onto the relevant module `<g onclick="...">`; never leave prompts detached in script tags or invisible elements. |
| `escaped prompt string` | Escape any quote that matches the JavaScript string delimiter before placing prompt text in `onclick` or `onkeydown`; keep pointer and keyboard handlers equivalent. |
| `readability score is too low` | Identify the failed dimension, then shorten visible text, reduce connector clutter, add label protection, add compact legends, improve palette separation, or attach missing clickable groups. |

Strict flowchart SVG checklist:

1. Starts with `<svg` and ends with `</svg>`.
2. No Markdown fences.
3. No XML declaration.
4. No comments.
5. viewBox width is 680.
6. No negative coordinates.
7. Height is sufficient.
8. Node count is at most 8.
9. Color classes are at most 3.
10. All text elements have class.
11. Node text has `dominant-baseline="central"`.
12. Paths have `fill="none"`.
13. Decision polygons do not hard-code fill or stroke.
14. Text escapes `&`, `<`, and `>`.
15. All tags are closed.
16. Root SVG has `xml:lang`, `lang`, and `dir`.

Official-style interactive SVG checklist:

1. Starts with `<svg` and ends with `</svg>`.
2. Contains `<title>` and `<desc>`.
3. viewBox width is 680.
4. Contains enough clickable modules when action prompts exist.
5. No rect or text coordinates exceed the viewBox.
6. Nested cards remain inside parent groups.

System-loop SVG checklist:

1. Contains at least two actor cards.
2. Contains at least three labeled signal paths.
3. Contains at least one bidirectional exchange when feedback exists.
4. Dashed secondary paths are used for deployment, calibration, or side feedback.
5. Label chips or masks keep text legible over connectors.
6. No ASCII control characters are present.

Module-grid HTML checklist:

1. Contains a visually hidden heading.
2. Uses CSS grid with a responsive one-column fallback.
3. Uses host design tokens for color and radius.
4. Contains 2 to 8 module cards.
5. Each card has title, subtitle, at least 3 detail items, and one CTA button.
6. Detail items include labels and semantic tones.
7. CTA buttons call `sendPrompt(...)`.
8. No ASCII control characters are present.
9. Browser render metrics pass with no horizontal overflow, visible cards, and CTA buttons sized as at least 32px click targets.
10. Cards use `min-width:0` and overflow protection for long labels.

Agentic-pipeline SVG checklist:

1. Contains entry, orchestrator, worker row, source row, synthesizer, and output.
2. Contains at least two worker/source pairs.
3. Contains dashed fan-out connectors.
4. Contains fan-in connectors to the synthesizer.
5. Contains a replanning loop when the source describes insufficient results or retry.
6. Supports viewBox width 680 or 690.
7. No ASCII control characters are present.

Phased-pipeline SVG checklist:

1. Contains a long vertical 680-wide viewBox.
2. Contains at least two phase containers.
3. Contains main spine nodes and connectors.
4. Contains at least two local phase flows.
5. Contains a legend when color semantics are used.
6. Contains side notes when the source includes auxiliary lifecycle calls.
7. No ASCII control characters are present.

Interactive walkthrough HTML checklist:

1. Contains a visually hidden heading.
2. Contains progress dots and previous/next controls.
3. Controls include `aria-label`.
4. The first step is active.
5. Every step has one valid SVG with `<title>` and `<desc>`.
6. Animations are inside `prefers-reduced-motion: no-preference`.
7. Step switching JavaScript updates active step, label, dots, and disabled state.
8. Browser render metrics pass with no horizontal overflow, visible scalable SVGs, a single active step, and previous/next controls sized as at least 32px click targets.
9. Embedded SVGs use `width="100%"` and controls use stable minimum dimensions.

If any issue is found, repair and then output the artifact.
