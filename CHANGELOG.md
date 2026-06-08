# Changelog

## 1.36.0

- Extended production pipeline fixtures beyond SVG so assistant-response-to-DSL-to-HTML walkthrough and module-grid paths are validated.
- Added HTML production cases that run DSL validation, production HTML contract, render surface, and escaping-safety gates.
- Updated the pipeline helper and shared validator registry to dispatch validators against DSL, SVG, HTML, or rendered-output artifacts.

## 1.35.0

- Added renderer contract checks that require browser render metrics guidance for generated HTML.
- Updated renderer guidance so walkthrough and module-grid HTML are generated with scalable SVGs, no horizontal overflow, 32px click targets, deterministic active state, and mobile-safe grids.
- Updated repair rules for browser metric failures, including overflow, undersized controls, hidden active steps, and invisible cards or SVGs.

## 1.34.0

- Added dependency-free browser render metric validation through Chrome DevTools Protocol.
- Added browser metric fixtures for walkthrough and module-grid HTML, including negative cases for horizontal overflow and undersized click targets.
- Documented browser render metrics as the real DOM layout verification step for release environments with Chrome or Chromium.

## 1.33.0

- Added `--render-surface` validation for embeddable walkthrough and module-grid HTML render stability.
- Added render surface fixtures for scalable embedded SVGs, stable click targets, overflow protection, deterministic initial state, and responsive grids.
- Wired render surface validation into package and release checks.

## 1.32.0

- Added `--production-html-contract` validation for interactive walkthrough and module-grid HTML outputs.
- Added production HTML contract fixtures covering reduced-motion guards, responsive module grids, host tokens, action buttons, safe HTML, and embedded SVG accessibility.
- Wired production HTML contract validation into package and release checks.

## 1.31.0

- Added `--escaping-safety` validation for SVG/HTML text, attributes, dangerous tags, JavaScript URIs, and unsafe inline event handlers.
- Added escaping safety fixtures for valid XML entities, unescaped SVG ampersands, injected HTML tags, and `javascript:` URIs.
- Added `escaping_safety` to the production pipeline validator set so release fixtures check escaping before interaction accessibility.

## 1.30.0

- Added interaction validation for escaped `sendPrompt(...)` prompt strings so inline handlers cannot break on apostrophes or quote-heavy user text.
- Added focused and production-pipeline negative fixtures for unsafe prompt escaping.
- Documented prompt escaping as part of the production interaction-accessibility contract.

## 1.29.0

- Added negative pipeline coverage for `text_fit` and `interaction_accessibility` validator failures.
- Added pipeline-specific invalid SVG fixtures that pass earlier structure checks but fail the intended production validator.
- Documented expanded negative pipeline coverage for text-fit and interaction-accessibility regressions.

## 1.28.0

- Added `text_fit` and `interaction_accessibility` to the shared production pipeline validator registry.
- Updated production pipeline fixtures so every response-to-DSL-to-SVG case executes DSL, SVG, visual-quality, readability, text-fit, and interaction-accessibility gates.
- Documented the expanded production pipeline contract in the README, skill instructions, and production checklist.

## 1.27.0

- Added `--production-svg-contract` to validate every universal/unknown infographic SVG example through structure, visual quality, text-fit, and interaction accessibility checks.
- Updated universal infographic SVG fixtures so clickable modules are named, focusable, keyboard-operable controls instead of pointer-only groups.
- Included the production SVG contract in release documentation and the package gate.

## 1.26.0

- Added `tests/renderer_contract_cases.json` and `--renderer-contract` validation to keep renderer prompts, repair rules, and base templates aligned with release gates.
- Updated renderer guidance so new interactive SVG modules include accessible button semantics, keyboard activation, named controls, and no detached script prompts.
- Updated repair guidance for text-fit failures, negative letter spacing, locale/direction mismatches, and inaccessible interactive modules.

## 1.25.0

- Added `tests/interaction_accessibility_cases.json` and `--interaction-accessibility` validation for clickable SVG modules.
- Required visible prompt controls to expose `role="button"`, `tabindex="0"`, an accessible name, and Enter/Space keyboard handling.
- Added a negative guard against detached `sendPrompt` calls inside scripts so interactions stay attached to visible modules.

## 1.24.0

- Added `tests/text_fit_cases.json` and `--text-fit` validation for long unbreakable labels, explicit fit metadata, CJK locale metadata, RTL direction metadata, and negative letter-spacing failures.
- Added dedicated Arabic and Chinese text-fit fixtures to keep multilingual rendering constraints covered without expanding the diagram family model.
- Included text-fit validation in the package release gate and production checklist.

## 1.23.0

- Added template selection validation for common information-architecture signals, mapping assistant responses to v2 template hints and layout intents before DSL generation.
- Added `tests/template_selection_cases.json` and `--template-selection` coverage for comparison, dashboard, hierarchy, cause/effect, swimlane, timeline, layered architecture, feedback loop, concept map, matrix fallback, and freeform fallback.
- Expanded the input quality gate so structured non-flow responses such as dashboards, hierarchies, concept maps, swimlanes, and mixed-signal maps are not rejected before template selection.

## 1.22.0

- Added primitive coverage validation for reusable infographic grammar: group containers, lanes, nested membership, feedback loops, fan-out/fan-in, phase steps, protected connector labels, legend swatches, card grids, and clickable modules.
- Added `tests/primitive_coverage_cases.json` and a universal primitive coverage DSL fixture to prove breadth without adding another diagram family.
- Added `--primitive-coverage` as a focused validation command.
- Expanded a freeform infographic SVG fixture so more modules expose clickable `sendPrompt` interactions.

## 1.21.0

- Added a shared `PIPELINE_VALIDATORS` registry and `run_pipeline_validators()` runner for production pipeline validation.
- Updated `scripts/run_pipeline_fixture.py` to delegate validator dispatch to the shared registry instead of duplicating validator names and branches.
- Tightened pipeline-helper maintainability checks so future validators must be added in one place.

## 1.20.0

- Replaced the long `validate_svg.py` CLI branch chain with a `COMMAND_HANDLERS` registry and centralized usage output.
- Added validator maintainability checks so future CLI gates must use the command registry instead of adding ad-hoc branches.

## 1.19.0

- Added negative pipeline cases and `--negative-pipeline` validation for production-helper failure paths.
- Release validation now proves bad validator declarations, invalid SVG output, and layout-intent drift fail through the same production pipeline helper.

## 1.18.0

- Expanded production pipeline fixtures to cover universal fallback cases and readability validation.
- Updated `scripts/run_pipeline_fixture.py` so declared validators are enforced, unknown validators fail, and `readability_score` is executed instead of being silently ignored.

## 1.17.0

- Added unknown infographic fallback cases and `--unknown-infographic` validation so structured inputs that do not match a catalog template still use the universal infographic DSL.
- Added matrix and freeform fallback fixtures that pass infographic, visual-quality, and readability validation without creating new schema families.

## 1.16.0

- Added readability score cases and `--readability-score` validation across official-style infographic fixtures.
- Added release-gate coverage for text budget, label protection, legend coverage, palette diversity, interactions, and connector density.

## 1.15.0

- Added input quality cases and `--input-quality` validation for visualize, overview, and reject decisions before DSL generation.

## 1.14.0

- Added repair-signal fixture cases and a `scripts/run_repair_signal_fixture.py` helper that maps validator failures to repair rules and concrete actions.

## 1.13.0

- Added production pipeline fixture cases and a `scripts/run_pipeline_fixture.py` helper for validating one response-to-DSL-to-SVG chain.

## 1.12.0

- Added a production checklist and `--release-check` gate for release-ready package verification.
- Added MANIFEST consistency validation so required release files and negative fixtures cannot drift out of the package list.

## 1.11.0

- Added a v2 infographic template catalog for decision matrix, KPI dashboard, org hierarchy, cause-effect map, swimlane workflow, roadmap timeline, architecture stack, feedback loop, and concept map.
- Added a freeform insight-map template and real assistant-response regression fixture for mixed signals, risks, recommendations, and evidence.
- Added negative visual-quality fixtures for long text, missing legends, unprotected labels, narrow palettes, and detached interactions.
- Added package validation for the template catalog to keep templates as v2 presets instead of schema families.
- Added the universal `infographic` DSL as the preferred v2 structure for new visuals.
- Added `layout.intent` so visual shape can be chosen by structure instead of narrow diagram families.
- Added validation for universal nodes, groups, edges, labels, legends, steps, and interactions.
- Added common v2 layout intents for `comparison`, `hierarchy`, and `dashboard` instead of creating more legacy families.
- Added a universal infographic SVG golden fixture and validator for generic official-style output.
- Added v2 DSL and SVG golden coverage for comparison, hierarchy, and dashboard layouts.
- Added v2 end-to-end case validation for decision matrix, architecture stack, swimlane workflow, roadmap timeline, cause-effect map, feedback loop, and freeform insight maps from response input to template, DSL, and SVG fixtures.
- Added machine-validated legacy-to-v2 mapping so the 8 legacy families remain compatibility templates rather than expansion targets.
- Added `--visual-quality` checks for universal infographic SVG text length, label protection, legend swatches, palette diversity, clickable groups, and group containment.
- Added `--negative-visual-quality` checks so known-bad infographic SVG fixtures must fail with expected repair signals.
- Added `--visual-snapshots` structural baselines for key infographic SVGs to catch regressions in paths, text, legends, clicks, palettes, and required visible fragments.
- Added repair prompt guidance for negative visual-quality signals so generated SVGs have deterministic fixes for text, legends, labels, palettes, and clickable interactions.
- Reworked parser, DSL builder, layout planner, renderer, and repair prompts so new work defaults to the universal model.
- Added package validation that prevents prompt guidance from drifting back to legacy family-first behavior.
- Fixed agentic-pipeline validation so phased-pipeline fixtures are no longer misclassified by broad filename globs.

## 1.10.0

- Added `phased_pipeline` for long technical lifecycle diagrams with phase containers and local subflows.
- Added phased-pipeline DSL schema, Chinese Flutter rendering pipeline fixture, and official-style SVG golden output.
- Added validation for long 680-wide SVGs, phase containers, local flows, side notes, legends, label masks, and control-character rejection.

## 1.9.0

- Added `agentic_pipeline` for fan-out/fan-in agent workflows such as agentic RAG.
- Added agentic-pipeline DSL schema, Chinese agentic RAG fixture, and official-style SVG golden output.
- Added validation for 680/690-wide official SVG, worker/source pairing, fan-out/fan-in connectors, replanning loops, masks, and control-character rejection.

## 1.8.0

- Added `module_grid` for HTML card-grid infographics with module cards, semantic badges, icons, and CTA buttons.
- Added module-grid DSL schema, Chinese RL engineering module fixture, and HTML golden output.
- Added validation for host design tokens, responsive one-column fallback, per-card titles, subtitles, detail labels, and `sendPrompt` buttons.

## 1.7.0

- Added `system_loop` for closed-loop interaction diagrams such as agent-environment-device feedback systems.
- Added system-loop DSL schema, Chinese RL digital twin fixture, and official-style SVG golden output.
- Added validation for actors, bidirectional signals, dashed secondary paths, label-gap masks, and forbidden control characters.

## 1.6.0

- Reframed the package from a flowchart-only skill to a response-to-infographic skill.
- Added `knowledge_map`, `architecture_map`, and `interactive_walkthrough` DSL families.
- Added official-style validation for interactive SVG knowledge maps and layered architecture maps.
- Added HTML walkthrough validation for step controls, progress dots, accessibility labels, and reduced-motion-safe animation.
- Added Chinese fixtures for IoT data lake architecture and federated learning walkthroughs to verify language preservation.
- Upgraded parser, DSL builder, layout, renderer, and repair prompts from flowchart-only rules to infographic-family rules.
- Extended test cases and i18n validation beyond `nodes` and `edges`.

## 1.5.0

- Added dedicated locale signal fixtures for English, Chinese, and Arabic parsing.
- Added a Chinese DSL fixture to verify that Chinese input can produce Chinese output.
- Strengthened i18n validation to require English, Chinese, and RTL coverage.
- Clarified that Chinese should only appear in the Chinese README and necessary locale/i18n fixtures.

## 1.4.0

- Converted primary package documentation, prompts, validators, examples, and tests to English-first content.
- Added `README.zh-CN.md` as the dedicated Chinese documentation file.
- Added `locale` and `textDirection` to Flow DSL metadata.
- Added SVG `xml:lang`, `lang`, and `dir` requirements.
- Relaxed edge labels for localized short labels.
- Added English and Arabic DSL examples for i18n coverage.
- Added `--i18n` validation.

## 1.3.0

- Added coverage validation for DSL examples across node types, branches, routes, modes, directions, and colors.
- Added diverse DSL examples for error handling, right-side retry loops, LR layout, and overview diagrams.
- Added rendered golden SVG examples for right-side error handling and LR layout.
- Package validation now checks every DSL example and every rendered SVG golden output.

## 1.2.0

- Scoped SVG root styling with `class="svgflow"` and `data-svgflow-id`.
- Replaced generic marker ids with diagram-scoped marker ids.
- Added deterministic layout constants for node sizes, branch positions, and connector routing.
- Added host CSS template for `raw_svg` and `component_ready` modes.
- Expanded SVG validation to catch rect, polygon, and path bounds issues.
- Added an invalid overflow fixture to prove rendering overflow is rejected.

## 1.1.0

- Added standard SKILL.md frontmatter for skill discovery.
- Added supporting-file guidance and package verification command.
- Expanded test cases with real assistant-response inputs and edge cases.
- Added package-level validation for metadata, fixtures, DSL, and SVG examples.
- Tightened Flow DSL and Layout schema constraints.

## 1.0.0

- Initial production-grade SVGFlow Response-to-Flow Skill package.
- Added SKILL.md with full operating rules.
- Added Flow DSL and Layout schemas.
- Added prompt modules.
- Added SVG / HTML templates.
- Added validation checklist and repair rules.
- Added search flow example and test cases.
- Added basic SVG validator script.
