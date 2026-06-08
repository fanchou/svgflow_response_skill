# SVG Validation Checklist

## Structure

- [ ] Starts with `<svg`
- [ ] Ends with `</svg>`
- [ ] No XML declaration
- [ ] No Markdown fence
- [ ] No comments
- [ ] Has `<title>`
- [ ] Has `<desc>`
- [ ] Has `<defs>`
- [ ] Has a unique marker id in the form `svgflow-{id}-arrow`
- [ ] Root has `class="svgflow"` and `data-svgflow-id`
- [ ] Root has `xml:lang`, `lang`, and `dir`

## Coordinates

- [ ] `viewBox="0 0 680 H"`
- [ ] Width is 680
- [ ] No negative coordinates
- [ ] rect `x + width` is not greater than 680
- [ ] rect `y + height` is not greater than H
- [ ] All polygon points are inside the viewBox
- [ ] All path coordinates are inside the viewBox
- [ ] All elements are inside the safe area
- [ ] `H = max bottom + 40`

## Nodes

- [ ] Node count is at most 8
- [ ] Each node is `<g class="node c-xxx">`
- [ ] Decision nodes use polygon
- [ ] Decision nodes do not hard-code fill or stroke
- [ ] Start and end nodes use `rx = 22`
- [ ] Action nodes use `rx = 8`

## Text

- [ ] All text elements have class
- [ ] Node text has `dominant-baseline="central"`
- [ ] Titles are short
- [ ] Subtitles are short
- [ ] Special characters are escaped
- [ ] Text language matches `xml:lang`
- [ ] RTL text uses `dir="rtl"`

## Connectors

- [ ] Lines use `class="arr"`
- [ ] Paths use `fill="none"`
- [ ] `marker-end` references the scoped marker id
- [ ] Connectors do not cross unrelated nodes
- [ ] Labels use `class="ts label"`

## Colors

- [ ] At most 3 color semantics
- [ ] Colors are semantically consistent
- [ ] Colors do not encode sequence

## Universal Infographic Quality

- [ ] Visible text snippets are short enough to fit stable SVG cards
- [ ] Connector labels use masks or label backgrounds
- [ ] Repeated color semantics have compact legend swatches
- [ ] Palette uses enough distinct semantic tones for scanability
- [ ] Clickable prompts are attached to clickable groups
- [ ] Large group containers visibly contain child cards
- [ ] Rect geometry stays inside the 680/690-wide viewBox
