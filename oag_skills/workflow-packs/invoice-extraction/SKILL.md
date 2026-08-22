---
name: invoice-extraction
description: >
  Invoice extraction pack: pull vendor, totals, tax, line items, and due dates from invoice text or files into clean JSON.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [invoices,extraction,json,finance]
---

# Invoice Extraction Pack

## Procedure
1. Read the invoice text or image transcript.
2. Extract: vendor, invoice number, issue date, due date,
   currency, subtotal, tax, total.
3. Extract line items: description, quantity, unit price, amount.
4. Verify subtotal + tax == total; flag mismatches instead of guessing.
5. Emit strict JSON matching the bench task schema.

## Output contract
One JSON object; no prose around it. Unknown fields are null, never invented.
