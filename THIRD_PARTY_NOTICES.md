# Third-Party Notices — Xavani Agent

Xavani Agent is developed and published by **Enternovate (Pty) Ltd** and is
distributed under the **MIT License**. See [`LICENSE`](LICENSE) for the full
terms of the license that applies to this repository.

Xavani Agent derives from, ports behavior from, and bundles the third-party
components listed below. The notices in this file are reproduced to satisfy the
license terms of each component. **They are a legal requirement and must not be
removed, shortened, or replaced to satisfy a product-brand scan.**

Functional identifiers are not branding: for example the provider id `nous` and
`NOUS_*` environment variables are API identifiers that an external service
requires, and they stay as they are. Attribution of a third-party work is not a
claim of that party's sponsorship, nor a claim that Enternovate wrote the
upstream code.

---

## 1. Derived work — Hermes Agent (Nous Research, MIT)

Xavani Agent is a **derivative work** of Hermes Agent
(<https://github.com/NousResearch/hermes-agent>), originally developed by Nous
Research and licensed under the MIT License.

> Copyright (c) 2025 Nous Research

The full MIT License text is retained in [`LICENSE`](LICENSE) together with the
copyright line for Enternovate's modifications and additions:

> Copyright (c) 2025-2026 Enternovate (Pty) Ltd

The MIT License requires that the above copyright notice and permission notice
be included in all copies or substantial portions of the Software. Copied
upstream source headers that carry the notice are preserved where the license
requires it.

## 2. Ported behavior — oh-my-pi (MIT)

Parts of this repository are ports of behavior from the **oh-my-pi** project
(<https://github.com/can1357/oh-my-pi>), licensed under the MIT License. The
copyright holders named in the oh-my-pi license are:

> Copyright (c) Mario Zechner
> Copyright (c) Can Bölük
> Copyright (c) Stencil Labs, Inc.

The MIT License text governing those ports is the same MIT License reproduced in
[`LICENSE`](LICENSE).

## 3. Bundled third-party components

These components ship inside this repository and each keeps its own license or
notice file on disk, which remains the authoritative copy.

| Component | License | Copyright / attribution | Notice file |
| --- | --- | --- | --- |
| Xavani Achievements dashboard plugin (vendored; originally authored by [@PCinkusz](https://github.com/PCinkusz)) | MIT | Copyright (c) 2026 Hermes Achievements contributors | `plugins/xavani-achievements/LICENSE` |
| `humanizer` skill | MIT | Copyright (c) 2025 Siqi Chen | `skills/creative/humanizer/LICENSE` (mirrored at `oag_skills/creative/humanizer/LICENSE`) |
| `powerpoint` skill | Anthropic materials license | © 2025 Anthropic, PBC. All rights reserved. | `skills/productivity/powerpoint/LICENSE.txt` (mirrored at `oag_skills/productivity/powerpoint/LICENSE.txt`) |
| Cybersecurity skills (adapted for the Xavani skill loader) | Apache License, Version 2.0 | Copyright (c) mukul975/Anthropic-Cybersecurity-Skills — source commit `9a588e643e36694dc1dafe7acc64589d246cb280`, 754 skills | `optional-skills/cybersecurity/NOTICE` (full details in `optional-skills/cybersecurity/ATTRIBUTION.md`) |

For the Apache-2.0 component, the upstream `NOTICE` file is retained unchanged
at `optional-skills/cybersecurity/NOTICE` and the full license details are in
`optional-skills/cybersecurity/ATTRIBUTION.md`, as required by Section 4 of the
Apache License, Version 2.0.

## 4. Dependencies

Python and JavaScript dependencies are enumerated, with exact pins, in
`uv.lock`, `package-lock.json`, `website/package-lock.json`,
`ui-tui/package-lock.json`, and `web/package-lock.json`. Each dependency
carries its own license, available in its distribution metadata. Dependency
names that merely resemble another project's name (for example the unrelated
`hermes-parser` npm package) are dependency metadata, not product branding, and
are left unmodified.

---

## Keeping this file honest

`scripts/check_product_boundary.py` (Task 24a) verifies, on every run, that:

* both legal files exist and are non-empty;
* the derived-work MIT notice and the Enternovate copyright line are retained in
  `LICENSE`;
* the derived-work ancestor and the upstream ported-project copyright holders
  are named here;
* every bundled notice listed in section 3 exists on disk and is declared in
  this file.

Run it with:

```sh
python3 scripts/check_product_boundary.py
```

Exit code 0 means the product and legal boundary holds.
