---
sidebar_position: 19
title: "Document Generation"
description: "generate_document tool — pptx/xlsx/docx with quality presets"
---

# Document Generation

The `generate_document` tool creates styled PowerPoint, Excel, and Word
files. Every preset enforces one visual system: font family, heading
scale, accent color, and table styling stay consistent across the file.

## Presets

| Preset | Font | Look |
|---|---|---|
| corporate | Calibri | Navy accents; default for business decks |
| minimal | Helvetica | Monochrome; clean product docs |
| report | Georgia | Deep red accents; written reports |

## Usage

Ask in chat, or call the tool directly:

```
generate_document(
  path="~/reports/q3.pptx", kind="pptx",
  title="Q3 Review",
  slides=[{title: "Revenue", bullets: ["Up 12%"]}],
  style="corporate")
```

- `kind=pptx` takes `slides`: a list of `{title, bullets}`.
- `kind=xlsx` takes `sheets`: `{name, header, rows}` per sheet.
  Header rows freeze automatically.
- `kind=docx` takes `sections`: `{title, paragraphs, bullets}` each.
- The file extension is corrected to match `kind`.

The tool is deferred: it costs no schema tokens until needed. Find it
through tool search or enable the files toolset explicitly.

Writer libraries (`python-pptx`, `openpyxl`, `python-docx`) load
lazily. A missing one returns an install hint instead of an error.
