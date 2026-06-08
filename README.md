# SVGFlow Response Infographic Skill

A skill package for turning an assistant response into a compact SVG or HTML infographic.

## Purpose

This is a Response-to-Infographic post-processing skill. It does not draw directly from the user's raw prompt. It reads an assistant response, builds a universal infographic DSL when possible, plans layout, renders valid SVG or HTML, validates, and repairs once if needed.

## Universal Model

New work should prefer `diagramType: "infographic"` unless a legacy fixture or a very specific renderer requires a specialized family.

The universal DSL separates content semantics from visual shape:

- `content.nodes`: entities, actions, containers, decisions, metrics, notes, and outputs
- `content.groups`: containers, layers, zones, sections, and swimlanes
- `content.edges`: process, control, data, dependency, and feedback links
- `content.labels`: annotations and callouts
- `content.legends`: tone and symbol explanations
- `content.steps`: optional walkthrough states
- `interactions`: click, step, highlight, toggle, and prompt actions
- `layout.intent`: `linear`, `layered`, `loop`, `matrix`, `hub_spoke`, `timeline`, `swimlane`, `comparison`, `hierarchy`, `dashboard`, or `freeform`

Template selection is defined in `templates/infographic-templates.json`. Templates are v2 presets, not new schema families.

## Legacy And Specialized Families

Legacy families are compatibility templates. Their v2 mapping is defined in `schemas/legacy-to-infographic-map.json`.

| family | DSL `diagramType` | Output |
|---|---|---|
| Universal infographic | `infographic` | Preferred v2 structure for most SVG or HTML information graphics |
| Flowchart | `flowchart` | Compact SVG process, branch, retry, or error flow |
| Knowledge map | `knowledge_map` | Official-style interactive SVG with chapters and principle grids |
| Architecture map | `architecture_map` | Layered SVG information architecture with nested zones and chips |
| Interactive walkthrough | `interactive_walkthrough` | HTML preview with step controls, progress dots, and CSS animation |
| System loop | `system_loop` | Compact feedback-loop SVG with actors, labeled signals, guards, and secondary paths |
| Module grid | `module_grid` | HTML card grid with modules, badges, semantic tones, icons, and CTA buttons |
| Agentic pipeline | `agentic_pipeline` | Fan-out/fan-in agent workflow with workers, knowledge sources, synthesizer, output, and replanning loop |
| Phased pipeline | `phased_pipeline` | Long vertical lifecycle pipeline with phase containers, local flows, side notes, and legend |

## Usage

Run package validation before release:

```bash
python3 scripts/validate_svg.py --release-check .
```

The production checklist is maintained in `docs/production-checklist.md`.

Run a production pipeline fixture:

```bash
python3 scripts/run_pipeline_fixture.py --root . --case production_freeform_growth
python3 scripts/run_pipeline_fixture.py --root . --case production_unknown_experiment_priority
python3 scripts/run_pipeline_fixture.py --root . --case production_walkthrough_html
```

Production pipeline fixtures run DSL plus SVG or HTML artifact validators. SVG cases run visual-quality, readability, text-fit, escaping-safety, and interaction-accessibility validators. HTML cases run production HTML contract, render surface, and escaping-safety validators.

Check XML/HTML escaping safety:

```bash
python3 scripts/validate_svg.py --escaping-safety .
```

Check the production HTML contract:

```bash
python3 scripts/validate_svg.py --production-html-contract .
```

Check the render surface contract:

```bash
python3 scripts/validate_svg.py --render-surface .
```

Run browser render metrics when Chrome or Chromium is available:

```bash
node scripts/check_browser_render_metrics.mjs --root . --cases tests/browser_render_metric_cases.json
```

Check negative pipeline cases:

```bash
python3 scripts/validate_svg.py --negative-pipeline .
```

Negative pipeline cases include unknown validators, bad SVG quality, text-fit failures, interaction-accessibility failures, prompt escaping failures, and layout drift.

Run a repair signal fixture:

```bash
python3 scripts/run_repair_signal_fixture.py --root . --case repair_long_text
```

Run package validation directly while debugging:

```bash
python3 scripts/validate_svg.py --package .
```

Check flow element coverage:

```bash
python3 scripts/validate_svg.py --coverage .
```

Check internationalization coverage:

```bash
python3 scripts/validate_svg.py --i18n .
```

Check input quality decisions:

```bash
python3 scripts/validate_svg.py --input-quality .
```

Check unknown infographic fallback cases that must use the universal model:

```bash
python3 scripts/validate_svg.py --unknown-infographic .
```

Check template selection from assistant-response structure:

```bash
python3 scripts/validate_svg.py --template-selection .
```

Check readability score across official-style infographic fixtures:

```bash
python3 scripts/validate_svg.py --readability-score .
```

Check multilingual text fit and overflow guardrails:

```bash
python3 scripts/validate_svg.py --text-fit .
```

Check SVG interaction accessibility:

```bash
python3 scripts/validate_svg.py --interaction-accessibility .
```

Check renderer contract coverage for prompts and repair rules:

```bash
python3 scripts/validate_svg.py --renderer-contract .
```

Check production SVG contract across universal infographic examples:

```bash
python3 scripts/validate_svg.py --production-svg-contract .
```

Check official-style infographic families:

```bash
python3 scripts/validate_svg.py --knowledge-map .
python3 scripts/validate_svg.py --architecture-map .
python3 scripts/validate_svg.py --walkthrough .
python3 scripts/validate_svg.py --system-loop .
python3 scripts/validate_svg.py --module-grid .
python3 scripts/validate_svg.py --agentic-pipeline .
python3 scripts/validate_svg.py --phased-pipeline .
python3 scripts/validate_svg.py --infographic .
```

Validate one SVG:

```bash
python3 scripts/validate_svg.py examples/search_flow.output.svg
```

Validate one DSL file:

```bash
python3 scripts/validate_svg.py examples/search_flow.dsl.json
```

## Output Modes

| mode | Description |
|---|---|
| `preview_svg` | Standalone SVG with embedded style |
| `raw_svg` | SVG without style, depends on host CSS |
| `html_preview` | Complete HTML document with embedded SVG |
| `component_ready` | Class-based SVG for frontend integration |

`raw_svg` and `component_ready` preserve `class="svgflow"`, `data-svgflow-id`, node color classes, and marker ids. Use `templates/host_css.template.css` as the baseline host CSS.

## Internationalization

The skill keeps labels in the source response language. DSL metadata includes `meta.locale` and `meta.textDirection`; rendered flowchart SVG includes matching `xml:lang`, `lang`, and `dir` attributes. Official-style interactive examples preserve the user's language in visible labels and prompts.

Chinese text is intentionally limited to `README.zh-CN.md` and dedicated i18n fixtures such as `locales/signals.json`, `examples/chinese_*`, and official-style Chinese examples required to verify locale preservation. Other files should avoid Chinese unless they are required language fixtures.
