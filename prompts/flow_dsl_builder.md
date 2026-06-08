# Infographic DSL Builder

Convert parser output into the smallest DSL that preserves the response structure.

Default to the universal `diagramType: infographic` DSL for new work. Use legacy diagram families only when the user explicitly asks for one, a fixture requires compatibility, or the output needs a specialized HTML/SVG renderer that the universal model cannot yet express. Check `schemas/legacy-to-infographic-map.json` before selecting any legacy family.

Use `templates/infographic-templates.json` as a preset catalog. A template may set the initial `layout.intent`, expected primitives, node kinds, edge kinds, and renderer notes, but the output remains `diagramType = "infographic"`.

Rules:

1. Prefer `meta.diagramType = "infographic"` and select visual structure with `layout.intent`.
2. Generate a legacy `meta.diagramType` only when required: `flowchart`, `knowledge_map`, `architecture_map`, `interactive_walkthrough`, `system_loop`, `module_grid`, `agentic_pipeline`, or `phased_pipeline`.
3. `meta` must include `locale` and `textDirection`.
4. Use the source response's primary language for all visible labels and action prompts.
5. Use `ltr`, `rtl`, or `auto` for `textDirection`; use `rtl` for Arabic, Hebrew, Persian, and Urdu.
6. Do not invent core business logic or domain-specific components absent from the source response.
7. Keep titles concise; move extra detail into subtitles, details arrays, module items, or action prompts.
8. Treat the DSL as the semantic model, not a drawing sketch. A node exists because the response names a meaningful entity, capability, state, metric, risk, or output. A group exists because the response implies a real layer, actor, phase, category, zone, or option set. An edge exists because the response states or strongly implies a relationship verb.
9. Preserve hierarchy: groups hold major semantic containers, nodes hold peer modules inside those containers, and `items` hold implementation details or examples that should not become peer nodes.
10. Preserve directionality: use `kind = "data"`, `"control"`, `"feedback"`, or `"dependency"` to distinguish flow meaning instead of drawing every connector as a generic arrow.
11. Preserve the Structure Decision Record from the parser. If `not_the_structure` warns against a flat data-flow or prose-card layout, do not rebuild the DSL as that layout.
12. Every group, node, and edge must be backed by a source claim or synthesized source brief claim. If the evidence is only an example, protocol, tool, threshold, or adjective, make it an `item`, `subtitle`, `label`, or `legend` instead of a peer node.
13. Keep `promoted_claims` and `demoted_claims` consistent with the DSL. A promoted claim should have a visible primitive; a demoted claim should remain subordinate and should not reappear as an equal card.
14. If two candidate structures compete, encode only the highest-scoring organizing axis in `layout.intent`; express secondary axes through legends, badges, side labels, rails, or node items.
15. Preserve containment explicitly. When a node belongs to a group, set or imply that parent relationship through the group `members` list, node `parent`, or stable id naming. Do not rely on spatial proximity alone to communicate hierarchy.

Universal infographic rules:

1. Generate `meta`, `canvas`, `content`, `layout`, optional `style`, and optional `interactions`.
2. Use `content.nodes` for entities, actions, decisions, containers, metrics, notes, and outputs.
3. Use `content.groups` for layers, zones, phase containers, swimlanes, card clusters, and conceptual sections.
4. Use `content.edges` for process, data, control, dependency, and feedback relationships.
5. Use `content.labels` for callouts and annotation text that should not become a primary node.
6. Use `content.legends` when color, tone, line style, or symbol meaning spans multiple elements.
7. Use `content.steps` when the same content should be revealed as states.
8. Use `interactions` for `sendPrompt`, step switching, highlighting, or toggles.
9. Select one `layout.intent`: `linear`, `layered`, `loop`, `matrix`, `hub_spoke`, `timeline`, `swimlane`, `comparison`, `hierarchy`, `dashboard`, or `freeform`.
10. Keep the source semantics independent from layout; changing `layout.intent` should not require changing node ids.
11. Use `kind = "recommendation"` for options or suggested choices.
12. Use `kind = "risk"` for caveats, blockers, hazards, and failure-prone items.
13. Use `kind = "evidence"` for citations, proof points, observations, and source-backed claims.
14. Use `kind = "category"` for taxonomy or hierarchy nodes.
15. Use `kind = "media"` for image, icon, screenshot, or document placeholders that should be represented visually.
16. Use `layout.intent = "dashboard"` when metric cards are the main reading path.
17. For layered architectures, put layer responsibilities in group titles/subtitles or labels, put components in nodes, put examples/technologies in node `subtitle` or `items`, and put cross-layer movement in edges and labels.
18. For dense layered architectures with two-way or cross-cutting relationships, model only the categories present in the source: source/input layer, execution or processing layer, shared platform or service layer, output or application layer, upward data flow, downward control flow, feedback flow, and cross-cutting policy or governance.
19. For zoned layered architectures, model major lifecycle or architecture layers as groups and significant zones inside a layer as peer nodes. Put formats, retention windows, policies, SLAs, protocols, technologies, and examples into `subtitle` or `items`.
20. Do not add architecture parts just because a template usually has them. If a common component is absent from the response, omit it or keep it as a generic label only when the user explicitly requested a complete reference architecture.

Flowchart-specific rules:

1. Generate `meta`, `style`, `nodes`, and `edges`.
2. Use at most 8 nodes.
3. Decision nodes must be questions in the source language.
4. Failure branches default to `branch = left`.
5. Main success path uses `branch = main`.
6. Retry routes default to `route = loop-left` unless the layout needs `loop-right`.

Knowledge-map-specific rules:

1. Generate `meta`, `theme`, and `sections`.
2. Include `header`, `chapter_grid`, `summary_grid`, and `footer` when the source supports them.
3. Use `actionPrompt` for clickable drill-down modules.
4. Do not require a specific book, topic, or principle wording.

Architecture-map-specific rules:

1. Generate `meta`, `theme`, and `layers`.
2. Use `chip_row` for small peer components.
3. Use `zone_grid` for nested zones or grouped subareas.
4. Use `actionPrompt` for details the user may explore.

Walkthrough-specific rules:

1. Generate `meta`, `theme`, and `steps`.
2. Use 2 to 8 steps.
3. Use `animation = "travel"` for moving data or model updates.
4. Use `animation = "pulse"` for waiting, training, processing, or active state.
5. Use `animation = "pulse_travel"` when both are visible.

System-loop-specific rules:

1. Generate `meta`, `theme`, `actors`, `signals`, and optional `guards`.
2. Use 2 to 5 actors.
3. Include at least one bidirectional exchange when the source describes feedback.
4. Use `signals[].label` for action, state, reward, feedback, deployment, calibration, command, or observation labels.
5. Use dashed secondary signals for deployment, feedback, calibration, or optional paths.
6. Use guards for safety filters, validation layers, policy gates, or constraint checks.

Module-grid-specific rules:

1. Generate `meta` and `modules`.
2. Use 2 to 8 modules.
3. Each module needs title, subtitle, 3 to 8 labeled items, and one CTA action.
4. Use item tones: `info`, `warn`, `ok`, and `neutral`.
5. Preserve icon hints only when useful; icons are decorative and must not carry essential meaning alone.

Agentic-pipeline-specific rules:

1. Generate `meta`, `entry`, `orchestrator`, `workers`, `synthesizer`, `output`, and optional `loops`.
2. Use 2 to 6 workers.
3. Each worker must pair one agent with one knowledge source or tool source.
4. Use dashed fan-out connectors from orchestrator to workers.
5. Use fan-in connectors from sources back to synthesizer.
6. Include a dashed replanning loop when the source mentions insufficient results, retries, or re-routing.

Phased-pipeline-specific rules:

1. Generate `meta`, `spine`, `phases`, optional `sideNotes`, optional `legend`, and optional `footer`.
2. Use 3 to 12 spine nodes for the main vertical lifecycle.
3. Use 2 to 8 phases.
4. Each phase must contain at least one node.
5. Use `localFlows` for phase-internal horizontal or loopback flows.
6. Use `legend` when color semantics span multiple phases.

Do not generate SVG or HTML directly.
