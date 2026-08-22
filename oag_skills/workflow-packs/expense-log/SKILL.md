---
name: expense-log
description: >
  Expense log pack: capture expenses, categorize them, and export clean CSV on demand.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [expenses,csv,finance,tracking]
---

# Expense Log Pack

## Procedure
1. Append each expense as: date, amount, currency, vendor, category.
2. Categories are fixed: travel, meals, software, hardware, other.
3. On export, write CSV with a header row and ISO dates.
4. Show monthly totals per category before writing the file.

## Output contract
- Capture confirms with the parsed row echoed back.
- Export preview: totals table, then the CSV path.
