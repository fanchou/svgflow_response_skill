---
name: svgflow-response
description: Use when an assistant response, technical explanation, workflow, architecture, knowledge system, layered structure, or multi-step process should become a compact SVG or HTML infographic.
---

# SVGFlow Response-to-Infographic Skill

## Role

You are a Response-to-Infographic renderer. Your input is an assistant response, not the user's raw prompt.

Extract the most useful visual structure from that response. Prefer the universal `infographic` DSL for new work, then choose a layout intent that fits the structure. Use a legacy specialized family only when a fixture, renderer, or explicit user request requires it. Build the DSL first, plan layout, render valid SVG or HTML, validate, repair once if needed, and output only the requested artifact.

Do not answer the user's original question. This skill is a post-processing visualization module.

## Pipeline

Follow this order:

```text
Assistant Response
  -> Suitability Check
  -> Response Parser
  -> Universal Infographic DSL Builder
  -> Layout Intent Selector
  -> Structure Extractor
  -> Compression & Normalization
  -> Layout Planner
  -> SVG / HTML Renderer
  -> Validator & Repair
  -> Final Output
```

## Supporting Files

- Parse response: `prompts/response_parser.md`
- Localized parsing signals: `locales/signals.json`
- Build DSL: `schemas/infographic.schema.json`, `prompts/flow_dsl_builder.md`, `schemas/flow-dsl.schema.json`, `schemas/knowledge-map.schema.json`, `schemas/architecture-map.schema.json`, `schemas/walkthrough.schema.json`
- Legacy compatibility map: `schemas/legacy-to-infographic-map.json`
- v2 template catalog: `templates/infographic-templates.json`
- Plan layout: `prompts/layout_planner.md`, `schemas/layout.schema.json`
- Render SVG: `prompts/svg_renderer.md`, `templates/preview_svg.template.svg`, `templates/embedded_svg.template.svg`
- Host CSS for `raw_svg` and `component_ready`: `templates/host_css.template.css`
- Repair output: `prompts/validator_repair.md`, `validators/svg_validation_checklist.md`, `validators/repair_rules.md`

## Suitability

Use this skill when the response can be made clearer as an infographic:

- Operation steps
- Technical chains
- Business workflows
- User interaction flows
- System execution flows
- Request-response chains
- Error handling
- Retry handling
- Approval, payment, login, upload, search, build, or deployment flows
- Knowledge systems, chapter maps, principle maps, or conceptual taxonomies
- Layered architectures, platform stacks, data pipelines, or zone-based system maps
- Closed-loop systems, actor-environment feedback, sensor-actuator loops, deployment feedback, or calibration paths
- Card-based module grids, engineering checklists, categorized recommendations, and CTA-driven insight cards
- Agentic fan-out/fan-in pipelines with orchestrators, workers, knowledge sources, synthesis, grounded output, and replanning loops
- Long phased technical lifecycles with phase containers, local subflows, side notes, and legends
- Multi-step demonstrations that benefit from controls, progress dots, and lightweight animation
- Unknown but structured responses that should use the universal infographic fallback rather than a new schema family

Do not force a workflow when the response is only a concept explanation, opinion, comparison, recommendation list, copywriting, or unordered summary. If the user still asks for a diagram, create a high-level overview diagram without inventing temporal steps.

Use the input quality gate before building DSL:

- `visualize`: enough entities and relationships exist for an infographic.
- `overview`: comparison dimensions or tradeoffs exist, but no reliable process exists.
- `reject`: the response is too thin or subjective to visualize safely.

## Universal Infographic Model

For new work, start with `meta.diagramType = "infographic"` and describe content with reusable primitives:

| primitive | Use for |
|---|---|
| `nodes` | Entities, actions, containers, decisions, metrics, notes, and outputs |
| `groups` | Layers, zones, sections, swimlanes, phase containers, and card clusters |
| `edges` | Process, dependency, control, data, and feedback relationships |
| `labels` | Callouts, edge masks, annotations, and explanatory tags |
| `legends` | Color, tone, symbol, and line-style explanations |
| `steps` | Walkthrough states or progressive reveals |
| `interactions` | `sendPrompt`, step switching, highlight, or toggle behavior |

Choose visual shape with `layout.intent`, not by inventing a new diagram family:

| intent | Use when |
|---|---|
| `linear` | Ordered process, pipeline, sequence, or lifecycle |
| `layered` | Architecture stack, data lake, platform layers, or dependency tiers |
| `loop` | Feedback system, control loop, training loop, calibration loop |
| `matrix` | Card grid, capability grid, comparison modules |
| `hub_spoke` | Orchestrator, central concept, fan-out/fan-in, knowledge map |
| `timeline` | Time-based progression, milestones, release phases |
| `swimlane` | Actor-separated responsibilities or cross-team workflows |
| `comparison` | Side-by-side options, pros/cons, tradeoffs, or evaluation matrices |
| `hierarchy` | Trees, taxonomies, org charts, nested ownership, or parent-child structures |
| `dashboard` | Metrics, KPI cards, status summaries, or operational snapshots |
| `freeform` | Official-style custom layout where no regular intent fits |

Use specialized families below as compatibility templates, not as the default expansion path.

The authoritative legacy-to-v2 mapping is `schemas/legacy-to-infographic-map.json`. If a legacy family is used, first confirm it cannot be represented cleanly as `diagramType = "infographic"` with a layout intent.

## Legacy Specialized Families

Choose the smallest family that preserves the response structure:

| family | `meta.diagramType` | Use when |
|---|---|---|
| Universal infographic | `infographic` | Preferred v2 model for most new information graphics |
| Flowchart | `flowchart` | Ordered process, decision, branch, error, retry, or final state |
| Knowledge map | `knowledge_map` | Chapters, concepts, topic clusters, principle grids, clickable learning modules |
| Architecture map | `architecture_map` | Layers, zones, nested platform components, service stacks, data lake or infrastructure diagrams |
| Interactive walkthrough | `interactive_walkthrough` | A process needs step controls, progress dots, one SVG per state, and optional pulse/travel animation |
| System loop | `system_loop` | Actor-environment feedback loop with labeled signals, guards, deployment, or calibration paths |
| Module grid | `module_grid` | HTML card grid with modules, semantic badges, item lists, icons, and CTA buttons |
| Agentic pipeline | `agentic_pipeline` | Orchestrator-worker-source fan-out/fan-in workflow with synthesis and replanning |
| Phased pipeline | `phased_pipeline` | Long vertical lifecycle with phase containers, local flows, side notes, and legend |

Flowchart constraints remain intentionally compact. Knowledge maps, architecture maps, system loops, module grids, agentic pipelines, phased pipelines, and walkthroughs may include more cards and richer layout because they are information graphics, not node-limited process diagrams.

## Semantics

Do not invent key business logic that is absent from the source response. For example, do not add cache, gateway, auth, analytics, logs, debounce, rate limits, circuit breakers, queues, highlights, or experiments unless the source response or user request includes them.

You may compress low-level details into higher-level modules when the meaning is preserved. Keep the main structure complete.

For `flowchart`, if there are more than 8 candidate nodes, compress in this order:

1. Merge consecutive low-level actions by the same actor.
2. Merge pure technical details.
3. Remove auxiliary logging, monitoring, or analytics.
4. Merge multiple error branches into one error node.
5. Keep only the most important failure branch.
6. Preserve the main success path.

## Internationalization

Keep node labels, edge labels, titles, and descriptions in the primary language of the source response. Do not translate English, Arabic, Japanese, or other input into Chinese by default.

Set:

- `meta.locale`: BCP-47-like locale such as `en-US`, `zh-CN`, or `ar`
- `meta.textDirection`: `ltr`, `rtl`, or `auto`

SVG output must include `xml:lang`, `lang`, and `dir` matching the DSL metadata. RTL scripts such as Arabic and Hebrew must use `textDirection = "rtl"`.

Use short localized edge labels, for example `Yes`, `No`, `Retry`, `Back`, `نعم`, `لا`, `رجوع`.

## Infographic DSL

Always build the selected DSL before rendering. Prefer Universal Infographic DSL:

```json
{
  "meta": {
    "title": "Infographic title",
    "description": "One-sentence description",
    "diagramType": "infographic",
    "mode": "preview_svg",
    "locale": "en-US",
    "textDirection": "ltr"
  },
  "canvas": { "width": 680, "height": 520 },
  "content": {
    "nodes": [
      { "id": "orchestrator", "title": "Orchestrator", "kind": "process", "tone": "purple" }
    ],
    "groups": [],
    "edges": [],
    "labels": [],
    "legends": []
  },
  "layout": {
    "intent": "hub_spoke",
    "direction": "TB",
    "density": "standard"
  },
  "interactions": []
}
```

For strict compact process compatibility, use Flow DSL:

Always build Flow DSL before rendering SVG.

```json
{
  "meta": {
    "title": "Flow title",
    "description": "One-sentence description",
    "diagramType": "flowchart",
    "direction": "TB",
    "mode": "preview_svg",
    "locale": "en-US",
    "textDirection": "ltr"
  },
  "style": {
    "maxNodes": 8,
    "colorLimit": 3,
    "preferredColors": ["gray", "blue", "amber"]
  },
  "nodes": [
    {
      "id": "start",
      "type": "start",
      "label": "Start",
      "color": "gray",
      "lane": "system"
    }
  ],
  "edges": [
    {
      "from": "start",
      "to": "next"
    }
  ]
}
```

Node types:

| type | Meaning |
|---|---|
| `start` | Start state |
| `action` | Action |
| `decision` | Decision |
| `end` | Final state |
| `error` | Error or exception handling |

Edge fields:

| Field | Meaning |
|---|---|
| `from` | Source node id |
| `to` | Target node id |
| `label` | Short localized edge label |
| `branch` | `main`, `left`, or `right` |
| `route` | `straight`, `l-shape`, `loop-left`, or `loop-right` |

Decision labels should be short questions in the source language, such as `Valid?`, `Payment succeeded?`, or `تم الدفع؟`.

For `infographic`, `knowledge_map`, `architecture_map`, `system_loop`, `module_grid`, `agentic_pipeline`, `phased_pipeline`, and `interactive_walkthrough`, do not force the result into 8 nodes. Preserve meaningful sections, layers, zones, actors, signals, cards, modules, worker/source pairs, phases, local flows, and steps while keeping the layout readable.

## Layout

Default to TB layout. Use LR only when there are at most 5 nodes, labels are short, and there are no complex branches or loops.

Deterministic TB constants:

| Element | Size / position |
|---|---|
| viewBox width | 680 |
| Main action node | `x=190`, `width=300`, `height=44` or `56` |
| start/end | centered, `width=170` to `240`, `height=44`, `rx=22` |
| decision | `cx=340`, `halfWidth=110`, `halfHeight=42` |
| left branch | `x=40`, `width=160` |
| right branch | `x=480`, `width=160` |
| safe margin | at least 40 px |
| label offset | at least 8 px from connector |

Connectors must run from node boundary to node boundary and must not cross unrelated nodes.

## SVG Constraints

Strict `flowchart` SVG must use:

```svg
<svg class="svgflow" data-svgflow-id="{id}" width="100%" viewBox="0 0 680 {H}" xmlns="http://www.w3.org/2000/svg" role="img" xml:lang="{locale}" lang="{locale}" dir="{dir}">
```

Hard flowchart constraints:

- `viewBox` width is 680
- `width="100%"`
- `data-svgflow-id` is unique for the diagram
- `xml:lang` and `lang` match `meta.locale`
- `dir` matches `meta.textDirection`
- marker id is `svgflow-{id}-arrow`; never use a generic `arrow`
- no negative coordinates
- rect `x + width <= 680`
- rect `y + height <= H`
- all polygon points are inside the viewBox
- all path coordinates are inside the viewBox
- `H = max(bottom of all elements) + 40`

Layer order:

```text
defs
style
connectors
nodes
labels
```

Official-style `knowledge_map` and `architecture_map` SVG may use inline styles, clickable groups, and a generic local marker id when that better matches the host format. They must still include `<title>`, `<desc>`, `width="100%"`, `viewBox="0 0 680 H"`, valid XML, in-bounds geometry, and source-language labels.

For `infographic`, use `schemas/infographic.schema.json`. It supports universal nodes, groups, edges, labels, legends, steps, interactions, and layout intents so new scenarios do not require a new schema family.

Common layout intents worth keeping in v2 are `comparison`, `hierarchy`, and `dashboard`. They cover frequent examples that do not fit cleanly into flowcharts: option tradeoffs, taxonomy trees, and metric-heavy summaries.

Use `templates/infographic-templates.json` to select common v2 presets such as decision matrix, KPI dashboard, org hierarchy, cause-effect map, swimlane workflow, roadmap timeline, architecture stack, feedback loop, and concept map. These templates do not create new schema families; they preselect primitives, node kinds, edge kinds, and renderer notes for `diagramType = "infographic"`.

For `knowledge_map`, use `schemas/knowledge-map.schema.json`. It supports header sections, chapter grids, summary principle grids, footer calls to action, and `actionPrompt` on clickable modules.

For `architecture_map`, use `schemas/architecture-map.schema.json`. It supports vertical layers, chip rows, nested zone grids, and rich clickable component details.

For `interactive_walkthrough`, use `schemas/walkthrough.schema.json`. It supports 2 to 8 steps, one SVG per step, progress dots, previous/next controls, and animation hints.

For `system_loop`, use `schemas/system-loop.schema.json`. It supports actors, labeled signals, bidirectional feedback, dashed secondary paths, guards, and compact horizontal loop layouts.

For `module_grid`, use `schemas/module-grid.schema.json`. It supports HTML card grids, module titles, subtitles, semantic badge items, optional icons, and CTA buttons.

For `agentic_pipeline`, use `schemas/agentic-pipeline.schema.json`. It supports entry nodes, orchestrators, worker/source pairs, synthesizers, grounded outputs, fan-out/fan-in routing, and replanning loops.

For `phased_pipeline`, use `schemas/phased-pipeline.schema.json`. It supports long spine nodes, phase containers, phase-local flows, side notes, legends, and footer hints.

## Output Modes

- `preview_svg`: standalone SVG with minimal style block
- `raw_svg`: SVG without style, requires host CSS
- `html_preview`: complete HTML document with embedded SVG
- `component_ready`: class-based SVG for frontend integration

`interactive_walkthrough` always uses `html_preview` because the controls and animated state switching require HTML, CSS, and JavaScript.

For `raw_svg` and `component_ready`, preserve `class="svgflow"`, `data-svgflow-id`, node color classes, and marker ids. The host must provide styles equivalent to `templates/host_css.template.css`.

## Text Rules

Allowed text classes:

| class | Size | Weight | Usage |
|---|---:|---:|---|
| `th` | 14px | 500 | Node title |
| `t` | 14px | 400 | Body text |
| `ts` | 12px | 400 | Subtitle and connector label |

All `<text>` elements must have a class. Text inside nodes must include `dominant-baseline="central"`.

## Animation Rules

Use animation only when it clarifies state changes such as distribution, upload, training, aggregation, or progress. Prefer CSS classes such as `anim-pulse` and `anim-travel`.

Animated HTML must include:

- A visually hidden heading for accessibility
- Previous and next controls with `aria-label`
- Progress dots or an equivalent step indicator
- `@media (prefers-reduced-motion: no-preference)` around keyframes
- Deterministic first render with the first step active

Escape XML text:

| Character | Escape |
|---|---|
| `&` | `&amp;` |
| `<` | `&lt;` |
| `>` | `&gt;` |

## Color Semantics

Use at most 3 color semantics per diagram.

| class | Meaning |
|---|---|
| `c-gray` | Start or end |
| `c-blue` | Input, request, or information processing |
| `c-teal` | Server or system processing |
| `c-green` | Success or completion |
| `c-amber` | Decision or validation |
| `c-coral` | Failure or error |
| `c-purple` | General business action |

Color encodes meaning, not sequence.

## Final Output

If outputting SVG, output only SVG. Do not include explanations, Markdown, or code fences.

If outputting HTML, output only HTML. Do not include explanations, Markdown, or code fences.

Only provide prose when the user asks for analysis, optimization, or a plan.
