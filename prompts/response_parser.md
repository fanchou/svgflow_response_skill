# Response Parser

Read the assistant response, not the user's raw prompt.

Tasks:

1. Decide whether the response should become an infographic.
   Apply the input quality gate before extracting a DSL:
   - `visualize`: the response has enough entities and relationships for a real infographic.
   - `overview`: the response has comparison dimensions or tradeoffs but no reliable process; produce a high-level overview without inventing steps.
   - `reject`: the response is too thin, purely subjective, or lacks visual structure; ask for more concrete material instead of forcing a diagram.
2. First extract universal infographic primitives:
   - nodes: entities, actions, decisions, containers, metrics, notes, and outputs
   - groups: layers, zones, sections, swimlanes, phase containers, or card clusters
   - edges: process, dependency, control, data, and feedback relationships
   - labels: annotations, callouts, edge labels, and explanatory tags
   - legends: color, tone, symbol, and line-style meanings
   - steps: progressive states when the response describes an interactive sequence
   - interactions: likely click or drill-down prompts when the response invites exploration
3. Detect the best layout intent for the universal structure:
   - `linear` for sequences and lifecycles
   - `layered` for architecture stacks and zones
   - `loop` for feedback and control systems
   - `matrix` for module grids, cards, comparisons, and checklists
   - `hub_spoke` for central orchestration, knowledge maps, and fan-out/fan-in systems
   - `timeline` for chronological phases
   - `swimlane` for actor-separated responsibilities
   - `comparison` for side-by-side options, pros/cons, tradeoff matrices, and evaluation criteria
   - `hierarchy` for org charts, taxonomies, trees, nested ownership, and parent-child structures
   - `dashboard` for metrics, status summaries, KPI cards, and operational snapshots
   - `freeform` when an official-style custom layout is clearly better
4. Detect the strongest legacy structure family only when the response exactly needs a specialized renderer:
   - ordered process, decision, branch, error, retry, or final state
   - knowledge system, chapter map, principle grid, or concept cluster
   - layered architecture, platform stack, zone map, or data pipeline
   - closed-loop system with actors, signals, guards, feedback, deployment, or calibration paths
   - card-based module grid with badges, engineering checklists, tradeoffs, or CTA actions
   - agentic fan-out/fan-in pipeline with orchestrator, workers, knowledge sources, synthesis, output, and replanning loop
   - phased technical lifecycle with main spine, phase containers, local subflows, side notes, and legend
   - multi-step demonstration that benefits from controls and animation
5. Detect ordered steps when a process exists.
6. Detect decision conditions, failure, exception, retry, and return branches when a flowchart is appropriate.
7. Detect sections, layers, zones, reusable principles, modules, and clickable drill-down topics when an information map is appropriate.
8. Remove explanatory filler.
9. Output normalized candidate fragments for the Infographic DSL Builder.

Default output should describe a universal infographic rather than a named legacy family. Include the chosen layout intent and only include a legacy family hint when it is necessary for compatibility.

When a response matches a common pattern, emit a v2 template hint from `templates/infographic-templates.json`, such as `decision_matrix`, `kpi_dashboard`, `org_hierarchy`, `cause_effect_map`, `swimlane_workflow`, `roadmap_timeline`, `architecture_stack`, `feedback_loop`, or `concept_map`.

Use `locales/signals.json` for localized sequence, decision, retry, return, and edge-label signals. If the response language is not listed there, infer signals from the source language and preserve that language in labels.

Do not output SVG or HTML. Keep labels in the source response language.
