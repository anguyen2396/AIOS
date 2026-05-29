---
name: excalidraw-diagram
description: Use when someone asks to draw a diagram, make an Excalidraw diagram, or build an editable diagram. Default for all diagram requests.
---

## Style Reference

Base all visual decisions on `references/system design.png`. Read that file before generating any diagram. The canonical style:

- **Font:** Virgil (`fontFamily: 1`) — handwritten feel throughout. No Helvetica or Cascadia unless specifically a code label.
- **Roughness:** `1` on all shapes. Gives the authentic Excalidraw sketch look.
- **Roundness:** `{"type": 3}` on all rectangles (rounded corners). Sharp corners only for grid/matrix layouts.
- **Stroke width:** `2` for shapes, `1.5` for arrows.
- **Actor nodes:** Use `ellipse` (circle) for humans/clients/users, not rectangles.
- **Context boxes:** Dashed border (`strokeStyle: "dashed"`), no fill or very light gray fill, for Task/Constraint/Legend boxes.
- **Annotation stickies:** Pink/salmon background (`backgroundColor: "#ffc9c9"`, `strokeColor: "#e03131"`) for question callouts or design notes embedded in the diagram.
- **Arrow labels:** Plain inline text elements (lowercase, `fontSize: 14`, `strokeColor: "#1e1e1e"`), not boxed. Position 15-20px above the arrow midpoint.
- **Background:** White (`#ffffff`).

---

## Workflow

### Step 1: Understand the request
Before generating anything, make sure you know:
- What concept or system are they diagramming?
- What are the major components or sections?
- What is the flow or relationship between them?

If the request is vague (e.g., "make a diagram of Docker"), ask 1-2 clarifying questions:
- What specific aspect? (architecture, networking, volumes, etc.)
- What level of detail? (high-level overview vs. detailed internals)

### Step 2: Research if needed
If you're not confident about the technical accuracy of the concept, research it before diagramming. Verify:
- Correct component names and relationships
- Proper hierarchy and nesting
- Accurate data flow direction

### Step 3: Plan the layout
Before writing any JSON, sketch the layout mentally:
- What are the major sections? (left-to-right or top-to-bottom)
- What is nested inside what?
- What arrows connect what?

Write down the section plan:
```
[Section A: w=170] --40px gap-- [Section B: w=170] --40px gap-- [Section C: w=640]
```

### Step 4: Generate elements
Build elements in order:
1. Outer boxes / containers first
2. Section header text
3. Nested elements (top to bottom within each section)
4. Arrows and arrow labels last

### Step 5: Save and deliver
1. Save to `[concept-slug].excalidraw` in the current directory
2. Show the full JSON in a code block so the user can copy it directly
3. Briefly describe what the diagram shows and what each color zone represents
4. Tell the user how to use the file:

> **How to view and edit your diagram:**
> - Go to excalidraw.com (free, no account needed)
> - Option A: Click the menu (top-left hamburger icon) > "Open" > select the `.excalidraw` file
> - Option B: Copy the JSON code block above, open excalidraw.com, and paste it with Ctrl+V / Cmd+V
> - Every element is fully editable -- drag to move, grab handles to resize, double-click to edit text

### Step 6: Handle feedback
If the user asks for changes:
- Shifting an element = update x/y on that element + all elements that depend on it
- Changing text = update both `text` and `originalText` fields
- Adding a zone = assign it a new color from the palette, keep spacing consistent
- If a diagram gets complex (20+ elements), build it section by section to avoid coordinate errors

---

## Critical Rule: Text Contrast

Text inside colored shapes must be readable. Use `#1e1e1e` (near-black) or `#343a40` (dark charcoal) for all text inside filled shapes. Never use the zone's stroke color for text sitting on that zone's background (e.g., yellow text on a yellow card is unreadable). Reserve the zone's strokeColor for shape borders and arrows only.

---

## Design Principles

**Color tells the story:** One color per logical zone. Everything in the "input" zone is blue. Everything in the "output" zone is green. The viewer should understand structure before reading a word.

**Nesting shows containment:** If X lives inside Y, X's box is drawn inside Y's box with consistent padding. Coordinates are absolute, not relative: `child_x = parent_x + padding`.

**Labels are short:** 2-5 words per label. Longer explanations become annotations with smaller fontSize and muted color (`#868e96`).

**White space is structure:** 15px minimum gap between siblings. 40px minimum between major sections.

**Arrows carry intent:** Color arrows to match purpose. Label every non-obvious arrow.

---

## Layout System

Always plan coordinates before writing JSON.

1. Identify major sections (left-to-right or top-to-bottom)
2. Assign fixed width and starting x to each section
3. Calculate gaps: 40-60px between major sections, 15-25px between siblings
4. Work top-to-bottom within sections: `next_y = current_y + current_height + gap`

**Padding rules:**
- Outer box to inner label: 8-10px top offset
- Outer box to nested box: 10-15px offset on all sides
- Sibling elements: 10-15px gap

**Text width trick:** Set text width = parent box width. Text centers automatically when `textAlign: "center"`.

**Arrow labels:** Position as separate text elements, 20-25px above the arrow's midpoint y, with width and x matching the arrow.

**Coordinate math example:**
```
Section A: x=30,  w=170  -> right edge = 200
Gap:                        40px
Section B: x=240, w=170  -> right edge = 410
Gap:                        40px
Section C: x=450, w=600  -> right edge = 1050
```

---

## Color System

Derived from `references/system design.png`. Default palette — use this unless the user requests a specific color scheme:

| Role | strokeColor | backgroundColor |
|------|-------------|-----------------|
| Service / component (default) | `#1971c2` | `#a5d8ff` |
| Actor / user (circle) | `#1971c2` | `#74c0fc` |
| Storage / database | `#1971c2` | `#a5d8ff` |
| Annotation sticky | `#e03131` | `#ffc9c9` |
| Context / constraint box | `#868e96` | `transparent` (dashed border) |
| Success / output highlight | `#2f9e44` | `#b2f2bb` |
| Warning / error | `#c92a2a` | `#ffe3e3` |

**Color discipline from the reference PNG:**
- Don't assign colors by zone/layer. Assign by **node type** — services are all the same blue, only annotations and context boxes deviate.
- If a diagram has multiple logical zones (e.g., frontend vs backend vs data), use subtle background rectangles with light fill and dashed borders to group them — not color changes on individual nodes.
- Text on colored shapes: always `#1e1e1e` (near-black) or white if background is very dark.

---

## Typography Scale

All text uses `fontFamily: 1` (Virgil) to match the handwritten style in `references/system design.png`. Cascadia only for inline code snippets.

| Role | fontSize | fontFamily |
|------|----------|------------|
| Diagram title | 28-32 | 1 (Virgil) |
| Node / component label | 20-24 | 1 |
| Sub-label / service name | 14-16 | 1 |
| Arrow label | 13-14 | 1 |
| Annotation sticky text | 14-16 | 1 |
| Context box header | 20-22 | 1 |
| Context box body | 14-15 | 1 |

Text width = parent box width. Text x/y offset ~8-10px from box x/y for padding.

---

## Element Schema

Every element needs these base fields. Do not omit any.

### Base fields (all types)
```json
{
  "id": "unique-string",
  "type": "rectangle|ellipse|diamond|arrow|line|text|freedraw",
  "x": 0, "y": 0,
  "width": 100, "height": 50,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "frameId": null,
  "roundness": null,
  "boundElements": [],
  "updated": 1,
  "link": null,
  "locked": false
}
```

### Text fields (add to base)
```json
{
  "text": "Label text",
  "fontSize": 16,
  "fontFamily": 1,
  "textAlign": "center",
  "verticalAlign": "top",
  "containerId": null,
  "originalText": "Label text",
  "lineHeight": 1.25
}
```

### Arrow fields (add to base)
```json
{
  "points": [[0, 0], [100, 0]],
  "lastCommittedPoint": null,
  "startBinding": null,
  "endBinding": null,
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```

### Key values
- **fontFamily:** 1 = Virgil (handwritten, default — use this always), 2 = Helvetica, 3 = Cascadia (monospace, code only)
- **roughness:** `1` always (matches the sketchy hand-drawn look in the reference PNG)
- **fillStyle:** `"solid"` for all filled shapes
- **roundness:** `{"type": 3}` for rectangles (default), `{"type": 2}` for curved arrows, `null` for sharp-corner context boxes
- **strokeStyle:** `"solid"` for components, `"dashed"` for context/constraint boxes and optional/secondary connections
- **strokeWidth:** `2` for shapes, `1.5` for arrows

---

## Common Patterns

### Labeled box
```
[Rect: x, y, w, h]
[Title text: x, y+10, w, fontSize=18]
[Subtitle: x, y+38, w, fontSize=14, strokeColor=#868e96]
```

### Nested container
```
[Host rect: x=0, y=0, w=640, h=500]
[Host label: x=0, y=10, w=640]
[Item 1: x=15, y=50, w=190, h=200]
[Item 2: x=225, y=50, w=190, h=200]
[Item 3: x=435, y=50, w=190, h=200]
```

### Arrow with label
```
[Arrow: x=start_x, y=mid_y, width=gap_width, points=[[0,0],[gap_width,0]]]
[Label: x=start_x, y=mid_y-25, width=gap_width, textAlign=center]
```

---

## JSON Wrapper

Every diagram uses this shell:
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [ ... ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```
