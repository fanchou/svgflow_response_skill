# Production Checklist

Use this checklist before publishing or relying on the skill in production-like workflows.

## Production Invocation Path

1. Start from an assistant response, not the raw user prompt.
2. Apply the input quality gate: `visualize`, `overview`, or `reject`.
3. Prefer `meta.diagramType = "infographic"` for new work.
4. Select `layout.intent` from the universal intent set before choosing visual shape.
5. Use legacy families only as compatibility templates.
6. Render SVG or HTML from the DSL.
7. Run validation and apply one deterministic repair pass when validation fails.

## Required Release Command

Run the consolidated release gate from the package root:

```bash
python3 scripts/validate_svg.py --release-check .
```

The release check must cover package metadata, schemas, prompts, template catalog, v2 end-to-end cases, unknown infographic fallback, visual quality, readability score, negative fixtures, visual snapshots, legacy compatibility, coverage, and internationalization.

## Additional Debug Commands

Use narrower commands only to isolate a failure:

```bash
python3 scripts/run_pipeline_fixture.py --root . --case production_freeform_growth
python3 scripts/run_pipeline_fixture.py --root . --case production_unknown_experiment_priority
python3 scripts/run_repair_signal_fixture.py --root . --case repair_long_text
python3 scripts/validate_svg.py --package .
python3 scripts/validate_svg.py --input-quality .
python3 scripts/validate_svg.py --template-selection .
python3 scripts/validate_svg.py --unknown-infographic .
python3 scripts/validate_svg.py --pipeline-fixtures .
python3 scripts/validate_svg.py --negative-pipeline .
python3 scripts/validate_svg.py --repair-signals .
python3 scripts/validate_svg.py --infographic .
python3 scripts/validate_svg.py --visual-quality .
python3 scripts/validate_svg.py --readability-score .
python3 scripts/validate_svg.py --text-fit .
python3 scripts/validate_svg.py --escaping-safety .
python3 scripts/validate_svg.py --interaction-accessibility .
python3 scripts/validate_svg.py --renderer-contract .
python3 scripts/validate_svg.py --production-svg-contract .
python3 scripts/validate_svg.py --production-html-contract .
python3 scripts/validate_svg.py --render-surface .
node scripts/check_browser_render_metrics.mjs --root . --cases tests/browser_render_metric_cases.json
python3 scripts/validate_svg.py --negative-visual-quality .
python3 scripts/validate_svg.py --visual-snapshots .
python3 scripts/validate_svg.py --i18n .
python3 scripts/validate_svg.py --coverage .
```

## Failure Triage

- Schema failure: fix the DSL fixture or schema contract first.
- Unknown fallback failure: keep the output as `diagramType: infographic`, select a universal `layout.intent`, and do not add a new schema family for one-off examples.
- Negative pipeline failure: confirm bad validator declarations and bad outputs still fail through the same production helper path.
- Negative pipeline coverage includes text-fit, interaction-accessibility, and prompt escaping failures, not only structural SVG failures.
- Production pipeline failure: confirm every fixture declares DSL plus the right rendered artifact validators. SVG cases need visual-quality, readability, text-fit, escaping-safety, and interaction-accessibility. HTML cases need production HTML contract, render surface, and escaping-safety.
- Visual-quality failure: shorten text, add compact legend swatches, protect connector labels, diversify the palette, or attach `sendPrompt` to clickable groups.
- Readability score failure: reduce text and connector density, add missing labels or legends, improve palette separation, and protect connector labels before changing the core structure.
- Text-fit failure: add explicit wrapping or fitting metadata for long labels, remove negative letter spacing, and set matching locale plus direction for CJK or RTL output.
- Escaping-safety failure: escape XML/HTML text and attributes, reject injected tags, reject `javascript:` URIs, and keep inline handlers on the approved prompt/navigation path.
- Interaction accessibility failure: attach prompts only to visible controls, add `role="button"`, `tabindex="0"`, an accessible name, Enter/Space keyboard handling, and escaped `sendPrompt(...)` prompt strings.
- Renderer contract failure: update renderer and repair guidance before loosening validators; generation rules must mention every release gate that applies to fresh output.
- Production SVG contract failure: fix the generated SVG artifact, not only the prompt; universal infographic examples must pass SVG structure, visual quality, text-fit, escaping-safety, and interaction accessibility together.
- Production HTML contract failure: fix walkthrough/module-grid HTML output so it has a hidden accessible heading, safe HTML, responsive layout or controls, host tokens, reduced-motion guards for animation, and action buttons when present.
- Render surface contract failure: fix responsive SVG scaling, stable click target sizing, overflow protection, deterministic initial state, or mobile grid behavior before release.
- Browser render metric failure: inspect actual DOM boxes for horizontal overflow, hidden active SVGs, invisible cards, undersized click targets, or multiple visible walkthrough steps.
- Visual snapshot failure: inspect whether the SVG lost structure, labels, legends, interactions, or required visible fragments.
- I18n failure: keep visible output in the source response language and set `meta.locale` plus `meta.textDirection`.
- Legacy failure: confirm the legacy fixture still maps cleanly to the universal infographic model.

## Production Readiness Invariants

- Generated content does not invent business logic absent from the source response.
- New examples default to the universal infographic DSL unless a legacy renderer is explicitly required.
- Unknown structured examples use universal infographic fallback instead of legacy families or new one-off schema families.
- Every rendered infographic has title, description, compact legend, label protection, bounded coordinates, palette diversity, and interactions when prompts are present.
- Long labels either wrap or declare explicit fit behavior; multilingual SVGs declare matching `lang`/`xml:lang` and `dir`.
- Clickable SVG modules are named, focusable, keyboard-operable controls; detached `sendPrompt` calls in scripts and unescaped prompt strings are invalid.
- Renderer prompts and repair rules describe text fit, interaction accessibility, script-free prompt placement, and prompt escaping.
- SVG and HTML outputs escape user-language text before it enters XML attributes, HTML text, URI attributes, or inline handlers.
- HTML walkthrough and module-grid outputs pass the production HTML contract before release.
- HTML walkthrough and module-grid outputs pass the render surface contract before release.
- Browser render metrics pass when Chrome or Chromium is available in the release environment.
- Universal infographic examples pass the same production SVG contract expected from fresh generated output.
- Production pipeline fixtures execute the required SVG or HTML artifact gates before the output is considered usable.
- Chinese text appears only in `README.zh-CN.md` or necessary language fixtures.
- Release evidence comes from current command output, not from previous runs or intent.

## Publish Checklist

- `python3 scripts/validate_svg.py --release-check .` passes.
- `python3 scripts/validate_svg.py --input-quality .` passes.
- `python3 scripts/validate_svg.py --template-selection .` passes.
- `python3 scripts/validate_svg.py --unknown-infographic .` passes.
- `python3 scripts/validate_svg.py --readability-score .` passes.
- `python3 scripts/validate_svg.py --text-fit .` passes.
- `python3 scripts/validate_svg.py --interaction-accessibility .` passes.
- `python3 scripts/validate_svg.py --renderer-contract .` passes.
- `python3 scripts/validate_svg.py --production-svg-contract .` passes.
- `python3 scripts/validate_svg.py --negative-pipeline .` passes.
- `python3 scripts/run_pipeline_fixture.py --root . --case production_freeform_growth` passes.
- `python3 scripts/run_pipeline_fixture.py --root . --case production_unknown_experiment_priority` passes.
- `python3 scripts/run_repair_signal_fixture.py --root . --case repair_long_text` passes.
- `env PYTHONPYCACHEPREFIX=/tmp/svgflow_pycache python3 -m py_compile scripts/validate_svg.py` passes.
- JSON fixtures parse with `python3 -m json.tool`.
- A non-Chinese scan is clean outside `README.zh-CN.md` and dedicated language fixtures.
- `MANIFEST.txt`, `README.md`, `SKILL.md`, `CHANGELOG.md`, and `skill.json` match the files and behavior being shipped.
