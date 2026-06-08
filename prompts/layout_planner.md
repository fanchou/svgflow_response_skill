# Layout Planner

Convert infographic DSL into deterministic layout data.

Default to universal infographic layout when the DSL uses `diagramType: infographic`. Use family-specific layouts only for legacy specialized DSLs.

Global rules:

1. viewBox width is fixed at 680.
2. Keep a safe margin of at least 40 px unless the family template explicitly uses tighter chips.
3. All rect, polygon, path, line, and text coordinates must stay inside the viewBox.
4. `H = max(bottom of all elements) + 40` for SVG outputs.
5. Avoid overlaps between text, connectors, and cards.
6. Keep repeated cards aligned to a visible grid.
7. Layout follows semantic structure. Do not choose geometry first and then force content into it. Use groups as actual semantic containers, nodes as peer modules, node subtitles/items as card details, and edges/labels as relationship evidence.
8. When the selected template is `dark_layered_architecture`, use a 690 x 720 canvas, a dark background, four full-width horizontal layer bands when the source supports four layers, compact chips inside each layer, a left data-flow rail, a right AI/control-flow rail, and legend swatches near the bottom.

Universal infographic layout:

1. Use `layout.intent` as the primary visual strategy.
2. `linear`: place nodes on a vertical or horizontal spine with optional branch labels.
3. `layered`: use full-width layer bands, nested groups, and subtle inter-layer arrows.
4. `loop`: place primary actors or states around a closed exchange with labeled feedback edges.
5. `matrix`: use responsive card grids with stable row and column spacing.
6. `hub_spoke`: place the central node near the upper or middle center, then fan out grouped peers and fan back when needed.
7. `timeline`: use chronological bands or milestone cards with consistent intervals.
8. `swimlane`: allocate one lane per actor/group and keep cross-lane connectors orthogonal.
9. `comparison`: use aligned columns or cards with the same internal structure for each option.
10. `hierarchy`: use parent-child trees or nested bands; avoid diagonal clutter when more than three levels exist.
11. `dashboard`: use metric cards, compact status groups, and a small legend; emphasize scan order over edge density.
12. `freeform`: preserve official-style custom composition while keeping all bounds and label gaps valid.
13. Derive visual hierarchy from semantic hierarchy: larger containers for groups, repeated card/chip scale for peer nodes, smaller text rows for `subtitle` and `items`.
14. Place connectors only where an edge expresses a real relationship; avoid decorative arrows that imply nonexistent causality or sequence.
15. Render groups before nodes; render edges below labels; render legends near the bottom or side.
16. Use masks or label backgrounds when labels sit on top of connectors.

Flowchart layout:

1. Main flow center x is 340.
2. Start y is 40.
3. Main action nodes use width 300 and height 44 or 56, with x = 190.
4. Start and end nodes use width 170 to 240, height 44, centered.
5. Decision nodes use diamonds with `cx = 340`, `halfWidth = 110`, and `halfHeight = 42`.
6. Main vertical gap is 32 px. Decision gaps may be 30 px.
7. Left failure branch uses x = 40 and width = 160.
8. Right exception branch uses x = 480 and width = 160.
9. Branch node center y aligns with the decision center y.
10. Loop routes use L-shaped paths and must not cross unrelated nodes.
11. Connectors must run from node boundary to node boundary.
12. Labels must be at least 8 px away from connectors.

Knowledge map layout:

1. Use a compact centered header.
2. Put paired introductory modules in a two-column row when there are two peers.
3. Use full-width bands for major sequential modules.
4. Use two-column or three-column card grids for summary principles.
5. Keep cards clickable as whole groups when `actionPrompt` exists.

Architecture map layout:

1. Use vertical layers from source/input to output/consumer.
2. Use large full-width layer bands for primary layers.
3. Put small chips inside or adjacent to layer bands for peer components.
4. Use a nested zone grid for storage zones or subdomains.
5. Use subtle arrows between layers when flow direction matters.

Interactive walkthrough layout:

1. Use one SVG per step with the same viewBox and stable card positions across steps.
2. Keep controls outside SVG: progress dots, previous button, next button, and step label.
3. Preserve stable dimensions so switching steps does not shift the page.
4. Animate connectors or active text only; do not animate layout geometry.

System loop layout:

1. Use a compact horizontal canvas, usually 680 x 320 to 520.
2. Place the primary actor on the left and environment/system on the right.
3. Put labeled signal chips between actors.
4. Use opposite-direction arrows for feedback and return signals.
5. Use dashed paths for deployment, calibration, optional feedback, or side channels.
6. Put guards or safety filters between the training loop and external device when present.
7. Use mask gaps or label backgrounds so connectors do not run through text.

Module grid layout:

1. Use a 2-column grid on desktop and a 1-column fallback on narrow screens.
2. Keep each card internally structured as title, subtitle, detail items, then CTA button.
3. Use stable spacing and borders so cards remain scannable.
4. Use semantic badges for item labels, not color alone.
5. Keep CTA buttons full-width when cards are narrow.

Agentic pipeline layout:

1. Use a vertical pipeline: entry, orchestrator, worker row, source row, synthesizer, output.
2. Use a 4-column worker/source grid when there are four workers; scale to 2 to 6 columns as needed.
3. Draw dashed fan-out connectors from orchestrator to workers.
4. Draw vertical connectors from each worker to its source.
5. Draw dashed fan-in connectors from sources to synthesizer.
6. Draw a curved dashed replanning loop from synthesizer back to orchestrator when needed.
7. Use mask gaps or label backgrounds so central labels remain legible.

Phased pipeline layout:

1. Use a long vertical canvas, usually 680 x 700 to 1400.
2. Keep the main spine centered.
3. Use dashed rounded phase containers around grouped phase nodes.
4. Allow local horizontal flows inside phase containers.
5. Place side notes near the related phase with subtle dashed connectors.
6. Place legend near the bottom and keep it inside the viewBox.
7. Use masks or label backgrounds for annotation labels over connectors.
