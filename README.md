# SVGFlow Response Infographic Skill

[中文文档](README.zh-CN.md)

SVGFlow is a Codex skill for turning an assistant response into a compact, valid, previewable SVG or HTML infographic.

It is meant to run after an answer already exists. Instead of drawing directly from the user's raw prompt, it reads the assistant response, extracts the useful visual structure, builds a DSL, chooses a layout, renders SVG or HTML, validates the artifact, and repairs once when needed.

## When To Use

Use this skill when a response would be clearer as a visual artifact:

- workflows, decisions, retries, and error paths
- technical pipelines and system execution flows
- architecture maps, layered systems, and data movement
- knowledge maps, principle grids, and structured explanations
- product, business, support, reliability, or operations infographics
- interactive walkthroughs that benefit from step controls

Avoid it for purely conversational answers, short factual responses, or visuals that require information not present in the assistant response.

## Install

The installer is agent-neutral: it copies the runtime skill folder into any folder-based agent skills directory. The only requirement is that the installed skill folder contains `SKILL.md` at its root.

Install directly from GitHub with `npx`:

```bash
npx github:fanchou/svgflow_response_skill --skills-dir <agent-skills-dir>
```

After the package is published to npm, the same installer can be run as:

```bash
npx svgflow-response-skill --skills-dir <agent-skills-dir>
```

For Codex, `--skills-dir` can usually be omitted. The installer defaults to `$CODEX_HOME/skills`, then `~/.codex/skills`:

```bash
npx github:fanchou/svgflow_response_skill
```

For any other agent, pass that agent's skills directory explicitly:

```bash
npx github:fanchou/svgflow_response_skill --skills-dir /path/to/agent/skills
```

The resulting structure is:

```text
<agent-skills-dir>/
  svgflow-response/
    SKILL.md
    agents/openai.yaml
    locales/
    prompts/
    schemas/
    templates/
    validators/
```

The installer copies only runtime skill files, not repository-only files such as tests, changelogs, or release fixtures.

If you have already cloned the repository, you can run the local installer instead:

```bash
node scripts/install-skill.mjs --source /path/to/svgflow_response_skill --skills-dir <agent-skills-dir>
```

The Python installer is kept for environments that prefer Python:

```bash
python scripts/install_skill.py --source /path/to/svgflow_response_skill --skills-dir /path/to/agent/skills
```

Manual installation is also fine: copy or symlink the repository root, or a packaged runtime folder, to `<agent-skills-dir>/svgflow-response` as long as `SKILL.md` lands directly inside that folder.

Restart your agent or start a new session after installation so skill metadata can be discovered.

## Using It In Codex

Once the skill is available, ask Codex to visualize an existing answer as an SVGFlow infographic, SVG, HTML preview, architecture map, workflow, or walkthrough.

The important input is the assistant response to visualize. The skill should not invent missing business logic or answer the original question again.

## What It Produces

| Output mode | Best for |
|---|---|
| `preview_svg` | Standalone SVG with embedded styling |
| `raw_svg` | SVG embedded into an app that provides host CSS |
| `html_preview` | Complete HTML preview with embedded SVG and interaction controls |
| `component_ready` | Class-based SVG prepared for frontend integration |

The default mode is `preview_svg`. `raw_svg` and `component_ready` preserve `class="svgflow"`, `data-svgflow-id`, node color classes, and marker ids so host applications can style or inspect the output.

## Supported Visual Families

New work should prefer `diagramType: "infographic"` unless a fixture, renderer, or explicit request needs a specialized family.

| Family | DSL `diagramType` | Use case |
|---|---|---|
| Universal infographic | `infographic` | General-purpose SVG or HTML information graphics |
| Flowchart | `flowchart` | Process, branch, retry, or error flows |
| Knowledge map | `knowledge_map` | Chaptered knowledge maps and principle grids |
| Architecture map | `architecture_map` | Layered systems with zones, chips, and relationships |
| Interactive walkthrough | `interactive_walkthrough` | HTML previews with steps, progress, and animation |
| System loop | `system_loop` | Feedback loops with actors, signals, guards, and side paths |
| Module grid | `module_grid` | HTML module cards with badges, tones, icons, and actions |
| Agentic pipeline | `agentic_pipeline` | Fan-out/fan-in agent workflows with synthesis and replanning |
| Phased pipeline | `phased_pipeline` | Long lifecycle pipelines with phases, notes, and legends |

## How It Works

The skill keeps content semantics separate from visual layout:

1. Parse the assistant response.
2. Build the selected DSL, preferably the universal infographic DSL.
3. Select a layout intent such as `linear`, `layered`, `loop`, `matrix`, `hub_spoke`, `timeline`, `swimlane`, `comparison`, `hierarchy`, `dashboard`, or `freeform`.
4. Render SVG or HTML from templates.
5. Validate readability, text fit, escaping safety, accessibility, and production contracts.
6. Repair once when validation gives a clear signal.

Template selection lives in `templates/infographic-templates.json`. Legacy-to-v2 mapping lives in `schemas/legacy-to-infographic-map.json`.

## Project Layout

This repository is a development package. The installable runtime skill is the subset copied by `scripts/install_skill.py`.

| Path | Purpose |
|---|---|
| `SKILL.md` | Runtime instructions for the Codex skill |
| `agents/openai.yaml` | UI metadata for skill lists and chips |
| `skill.json` | Package metadata for this repository |
| `schemas/` | DSL and layout schemas |
| `prompts/` | Parser, DSL builder, layout, renderer, and repair prompts |
| `templates/` | SVG, HTML, host CSS, and infographic template presets |
| `validators/` | Validation checklists and repair rules |
| `scripts/install-skill.mjs` | npx-compatible installer |
| `scripts/install_skill.py` | Python installer for local/source installs |
| `examples/` | Development fixtures, not required at runtime |
| `tests/` | Positive and negative fixture cases |
| `docs/production-checklist.md` | Release checklist for maintainers |

## Maintainer Checks

Most users do not need these commands. They are here for contributors changing schemas, prompts, templates, examples, or validators.

Run the release check:

```bash
python3 scripts/validate_svg.py --release-check .
```

Run representative production fixtures:

```bash
python3 scripts/run_pipeline_fixture.py --root . --case production_freeform_growth
python3 scripts/run_pipeline_fixture.py --root . --case production_unknown_experiment_priority
python3 scripts/run_pipeline_fixture.py --root . --case production_walkthrough_html
```

Run focused checks while developing:

```bash
python3 scripts/validate_svg.py --package .
python3 scripts/validate_svg.py --coverage .
python3 scripts/validate_svg.py --i18n .
python3 scripts/validate_svg.py --text-fit .
python3 scripts/validate_svg.py --escaping-safety .
python3 scripts/validate_svg.py --interaction-accessibility .
python3 scripts/validate_svg.py --production-svg-contract .
python3 scripts/validate_svg.py --production-html-contract .
python3 scripts/validate_svg.py --render-surface .
```

Run browser render metrics when Chrome or Chromium is available:

```bash
node scripts/check_browser_render_metrics.mjs --root . --cases tests/browser_render_metric_cases.json
```

## Internationalization

The skill keeps labels in the source response language. DSL metadata includes `meta.locale` and `meta.textDirection`; rendered flowchart SVG includes matching `xml:lang`, `lang`, and `dir` attributes.

Chinese text is intentionally limited to `README.zh-CN.md` and dedicated i18n fixtures such as `locales/signals.json`, `examples/chinese_*`, and official-style Chinese examples required to verify locale preservation.
