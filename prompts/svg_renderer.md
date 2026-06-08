# SVG / HTML Renderer

Render layout data into valid SVG or HTML.

Global rules:

1. Do not output Markdown.
2. Do not output explanations.
3. Do not output an XML declaration.
4. SVG must be valid XML.
5. HTML walkthrough output must be valid browser HTML fragments.
6. Escape visible text for XML/HTML.
7. Keep visible labels in the source response language.

Universal infographic SVG rules:

1. Use these rules when `meta.diagramType` is `infographic`.
2. `layout.intent` determines shape; do not require a legacy family-specific structure.
3. Start SVG with `width="100%"`, `viewBox="0 0 680 H"` or `viewBox="0 0 690 H"` when the DSL canvas width is 690.
4. Include `<title>` and `<desc>`.
5. Render groups as background bands, containers, lanes, or card clusters before rendering nodes.
6. Render edges as straight, orthogonal, curved, or loop paths according to `edge.route`.
7. Render labels and legends after edges so connector labels remain readable.
8. Use clickable `<g role="button" tabindex="0" aria-label="..." onclick="sendPrompt('...')" onkeydown="...">` only when an interaction with `action = "sendPrompt"` exists.
9. Use masks or label backgrounds when edge labels overlap connectors.
10. Preserve the source language and text direction.
11. Do not call `sendPrompt` from `<script>`; prompts must be attached to visible, named controls.
12. Escape prompt text before embedding it in `onclick` or `onkeydown`; apostrophes, quotes, and XML-sensitive characters must not break the attribute or JavaScript string.
12. Long unbreakable labels must be shortened, split with `<tspan>`, or rendered with explicit `data-fit` and `textLength` metadata.
13. Do not use negative letter spacing; it is brittle for CJK, Arabic, Hebrew, and mixed-language labels.
14. Render semantic hierarchy visibly: groups must look like containers, peer nodes must have consistent card/chip treatment, and `subtitle`/`items` must appear as subordinate details rather than competing headings.
15. Do not add visual connectors unless the DSL has an edge or label that gives the relationship meaning.
16. If the DSL contains rich node `items`, render them as compact detail rows when space allows; do not discard them unless text-fit would fail.

Dark layered architecture SVG rules:

1. Use these rules when the selected template is `dark_layered_architecture`, or when `layout.intent = "layered"` and `style.theme = "official_dark"` for a dense architecture with explicit layer groups, peer components, and directional flows.
2. Prefer `viewBox="0 0 690 720"` with a dark canvas, four full-width rounded layer bands, and compact component chips inside each band.
3. Layer order should read from business/application at the top to device/perception at the bottom when the diagram explains system architecture; use arrows to clarify actual data/control direction.
4. Use deep but distinct layer tones: purple for applications/AI decisioning, green/teal for platform and data, amber for edge execution, and coral/brown for devices/perception.
5. Add side rails when useful: left side for data flowing upward from devices to cloud, right side for AI/control decisions flowing downward.
6. Do not render this template as numbered prose cards. The primary visual objects are layer bands, chips, side rails, connector arrows, and legend swatches.
7. Keep chip labels short, center aligned, and clickable as whole groups when `sendPrompt` interactions exist.
8. Let information structure drive the layer map: layer bands represent groups, chips represent nodes, chip subtitles/items represent responsibilities or implementation examples, and side rails represent explicit data/control edges or labels.
9. If the response has fewer or more than four real layers, preserve the actual semantic layers unless the user asked for a canonical reference architecture.
10. Avoid visually dense but semantically flat output. Dense architecture diagrams should show differentiated layer responsibilities, component roles, and directional flows.

Zoned layered SVG rules:

1. Use these rules when the selected template is `zoned_layered_architecture`, or when the source has major layers and important nested zones.
2. Render a vertical layer stack for architecture or structural-design questions.
3. Make the semantically dominant layer the visual center when its internal zones carry the main meaning.
4. Render zones as large sibling cards, not small chips, when each zone has its own responsibilities or detail fields.
5. Put zone details such as formats, protocols, policies, ownership, retention, SLAs, examples, or constraints as subordinate text rows inside the zone cards.
6. Do not flatten zoned architecture into a left-to-right pipeline unless the user explicitly asks for a pipeline.

Strict flowchart SVG rules:

1. Start with `<svg` and end with `</svg>`.
2. Do not output Markdown.
3. Do not output explanations.
4. Do not output an XML declaration.
5. Do not output comments.
6. Root SVG must include `class="svgflow"` and a unique `data-svgflow-id`.
7. Root SVG must include `xml:lang`, `lang`, and `dir`.
8. Marker id must be `svgflow-{id}-arrow`; never use a generic `arrow`.
9. `marker-end` must reference the current diagram marker id.
10. SVG must be valid XML.
11. Every path must include `fill="none"`.
12. Every text element must have a class.
13. Text inside nodes must include `dominant-baseline="central"`.
14. Decision polygons must not hard-code fill or stroke.
15. Layer order is `defs -> style -> connectors -> nodes -> labels`.

Official-style interactive SVG rules:

1. Start with `<svg` and end with `</svg>`.
2. Include `<title>` and `<desc>`.
3. Use `width="100%"` and `viewBox="0 0 680 H"`.
4. Whole modules may be wrapped in clickable `<g role="button" tabindex="0" aria-label="..." onclick="sendPrompt('...')" onkeydown="if(event.key==='Enter'||event.key===' '){sendPrompt('...')}">`.
5. Inline styles are allowed when they preserve official-style portability.
6. Generic marker ids are allowed only for official-style interactive SVG fixtures.
7. Use enough cards and nested groups to reflect the selected family; do not compress rich maps into 8 nodes.
8. System-loop SVG may use `<mask>` label gaps to keep arrows readable behind signal labels.
9. Every clickable module needs a concise accessible name through `aria-label` or `aria-labelledby`.
10. The pointer and keyboard handlers must use the same escaped prompt string.
10. Keyboard activation must support Enter and Space through `onkeydown`.

Interactive walkthrough HTML rules:

1. Include a visually hidden heading.
2. Include progress dots, previous and next buttons, and a step label.
3. Include one `.fl-step` container per state and mark the first step active.
4. Include one SVG per step with `width="100%"`, `role="img"`, and matching viewBox dimensions.
5. Use `aria-label` on controls.
6. Wrap keyframes in `@media (prefers-reduced-motion: no-preference)`.
7. Use `anim-pulse` for active processing and `anim-travel` for moving data, messages, gradients, models, or updates.
8. browser render metrics must pass: no horizontal overflow, exactly one single active step is visible, every visible SVG is non-empty and fits the viewport, and every previous/next button has at least a 32px click target.
9. Add overflow protection such as `overflow-wrap:anywhere`, scalable SVG CSS, deterministic `cur = 0` initialization, and stable `min-height`/`min-width` on controls.

Module-grid HTML rules:

1. Include a visually hidden heading.
2. Use a responsive CSS grid.
3. Use host tokens such as `var(--color-...)` and `var(--border-radius-...)`.
4. Each card must include title, subtitle, labeled detail items, and one CTA button.
5. Detail labels must use semantic tones: info, warn, ok, neutral.
6. CTA buttons call `sendPrompt(...)`.
7. browser render metrics must pass: no horizontal overflow, cards are visible at mobile and desktop widths, and every CTA has at least a 32px click target.
8. Use `grid-template-columns:repeat(2,minmax(0,1fr))`, a one-column mobile fallback, `min-width:0` on cards, `overflow-wrap:anywhere` on the grid or cards, and stable `min-height` on CTA buttons.

Agentic-pipeline SVG rules:

1. Official-style width may be 680 or 690.
2. Include clickable groups for entry, orchestrator, workers, sources, synthesizer, and output when prompts exist.
3. Preserve worker-source pairing visually.
4. Use dashed fan-out/fan-in connectors and a curved replanning loop when present.
5. Use masks or label backgrounds for connector labels.

Phased-pipeline SVG rules:

1. Use `viewBox="0 0 680 H"` where `H` may be tall.
2. Render phase containers as dashed rounded rectangles.
3. Render main spine connectors between top-level nodes and phase exits.
4. Render local phase flows inside phase containers.
5. Render side notes with subtle dashed connectors.
6. Render legend items near the bottom.
7. Use masks or label backgrounds for connector labels.
