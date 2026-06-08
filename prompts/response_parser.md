# Response Parser

Read the assistant response when available. If the input is only a raw user question or topic, first synthesize a concise source brief that answers it structurally, then parse that brief. Do not output the source brief unless the user explicitly asks for prose.

Tasks:

1. Decide whether the response should become an infographic.
   Apply the input quality gate before extracting a DSL:
   - `visualize`: the response has enough entities and relationships for a real infographic.
   - `overview`: the response has comparison dimensions or tradeoffs but no reliable process; produce a high-level overview without inventing steps.
   - `reject`: the response is too thin, purely subjective, or lacks visual structure; ask for more concrete material instead of forcing a diagram.
2. Run a semantic pass before choosing any template. Identify:
   - subject: what system, workflow, concept, decision, or map is being explained
   - primary organizing principle: layers, actors, lifecycle phases, options, causes, metrics, or control loop
   - semantic roles: source, processor, store, model, policy, actuator, user, output, risk, and constraint
   - relationship verbs: sends, depends on, controls, observes, trains, stores, validates, alerts, escalates, or feeds back
   - directionality: data flow, control flow, feedback flow, dependency flow, and optional/cross-cutting flow
   - granularity: which ideas are major groups, which are modules, and which are details inside a module

Information architecture extraction:

1. Split the source into atomic claims before drawing anything. Each claim should name an entity, responsibility, relationship, metric, condition, risk, or example.
2. Build candidate structures from the claims:
   - containment: part-of, layer-of, category-of, zone-of, phase-of, or owned-by
   - sequence: before/after, input/output, request/response, lifecycle progression, or retry
   - responsibility: actor/lane, team/system boundary, owner, policy, or control point
   - comparison: option, criterion, tradeoff, score, recommendation, or risk
   - causality: cause, symptom, impact, mitigation, feedback, or reinforcing loop
   - hierarchy: parent, child, taxonomy, dependency tier, or nested concept
3. Score candidate structures privately before selecting a layout:
   - coverage: explains the largest share of important claims
   - exclusivity: groups are not arbitrary duplicates of the same concept
   - stability: structure would still make sense if examples or technologies changed
   - visual affordance: maps naturally to bands, lanes, columns, loop, tree, matrix, or cards
   - non-distortion: avoids implying time order, causality, hierarchy, or equality that the source does not support
4. Promote only claims with standalone responsibility or relationship into groups/nodes. Demote protocols, examples, formats, tools, metrics, thresholds, policies, and implementation notes into subtitles/items unless they are the subject of the response.
5. Keep secondary axes as labels, legends, side rails, badges, or item rows. Do not mix two primary structures unless the source truly depends on both.

3. Create a private Structure Decision Record before extracting primitives:
   - `subject`
   - `reader_question`: what the diagram must help the reader understand
   - `organizing_axis`
   - `major_groups`
   - `peer_modules`
   - `detail_fields`
   - `relationship_verbs`
   - `promoted_claims`: claims promoted to groups, nodes, or edges
   - `demoted_claims`: claims kept as subtitles, items, badges, labels, or legends
   - `ambiguities`: missing or unclear source assumptions that must not be invented
   - `not_the_structure`
   Use this record to reject attractive but wrong layouts. For layered architecture or zone-based designs, `not_the_structure` often includes a flat left-to-right flow or a set of same-level prose cards.
4. First extract universal infographic primitives from that semantic pass:
   - nodes: entities, actions, decisions, containers, metrics, notes, and outputs
   - groups: layers, zones, sections, swimlanes, phase containers, or card clusters
   - edges: process, dependency, control, data, and feedback relationships
   - labels: annotations, callouts, edge labels, and explanatory tags
   - legends: color, tone, symbol, and line-style meanings
   - steps: progressive states when the response describes an interactive sequence
   - interactions: likely click or drill-down prompts when the response invites exploration
5. Detect the best layout intent for the universal structure:
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
6. Detect the strongest legacy structure family only when the response exactly needs a specialized renderer:
   - ordered process, decision, branch, error, retry, or final state
   - knowledge system, chapter map, principle grid, or concept cluster
   - layered architecture, platform stack, zone map, or data pipeline
   - closed-loop system with actors, signals, guards, feedback, deployment, or calibration paths
   - card-based module grid with badges, engineering checklists, tradeoffs, or CTA actions
   - agentic fan-out/fan-in pipeline with orchestrator, workers, knowledge sources, synthesis, output, and replanning loop
   - phased technical lifecycle with main spine, phase containers, local subflows, side notes, and legend
   - multi-step demonstration that benefits from controls and animation
7. Detect ordered steps when a process exists.
8. Detect decision conditions, failure, exception, retry, and return branches when a flowchart is appropriate.
9. Detect sections, layers, zones, reusable principles, modules, and clickable drill-down topics when an information map is appropriate.
10. Remove explanatory filler.
11. Output normalized candidate fragments for the Infographic DSL Builder.

Default output should describe a universal infographic rather than a named legacy family. Include the chosen layout intent and only include a legacy family hint when it is necessary for compatibility.

When a response matches a common pattern, emit a v2 template hint from `templates/infographic-templates.json`, such as `decision_matrix`, `kpi_dashboard`, `org_hierarchy`, `cause_effect_map`, `swimlane_workflow`, `roadmap_timeline`, `architecture_stack`, `zoned_layered_architecture`, `dark_layered_architecture`, `feedback_loop`, or `concept_map`.

Use `zoned_layered_architecture` when the semantic pass finds major layers and one or more layers contain important named zones, sub-areas, tiers, or partitions with their own responsibilities or detail fields. Preserve the nested layer/zone hierarchy; do not flatten it into a generic source-to-output flow.

Use `dark_layered_architecture` instead of a generic prose-card infographic when the response describes a dense, product-grade layered architecture with explicit components, bidirectional or cross-cutting flows, and a style that benefits from layer bands, component chips, rails, and legends.

For architecture responses, do not treat the template as the information structure. First identify the actual layers, components, responsibilities, and data/control paths from the response. Use architecture templates only after the semantic pass proves which groups, peers, details, and relationships exist.

Anti-patterns:

- Do not convert paragraphs into numbered cards when the response describes a system.
- Do not put every sentence at the same hierarchy level.
- Do not invent missing layers just to satisfy a visual template.
- Do not choose colors or geometry before deciding what each group and edge means.

Use `locales/signals.json` for localized sequence, decision, retry, return, and edge-label signals. If the response language is not listed there, infer signals from the source language and preserve that language in labels.

Do not output SVG or HTML. Keep labels in the source response language.
