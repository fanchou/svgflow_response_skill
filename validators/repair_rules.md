# SVG Repair Rules

## Common Issues

### 1. Wrong viewBox width

Bad:

```svg
viewBox="0 0 800 600"
```

Fix:

```svg
viewBox="0 0 680 600"
```

Then recalculate coordinates.

### 2. Path missing `fill="none"`

Bad:

```svg
<path d="M 1 2 L 3 4" class="arr"/>
```

Fix:

```svg
<path d="M 1 2 L 3 4" fill="none" class="arr"/>
```

### 3. Marker id is not scoped

Bad:

```svg
<marker id="arrow">
<line marker-end="url(#arrow)"/>
```

Fix:

```svg
<marker id="svgflow-signup-flow-arrow">
<line marker-end="url(#svgflow-signup-flow-arrow)"/>
```

Multiple diagrams may be embedded on the same page. Never use a generic marker id.

### 4. Text missing class

Bad:

```svg
<text x="340" y="62">Start</text>
```

Fix:

```svg
<text class="th" x="340" y="62" text-anchor="middle" dominant-baseline="central">Start</text>
```

### 5. Decision node hard-codes colors

Bad:

```svg
<polygon points="..." fill="#633806" stroke="#EF9F27"/>
```

Fix:

```svg
<g class="node c-amber">
  <polygon points="..."/>
</g>
```

### 6. Element exceeds safe area

Repair strategy:

1. Shorten the label.
2. Check `x + width <= 680` and `y + height <= H`.
3. Reduce node width within allowed bounds.
4. Adjust x.
5. Fall back to TB layout.

### 7. Too many nodes

Repair strategy:

1. Merge consecutive small actions.
2. Merge technical details.
3. Remove auxiliary steps.
4. Merge error branches.

### 8. Infographic text is too long

Repair strategy:

1. Move detail into subtitle, legend, or action prompt.
2. Replace prose with a short label.
3. Split one long label into two shorter lines only when the card has enough height.

### 9. Connector label lacks protection

Repair strategy:

1. Add a small label background rect.
2. Or add a mask gap behind the label.
3. Keep the label at least 8 px away from node edges.

### 10. Palette is too narrow

Repair strategy:

1. Assign semantic tones by role, not by sequence.
2. Use at least four distinct tones for rich official-style infographics.
3. Add a legend when tone meanings repeat.

### 11. Compact legend is missing

Repair strategy:

1. Add 2 to 5 small swatches near the bottom of the viewBox.
2. Keep each swatch 8 to 16 px wide and high.
3. Pair every swatch with a short text label.
4. Use legend tones only when they map to repeated semantics.

### 12. sendPrompt is detached

Repair strategy:

1. Wrap the visible card, chip, or module in `<g role="button" tabindex="0" aria-label="..." onclick="sendPrompt('...')" onkeydown="...">`.
2. Attach prompts to the element the user can reasonably click.

### 13. browser render metrics fail

Repair strategy:

1. For horizontal overflow, use scalable SVGs with `width="100%"`, add `overflow-wrap:anywhere`, add `min-width:0` to grid cards, and shorten unbreakable labels.
2. For undersized controls, give every HTML button at least a 32px click target with stable `min-height`, `min-width`, and padding.
3. For walkthrough state issues, keep exactly one single active step visible on first render and initialize the current step deterministically.
4. For invisible cards or SVGs, verify the active container is not `display:none`, each SVG has a viewBox, and card widths stay inside the viewport.
3. Remove detached prompt calls from `<script>`, invisible elements, or comments.
4. Keep one prompt focused on one drill-down question.
5. The keyboard handler must activate the same prompt with Enter or Space.

### 13. prompt string is not escaped

Repair strategy:

1. Treat the prompt as a JavaScript string literal embedded inside an XML attribute.
2. Escape any quote that matches the string delimiter before placing it in `onclick` or `onkeydown`.
3. Prefer a single escaping helper in generators instead of hand-building handler strings.
4. Keep the same escaped prompt in both the pointer and keyboard handlers.

### 14. Interactive SVG control is not accessible

Repair strategy:

1. Add `role="button"` to clickable SVG groups.
2. Add `tabindex="0"` so keyboard users can focus the module.
3. Add `aria-label` or `aria-labelledby` with a short localized control name.
4. Add an `onkeydown` handler for Enter or Space that calls the same `sendPrompt(...)` as `onclick`.
5. Keep `sendPrompt(...)` out of `<script>` blocks so the control remains discoverable and visible.

### 15. Long label does not fit

Repair strategy:

1. Shorten visible text before enlarging the layout.
2. Split labels into multiple `<tspan>` rows when the card has enough vertical room.
3. For unavoidable technical identifiers, add `data-fit` and `textLength` to make the fit explicit.
4. Remove negative letter spacing; it harms multilingual rendering.
5. Confirm the root locale and direction match the visible language.

### 16. Visual-quality negative fixtures fail

Repair strategy:

1. Treat `text is too long`, `compact legend`, `protect labels`, `palette is too narrow`, and `clickable groups` as repair signals.
2. Apply the matching repair above before changing unrelated layout structure.
3. Re-run `python3 scripts/validate_svg.py --negative-visual-quality .` after edits to prove bad fixtures are still rejected.

### 17. Readability score is too low

Repair strategy:

1. Inspect the failing readability metrics before changing the layout family.
2. Shorten visible text snippets before increasing card sizes.
3. Add or restore label protection, compact legend swatches, and semantic palette diversity when those signals are missing.
4. Reduce connector density by grouping related edges, using one labeled trunk path, or moving secondary detail into `sendPrompt`.
5. Re-run `python3 scripts/validate_svg.py --readability-score .` after edits.
