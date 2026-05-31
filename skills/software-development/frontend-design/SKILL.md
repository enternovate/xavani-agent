---
name: frontend-design
description: Frontend design principles — responsive layouts, accessible components, consistent design systems.
categories:
  - software-development
platforms:
  - web
tags:
  - frontend
  - design
  - ui
  - accessibility
condition: When building or reviewing any user-facing interface.
---

# Frontend Design

> "Good design is as little design as possible. Less, but better."

## When to use

- Building a new page or component.
- Reviewing frontend code for UX issues.
- Establishing a design system.

## Prerequisites

- Understanding of the target users.
- Design tokens or style guide (if available).

## Steps

### 1. Mobile-first layout

Start with the smallest screen. Scale up:
```css
/* Base: mobile */
.container { padding: 1rem; }
/* Tablet */
@media (min-width: 768px) { .container { max-width: 720px; margin: 0 auto; } }
/* Desktop */
@media (min-width: 1024px) { .container { max-width: 960px; } }
```

### 2. Accessible components

Every interactive element must be:
- Keyboard navigable (Tab, Enter, Escape).
- Screen reader friendly (ARIA labels).
- Has visible focus states.
- Colour contrast ≥ 4.5:1.

### 3. Consistent spacing

Use a spacing scale (4px grid):
- xs: 4px, sm: 8px, md: 16px, lg: 24px, xl: 32px, 2xl: 48px.

### 4. Typography

- Limit to 2-3 font sizes per page.
- Line height: 1.5 for body, 1.2 for headings.
- Max line width: 60-75 characters.

### 5. Colour

- Primary, secondary, accent, neutral.
- Semantic: success (green), warning (amber), error (red), info (blue).
- Test with colour-blind simulators.

### 6. Loading and error states

Every component needs:
- Loading skeleton or spinner.
- Error message with retry.
- Empty state with guidance.

## Verification

- Works on mobile, tablet, and desktop.
- Keyboard navigable.
- Screen reader tested.
- All states implemented (loading, error, empty).


## Provenance

Xavani-original (written from scratch for Xavani, inspired by common frontend design principles).
No upstream code was copied verbatim. This skill was authored by Enternovate
for the Xavani Agent platform under the MIT license.
