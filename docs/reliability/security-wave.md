# R1 security wave — full alert inventory and triage

Uncommitted working document. This is the input for the fix wave and for the final integration report.

## 1. Scope and method

- Repository: `enternovate/xavani-agent` (public).
- Local checkout: `/Users/andilemushwana/xavani-agent`, branch `feat/r1-reliability`, HEAD `50bc6559d15ac4af8d9ce16ae2b44ea4a96482bb`.
- Default branch: `main`. Last CodeQL analysis on `main`: 2026-09-11T22:59:11Z at commit `491121d8`, CodeQL 2.27.0.
- Inventory date: 2026-09-14. All three GitHub alert surfaces were read with `gh api` as account `enternovate`, `per_page=100`, full pagination.
- No dependency pin, lockfile, or source file was changed by this task. Every scanner ran read-only.

### 1.1 Surfaces fetched

| Surface | Endpoint | Open alerts returned |
| --- | --- | --- |
| Dependabot | `GET /repos/enternovate/xavani-agent/dependabot/alerts?state=open` | 32 |
| Code scanning | `GET /repos/enternovate/xavani-agent/code-scanning/alerts?state=open` | 64 |
| Secret scanning | `GET /repos/enternovate/xavani-agent/secret-scanning/alerts?state=open` | 0 |

All three calls returned HTTP 200. No 403 and no missing scope. Token scopes in use: `repo`, `workflow`, `read:org`, `gist`, `delete_repo`.
All 64 code-scanning alerts carry `most_recent_instance.ref == refs/heads/main`, so no explicit `ref=` filter was required.
Secret scanning and secret-scanning push protection are both enabled; non-provider patterns and validity checks are disabled; there are no open secret-scanning alerts.

### 1.2 Dependabot configuration context

`.github/dependabot.yml` is deliberately scoped to the `github-actions` ecosystem only. Source ecosystems (`uv`, `npm`) get no scheduled version PRs;
the 32 alerts below exist because repo-level *Dependabot security updates* is enabled (`security_and_analysis.dependabot_security_updates.status == "enabled"`), which opens a PR only when a published CVE hits a currently-pinned version.

## 2. Summary by category

Categories: **(a)** in-code (non-dependency), **(b)** Python dependency (`uv.lock`), **(c)** Node dependency (`package-lock.json`), **(d)** workflow/CI, **(e)** secret scanning.

| Category | Surface | Alerts | High | Medium | Low |
| --- | --- | --- | --- | --- | --- |
| (a) in-code (CodeQL `py/*`) | code scanning | 49 | 45 | 4 | 0 |
| (d) workflow/CI (CodeQL `actions/*`) | code scanning | 2 | 2 | 0 | 0 |
| (b) Python dependency (`uv.lock`) | Dependabot | 3 | 1 | 1 | 1 |
| (b) Python dependency (`uv.lock`) | code scanning (osv-scanner) | 3 | 1 | 1 | 1 |
| (c) Node dependency (`package-lock.json`) | Dependabot | 29 | 15 | 12 | 2 |
| (c) Node dependency (`package-lock.json`) | code scanning (osv-scanner) | 10 | 8 | 2 | 0 |
| (e) secret scanning | secret scanning | 0 | 0 | 0 | 0 |

Surface totals: **Dependabot 32** (16 high, 13 medium, 3 low); **code scanning 64** (56 high, 7 medium, 1 low); **secret scanning 0**.

### 2.1 Overlap between the two dependency surfaces

The 13 osv-scanner code-scanning alerts are **exact duplicates** of Dependabot alerts at advisory level — they report the same locked CVE against the same lockfile. No osv-scanner alert introduces an advisory that Dependabot does not already report.

| osv-scanner alert | Rule | Manifest | Duplicate of Dependabot |
| --- | --- | --- | --- |
| #1310 | `CVE-2026-82397` | `uv.lock` | #203 (tornado) |
| #1307 | `GHSA-8423-8fgw-73vq` | `uv.lock` | #196 (tornado) |
| #1308 | `GHSA-wwv5-g3v4-889x` | `uv.lock` | #193 (tornado) |
| #1303 | `CVE-2026-73088` | `ui-tui/package-lock.json` | #194, #197, #200 (browserslist) |
| #1304 | `CVE-2026-73088` | `website/package-lock.json` | #194, #197, #200 (browserslist) |
| #1305 | `CVE-2026-73089` | `ui-tui/package-lock.json` | #198, #201 (browserslist) |
| #1306 | `CVE-2026-73089` | `website/package-lock.json` | #198, #201 (browserslist) |
| #1312 | `CVE-2026-75931` | `website/package-lock.json` | #202 (fast-uri) |
| #1313 | `CVE-2026-75975` | `website/package-lock.json` | #210 (fast-uri) |
| #1314 | `CVE-2026-75899` | `website/package-lock.json` | #209 (fast-uri) |
| #1315 | `CVE-2026-76172` | `website/package-lock.json` | #208 (fast-uri) |
| #1309 | `CVE-2026-82417` | `website/package-lock.json` | #206 (qs) |
| #1311 | `CVE-2026-82562` | `website/package-lock.json` | #207 (qs) |

Distinct dependency issues after de-duplication: **21 advisories across 19 (package, manifest) pairs**, from 32 Dependabot alerts.

### 2.2 Distinct issues, counted once

| Set | Count |
| --- | --- |
| Dependabot alerts | 32 (21 distinct advisories) |
| Dependabot alerts, distinct (package, manifest) pairs | 19 |
| CodeQL in-code alerts | 49 (45 share one rule) |
| CodeQL workflow alerts | 2 |
| osv-scanner alerts (duplicates of Dependabot) | 13 |
| Secret-scanning alerts | 0 |
| **Distinct alert records to action (Dependabot + CodeQL)** | **83** |

## 3. Per-alert inventory

### 3.1 (a) In-code alerts — CodeQL `py/*` (49)

Severity below is GitHub's `rule.security_severity_level` (CodeQL raw severity in brackets: `error`/`warning`).
Line numbers are `most_recent_instance.location.start_line` on `refs/heads/main`. Two sites carry two alert IDs each (`agent/model_metadata.py:1523`, `xavani_cli/cli_agent_setup_mixin.py:145`), which is why 45 alerts map to 43 distinct lines.

| Alert | Severity | Rule | Location | Recommended action |
| --- | --- | --- | --- | --- |
| #1299 | high (error) | `py/clear-text-logging-sensitive-data` | `tools/mcp_oauth.py:420` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1302 | high (error) | `py/clear-text-logging-sensitive-data` | `agent/conversation_compression.py:400` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1316 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/_scan_venv_blockers.py:409` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1317 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/agent_import.py:1009` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1318 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/auth.py:7405` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1319 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_agent_setup_mixin.py:145` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1320 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_agent_setup_mixin.py:145` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1321 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2013` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1322 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2015` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1323 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2016` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1324 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2018` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1325 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2041` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1326 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2042` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1327 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2043` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1328 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2044` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1329 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2045` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1330 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2047` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1331 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2048` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1332 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2056` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1333 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2081` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1334 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2082` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1335 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2084` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1336 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2085` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1337 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2087` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1338 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2128` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1339 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2129` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1340 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2131` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1341 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2135` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1342 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2152` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1343 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2153` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1344 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2155` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1345 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2159` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1346 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2147` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1347 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py:2150` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1348 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/moa_cmd.py:19` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1349 | high (error) | `py/clear-text-logging-sensitive-data` | `agent/model_metadata.py:1523` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1350 | high (error) | `py/clear-text-logging-sensitive-data` | `agent/model_metadata.py:1523` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1351 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/prompt_size.py:375` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1352 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/prompt_size.py:377` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1353 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/setup_whatsapp_cloud.py:217` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1354 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/setup_whatsapp_cloud.py:296` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1355 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/setup_whatsapp_cloud.py:387` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1356 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/setup_whatsapp_cloud.py:405` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1357 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/setup_whatsapp_cloud.py:524` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1358 | high (error) | `py/clear-text-logging-sensitive-data` | `xavani_cli/status.py:284` | Confirm FP against `RedactingFormatter`; suppress or dismiss (see 7.1) |
| #1359 | medium (warning) | `py/cookie-injection` | `xavani_cli/dashboard_auth/cookies.py:352` | Mitigated: value is `base64url(JSON)`, a strict subset of cookie-octets — dismiss (see 7.3) |
| #1360 | medium (error) | `py/url-redirection` | `xavani_cli/dashboard_auth/routes.py:220` | Mitigated: `_validate_post_login_target()` enforces same-origin path — dismiss (see 7.4) |
| #1361 | medium (error) | `py/stack-trace-exposure` | `xavani_cli/dashboard_auth/middleware.py:364` | Redact provider exception text before it reaches the 503 body |
| #1362 | medium (error) | `py/stack-trace-exposure` | `xavani_cli/dashboard_auth/middleware.py:467` | Redact provider exception text before it reaches the 503 body |

Clear-text-logging sites, grouped by file:

| File | Sites |
| --- | --- |
| `xavani_cli/cli_commands_mixin.py` | 27 |
| `xavani_cli/setup_whatsapp_cloud.py` | 5 |
| `agent/model_metadata.py` | 2 |
| `xavani_cli/cli_agent_setup_mixin.py` | 2 |
| `xavani_cli/prompt_size.py` | 2 |
| `agent/conversation_compression.py` | 1 |
| `tools/mcp_oauth.py` | 1 |
| `xavani_cli/_scan_venv_blockers.py` | 1 |
| `xavani_cli/agent_import.py` | 1 |
| `xavani_cli/auth.py` | 1 |
| `xavani_cli/moa_cmd.py` | 1 |
| `xavani_cli/status.py` | 1 |

### 3.2 (d) Workflow/CI alerts — CodeQL `actions/*` (2)

| Alert | Severity | Rule | Location | Recommended action |
| --- | --- | --- | --- | --- |
| #1300 | high (error) | `actions/untrusted-checkout-toctou/high` | `.github/workflows/nix-lockfile-fix.yml:211` | Mitigating controls present (inlined actions, `clean: false`); config exclusion ID is wrong — fix ID then dismiss (see 7.2) |
| #1301 | high (error) | `actions/untrusted-checkout/high` | `.github/workflows/nix-lockfile-fix.yml:211` | Mitigating controls present (inlined actions, `clean: false`); config exclusion ID is wrong — fix ID then dismiss (see 7.2) |

Rule message: Insufficient protection against execution of untrusted code on a privileged workflow (issue_comment).

### 3.3 (b) Python dependency alerts — `uv.lock`

Current version is read from `uv.lock` locally; fixed version is `security_vulnerability.first_patched_version` from the advisory.

| Alert | Surface | Severity | Package | Current -> fixed | CVSS | Advisory | Recommended action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #193 | Dependabot | low | `tornado` | `6.5.7` -> `6.5.8` | 0.0 | GHSA-wwv5-g3v4-889x | Bump `tornado` to 6.5.8 via `uv lock --upgrade-package tornado` |
| #196 | Dependabot | medium | `tornado` | `6.5.7` -> `6.5.8` | 0.0 | GHSA-8423-8fgw-73vq | Bump `tornado` to 6.5.8 via `uv lock --upgrade-package tornado` |
| #203 | Dependabot | high | `tornado` | `6.5.7` -> `6.5.8` | 7.5 | CVE-2026-82397 | Bump `tornado` to 6.5.8 via `uv lock --upgrade-package tornado` |
| #1307 | code scanning (osv-scanner) | medium | `tornado` | `6.5.7` -> `6.5.8` | n/a | `GHSA-8423-8fgw-73vq` | Same pin move as above; closes automatically |
| #1308 | code scanning (osv-scanner) | low | `tornado` | `6.5.7` -> `6.5.8` | n/a | `GHSA-wwv5-g3v4-889x` | Same pin move as above; closes automatically |
| #1310 | code scanning (osv-scanner) | high | `tornado` | `6.5.7` -> `6.5.8` | n/a | `CVE-2026-82397` | Same pin move as above; closes automatically |

Dependency path: `tornado` is **transitive** in `uv.lock`, pulled in by `python-telegram-bot==22.6`, which is pinned in the `messaging` extra (`pyproject.toml` lines 118 and 165). `uv.lock` line 3444 pins `tornado` 6.5.7.

### 3.4 (c) Node dependency alerts — `package-lock.json`

Current version is read from the relevant `package-lock.json`; where a lockfile holds several copies, the copy inside the vulnerable range is the one shown.

| Alert | Surface | Severity | Package | Manifest | Current -> fixed | CVSS | Advisory | Recommended action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| #221 | Dependabot | high | `sharp` | `scripts/whatsapp-bridge/package-lock.json` | `0.35.3` -> `0.35.4` | 0.0 | GHSA-rgj7-g3m4-5g8c | Add `overrides.sharp` in that workspace |
| #194 | Dependabot | high | `browserslist` | `ui-tui/package-lock.json` | `4.28.6` -> `4.28.7` | 7.5 | CVE-2026-73088 | Add `overrides.browserslist` in that workspace |
| #223 | Dependabot | high | `js-yaml` | `ui-tui/package-lock.json` | `4.3.1` -> `4.3.2` | 7.5 | CVE-2026-84375 | Raise `overrides["js-yaml@4.x"]` from `^4.3.1` to `^4.3.2` in that workspace |
| #197 | Dependabot | high | `browserslist` | `web/package-lock.json` | `4.28.6` -> `4.28.7` | 7.5 | CVE-2026-73088 | Add `overrides.browserslist` in that workspace |
| #198 | Dependabot | high | `browserslist` | `web/package-lock.json` | `4.28.6` -> `4.28.7` | 7.5 | CVE-2026-73089 | Add `overrides.browserslist` in that workspace |
| #224 | Dependabot | high | `js-yaml` | `web/package-lock.json` | `4.3.1` -> `4.3.2` | 7.5 | CVE-2026-84375 | Raise `overrides["js-yaml@4.x"]` from `^4.3.1` to `^4.3.2` in that workspace |
| #200 | Dependabot | high | `browserslist` | `website/package-lock.json` | `4.28.2` -> `4.28.7` | 7.5 | CVE-2026-73088 | Add `overrides.browserslist` in that workspace |
| #201 | Dependabot | high | `browserslist` | `website/package-lock.json` | `4.28.2` -> `4.28.7` | 7.5 | CVE-2026-73089 | Add `overrides.browserslist` in that workspace |
| #202 | Dependabot | high | `fast-uri` | `website/package-lock.json` | `3.1.5` -> `3.1.6` | 7.5 | CVE-2026-75931 | Add `overrides.fast-uri` in that workspace |
| #208 | Dependabot | high | `fast-uri` | `website/package-lock.json` | `3.1.5` -> `3.1.6` | 7.5 | CVE-2026-76172 | Add `overrides.fast-uri` in that workspace |
| #209 | Dependabot | high | `fast-uri` | `website/package-lock.json` | `3.1.5` -> `3.1.6` | 7.5 | CVE-2026-75899 | Add `overrides.fast-uri` in that workspace |
| #210 | Dependabot | high | `fast-uri` | `website/package-lock.json` | `3.1.5` -> `3.1.6` | 7.5 | CVE-2026-75975 | Add `overrides.fast-uri` in that workspace |
| #225 | Dependabot | high | `js-yaml` | `website/package-lock.json` | `4.3.1` -> `4.3.2` | 7.5 | CVE-2026-84375 | Raise `overrides["js-yaml@4.x"]` from `^4.3.1` to `^4.3.2` in that workspace |
| #213 | Dependabot | high | `svgo` | `website/package-lock.json` | `4.0.2` -> `4.1.0` | 8.2 | CVE-2026-84370 | Raise the existing `css-minimizer-webpack-plugin` override; add `overrides["svgo@3.x"]` in that workspace |
| #216 | Dependabot | high | `svgo` | `website/package-lock.json` | `3.3.4` -> `3.3.5` | 8.2 | CVE-2026-84370 | Raise the existing `css-minimizer-webpack-plugin` override; add `overrides["svgo@3.x"]` in that workspace |
| #204 | Dependabot | medium | `qs` | `scripts/whatsapp-bridge/package-lock.json` | `6.15.2` -> `6.16.0` | 5.3 | CVE-2026-82417 | Add `overrides.qs` in that workspace |
| #205 | Dependabot | medium | `qs` | `scripts/whatsapp-bridge/package-lock.json` | `6.15.2` -> `6.16.0` | 3.7 | CVE-2026-82562 | Add `overrides.qs` in that workspace |
| #217 | Dependabot | medium | `@vitest/mocker` | `ui-tui/package-lock.json` | `4.1.6` -> `4.1.11` | 5.9 | CVE-2026-84373 | Follows the direct `vitest` bump in that workspace |
| #219 | Dependabot | medium | `baseline-browser-mapping` | `ui-tui/package-lock.json` | `2.10.43` -> `2.11.0` | 0.0 | CVE-2026-45819 | Add `overrides.baseline-browser-mapping` in that workspace |
| #218 | Dependabot | medium | `vitest` | `ui-tui/package-lock.json` | `4.1.6` -> `4.1.11` | 5.9 | CVE-2026-84373 | Direct dep: raise `devDependencies.vitest` to `^4.1.11` in that workspace |
| #220 | Dependabot | medium | `baseline-browser-mapping` | `web/package-lock.json` | `2.10.43` -> `2.11.0` | 0.0 | CVE-2026-45819 | Add `overrides.baseline-browser-mapping` in that workspace |
| #222 | Dependabot | medium | `colord` | `web/package-lock.json` | `2.9.3` -> `2.9.4` | 0.0 | CVE-2026-85062 | Add `overrides.colord` in that workspace |
| #199 | Dependabot | medium | `sanitize-html` | `web/package-lock.json` | `2.17.6` -> `2.17.7` | 5.4 | CVE-2026-84371 | Add `overrides.sanitize-html` in that workspace |
| #206 | Dependabot | medium | `qs` | `website/package-lock.json` | `6.15.2` -> `6.16.0` | 5.3 | CVE-2026-82417 | Add `overrides.qs` in that workspace |
| #207 | Dependabot | medium | `qs` | `website/package-lock.json` | `6.15.2` -> `6.16.0` | 3.7 | CVE-2026-82562 | Add `overrides.qs` in that workspace |
| #214 | Dependabot | medium | `svgo` | `website/package-lock.json` | `4.0.2` -> `4.1.0` | 6.1 | CVE-2026-84369 | Raise the existing `css-minimizer-webpack-plugin` override; add `overrides["svgo@3.x"]` in that workspace |
| #215 | Dependabot | medium | `svgo` | `website/package-lock.json` | `3.3.4` -> `3.3.5` | 6.1 | CVE-2026-84369 | Raise the existing `css-minimizer-webpack-plugin` override; add `overrides["svgo@3.x"]` in that workspace |
| #211 | Dependabot | low | `joi` | `website/package-lock.json` | `18.2.1` -> `18.2.5` | 3.7 | CVE-2026-84368 | Raise `overrides.joi` from `^18.2.1` to `^18.2.5` in that workspace |
| #212 | Dependabot | low | `joi` | `website/package-lock.json` | `18.2.1` -> `18.2.4` | 3.7 | CVE-2026-84367 | Raise `overrides.joi` from `^18.2.1` to `^18.2.5` in that workspace |
| #1303 | code scanning (osv-scanner) | high | `browserslist` | `ui-tui/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-73088` | Same pin move; closes automatically |
| #1305 | code scanning (osv-scanner) | high | `browserslist` | `ui-tui/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-73089` | Same pin move; closes automatically |
| #1304 | code scanning (osv-scanner) | high | `browserslist` | `website/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-73088` | Same pin move; closes automatically |
| #1306 | code scanning (osv-scanner) | high | `browserslist` | `website/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-73089` | Same pin move; closes automatically |
| #1312 | code scanning (osv-scanner) | high | `fast-uri` | `website/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-75931` | Same pin move; closes automatically |
| #1313 | code scanning (osv-scanner) | high | `fast-uri` | `website/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-75975` | Same pin move; closes automatically |
| #1314 | code scanning (osv-scanner) | high | `fast-uri` | `website/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-75899` | Same pin move; closes automatically |
| #1315 | code scanning (osv-scanner) | high | `fast-uri` | `website/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-76172` | Same pin move; closes automatically |
| #1309 | code scanning (osv-scanner) | medium | `qs` | `website/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-82417` | Same pin move; closes automatically |
| #1311 | code scanning (osv-scanner) | medium | `qs` | `website/package-lock.json` | see Dependabot row above | n/a | `CVE-2026-82562` | Same pin move; closes automatically |

Manifest spread of the 29 Dependabot Node alerts:

| Manifest | Alerts | Direct dependencies among them |
| --- | --- | --- |
| `website/package-lock.json` | 15 | none (all transitive) |
| `web/package-lock.json` | 6 | none (all transitive) |
| `ui-tui/package-lock.json` | 5 | `vitest` |
| `scripts/whatsapp-bridge/package-lock.json` | 3 | none (all transitive) |

Only `vitest` in `ui-tui/package-lock.json` is a declared (direct) dependency. `js-yaml` is declared directly in `web/package.json` and `website/package.json` at `^5.2.1`,
but the locked 5.3.0 / 5.2.3 copies are outside the vulnerable range — every flagged `js-yaml` instance is a nested 4.3.1 copy pulled in transitively, so raising the declared range does not fix it.

### 3.5 (e) Secret scanning — 0

`GET /repos/enternovate/xavani-agent/secret-scanning/alerts?state=open` returned `[]`. Secret scanning and push protection are enabled on the repository; nothing to triage.
## 4. Top findings by severity

Ranked by severity, then CVSS where an advisory carries one, then blast radius. `file:line` is given for in-code and workflow items.

| # | Severity | Finding | Location | Why it ranks here |
| --- | --- | --- | --- | --- |
| 1 | high | `svgo` executable-link bypass (CVE-2026-84370) | `website/package-lock.json` — `node_modules/svgo@3.3.4` and `node_modules/css-minimizer-webpack-plugin/node_modules/svgo@4.0.2` | Highest CVSS in the set (8.2). Two locked copies in range; runs at docs-site build time over SVG assets. |
| 2 | high | Privileged-workflow untrusted checkout (`actions/untrusted-checkout/high`, `actions/untrusted-checkout-toctou/high`) | `.github/workflows/nix-lockfile-fix.yml:211` | The only findings where untrusted input meets a privileged `issue_comment` workflow. Mitigations exist, but the repository exclusion does not match the emitted rule IDs. |
| 3 | high | 45 × `py/clear-text-logging-sensitive-data` | `xavani_cli/cli_commands_mixin.py` (27 sites), `xavani_cli/setup_whatsapp_cloud.py` (5), `agent/model_metadata.py:1523` (2), `xavani_cli/cli_agent_setup_mixin.py:145` (2), `xavani_cli/prompt_size.py:375,377`, `xavani_cli/dashboard_auth/middleware.py`, `xavani_cli/auth.py:7405`, `tools/mcp_oauth.py:420`, `agent/conversation_compression.py:400`, `xavani_cli/_scan_venv_blockers.py:409`, `xavani_cli/agent_import.py:1009`, `xavani_cli/moa_cmd.py:19`, `xavani_cli/status.py:284` | Largest single block of alerts (45 of 64). A repository-level exclusion already exists for this query, so it is a policy/config problem rather than 45 separate fixes. |
| 4 | high | `browserslist` prototype write + unbounded memory growth (CVE-2026-73088, CVE-2026-73089) | `ui-tui/package-lock.json` (`4.28.6`), `web/package-lock.json` (`4.28.6`), `website/package-lock.json` (`4.28.2`) | CVSS 7.5, three workspaces at once, and the most duplicated advisory across both surfaces (5 Dependabot + 4 osv-scanner alerts). |
| 5 | high | `fast-uri` host confusion / SSRF (CVE-2026-75899, -75931, -75975, -76172) | `website/package-lock.json` — `node_modules/fast-uri@3.1.5` | CVSS 7.5 against a single locked copy, four advisories, SSRF class. |
| 6 | high | `tornado` urlencoded-body parsing omits `max_num_fields` (CVE-2026-82397) | `uv.lock` — `tornado` 6.5.7, package block at line 3444 | CVSS 7.5 and the only Python dependency finding. Ships through the `messaging` extra. |
| 7 | high | `js-yaml` `maxTotalMergeKeys` CPU exhaustion (CVE-2026-84375) | `ui-tui/package-lock.json`, `web/package-lock.json`, `website/package-lock.json` — nested `js-yaml@4.3.1` | CVSS 7.5. The existing `overrides["js-yaml@4.x"] = ^4.3.1` sits exactly one patch below the fix. |
| 8 | high | `sharp` / libheif (GHSA-g89c-p67h-r497, GHSA-2jg2-4ch7-h545) | `scripts/whatsapp-bridge/package-lock.json` — `node_modules/sharp@0.35.3` | High with no CVSS vector published. Local-only bridge script, but the bump to `0.35.4` is free. |
| 9 | medium | `py/stack-trace-exposure` | `xavani_cli/dashboard_auth/middleware.py:364`, `xavani_cli/dashboard_auth/middleware.py:467` | The only in-code findings that look genuine: the 503 body interpolates `str(e)` from a `ProviderError`. The same pattern exists at `xavani_cli/dashboard_auth/routes.py:233`. |
| 10 | medium | `qs` array-limit bypass + `isBuffer` DoS (CVE-2026-82417, CVE-2026-82562) | `website/package-lock.json` and `scripts/whatsapp-bridge/package-lock.json` — `qs@6.15.2` | CVSS 5.3 / 3.7, transitive through `express` and `body-parser`. |

Medium items outside the top ten: `py/cookie-injection` (`xavani_cli/dashboard_auth/cookies.py:352`), `py/url-redirection` (`xavani_cli/dashboard_auth/routes.py:220`), `sanitize-html` (`web`), `colord` (`web`), `baseline-browser-mapping` (`web`, `ui-tui`), `@vitest/mocker` and `vitest` (`ui-tui`), `joi` (`website`).

## 5. Local scanner results

### 5.1 Bandit 1.9.4 — ran

```sh
bandit -r xavani_cli agent tools gateway -x '*/tests/*,*/build/*' -q        # text report
bandit -r xavani_cli agent tools gateway -x '*/tests/*,*/build/*' -f json   # counting pass
```

- Interpreter `/Library/Frameworks/Python.framework/Versions/3.14/bin/python`, bandit 1.9.4. Runtime about 10 s, well inside the 180 s bound.
- Files scanned: **669**. Lines of code: **325,870**.
- Results: **2,394** — 4 HIGH, 130 MEDIUM, 2,260 LOW. Confidence: 2,043 HIGH, 342 MEDIUM, 9 LOW.
- `nosec` annotations resolved by Bandit: 0. Tests skipped because a comment token could not be resolved as a test name: 8.
- Exit code 1 (findings present). Bandit scans a wider tree than the CI job, which runs `-ll`; the MEDIUM/LOW volume is expected and is not a regression against CI.

HIGH severity, all four:

| Location | Test | Finding |
| --- | --- | --- |
| `tools/marketplace.py:97` | B202 | `tarfile.extractall` used without member validation |
| `xavani_cli/bang_shell.py:176` | B602 | `subprocess` call with `shell=True` |
| `xavani_cli/cli_commands_mixin.py:3570` | B602 | `subprocess` call with `shell=True` |
| `xavani_cli/mcp_catalog.py:476` | B602 | `subprocess` call with `shell=True` |

MEDIUM severity by rule:

| Rule | Count |
| --- | --- |
| B310 — blacklist — urllib/open URL schemes | 50 |
| B608 — hardcoded_sql_expressions (f-string SQL) | 43 |
| B108 — hardcoded_tmp_directory | 19 |
| B104 — hardcoded_bind_all_interfaces | 16 |
| B307 — blacklist — eval | 1 |
| B314 — blacklist — xml.etree | 1 |

MEDIUM concentrates in `xavani_cli/session_recovery.py` (16), `xavani_cli/models.py` (13), `xavani_cli/kanban_db.py` (8), `xavani_cli/session_lost_and_found.py` (5), then a long tail.

Bandit reported no HIGH or MEDIUM finding inside the files CodeQL flagged for clear-text logging. The two scanners disagree on that query class, which is consistent with the documented false-positive position in 7.1 (Bandit does not model the redacting log formatter either, but it did not flag the same sites).

### 5.2 npm audit — ran

```sh
npm audit --json --package-lock-only   # . , website , web , ui-tui , scripts/whatsapp-bridge
```

Lockfile and manifest hashes were captured before and after the run; all are byte-identical, so `npm audit` modified nothing.

| Workspace | total | high | moderate | low |
| --- | --- | --- | --- | --- |
| `.` (root) | 0 | 0 | 0 | 0 |
| `website` | 26 | 22 | 3 | 1 |
| `web` | 5 | 2 | 3 | 0 |
| `ui-tui` | 5 | 2 | 3 | 0 |
| `scripts/whatsapp-bridge` | 4 | 1 | 3 | 0 |

npm audit counts vulnerable *packages*; Dependabot counts *advisories*. Per workspace:

| Workspace | npm audit packages (high/moderate/low) | Dependabot packages | Packages npm audit finds that Dependabot does not |
| --- | --- | --- | --- |
| `.` (root) | 0 | 0 | none |
| `web` | 5 (2/3/0) | 5 | none |
| `ui-tui` | 5 (2/3/0) | 5 | none |
| `scripts/whatsapp-bridge` | 4 (1/3/0) | 2 | `body-parser`, `express` (both via `qs`) |
| `website` | 26 (22/3/1) | 6 | `image-size`, 16 `@docusaurus/*` packages, `body-parser`, `express` |

`web` and `ui-tui` cover the same package set as Dependabot. **`website` and `scripts/whatsapp-bridge` do not**, and the `website` gap is the large one.

Extra findings in `website` with no matching Dependabot alert:

| Package | Severity | Via | fixAvailable |
| --- | --- | --- | --- |
| `image-size` | high | direct advisory — ICNS parser infinite loop; JXL and HEIF parser infinite loops | false |
| `@docusaurus/mdx-loader`, `@docusaurus/theme-common` | high | `image-size` | false |
| `@docusaurus/core`, `@docusaurus/plugin-content-docs`, `plugin-svgr`, `plugin-css-cascade-layers`, `plugin-google-tag-manager`, `preset-classic` | high | `@docusaurus/core` / `mdx-loader` | false |
| `body-parser` | moderate | `qs` | true |
| `express` | moderate | `qs` | true |

The `@docusaurus/*` cluster is one upstream root cause (`image-size`) with no fix available today. Dependabot has no advisory open for `image-size`, so the gap has to be tracked from the scanner rather than from the Security tab. The `scripts/whatsapp-bridge` extras (`body-parser`, `express`) are transitive through `qs` and close with the same `qs` override.

### 5.3 Scanners not installed locally

| Tool | Status |
| --- | --- |
| `gitleaks` | not installed — absent from PATH, `/opt/homebrew/bin`, `/usr/local/bin`, Homebrew, and `~/go/bin` |
| `trufflehog` | not installed |
| `semgrep` | not installed |
| `pip-audit` | not installed |
| `safety` | not installed |
| `trivy` | not installed |
| `osv-scanner` | not installed — CI runs it through `google/osv-scanner-action` v2.5.0; local findings were taken from the code-scanning surface |

No secret scanner ran locally, so the zero secret-scanning count comes only from the GitHub surface. `security.yml` already runs `gitleaks/gitleaks-action` and `pip-audit` in CI; having both available locally would let the same checks run before push.
## 6. Proposed fix order

In-code first, then direct pins, then transitive bumps, then dismissals. Each wave is independently verifiable.

### Wave A — in-code (no dependency change)

| Step | Items | Change |
| --- | --- | --- |
| A1 | `py/stack-trace-exposure` ×2 → alerts #1361, #1362 | Redact the provider exception in the 503 body at `xavani_cli/dashboard_auth/middleware.py:364` and `:467`. Apply the same treatment to the sibling leak at `xavani_cli/dashboard_auth/routes.py:233`, which the scanner did not raise but which carries identical text. Close both alerts when the next `main` analysis reports them fixed. |
| A2 | CodeQL config effectiveness | Resolve the config gap in 7.5 before touching the 45 clear-text-logging alerts. Outcome decides whether wave A3 is "fix" or "dismiss". |
| A3 | `actions/untrusted-checkout*` ×2 → alerts #1300, #1301 | Correct the exclusion IDs in `.github/codeql/codeql-config.yml`, then dismiss. |
| A4 | `py/cookie-injection` #1359, `py/url-redirection` #1360 | Already mitigated in code (7.3, 7.4). Dismiss with rationale. |

### Wave B — direct dependency pins (1 item)

| Item | Change | Closes |
| --- | --- | --- |
| `ui-tui/package.json` | `devDependencies.vitest` `^4.1.3` → `^4.1.11`, then regenerate `ui-tui/package-lock.json` | #218 (`vitest`) and #217 (`@vitest/mocker`, which follows) |

### Wave C — raise existing overrides (repo already uses this pattern)

`website/package.json` already declares `overrides` for `joi` and `js-yaml@4.x`; those floors sit exactly one patch below the fixes, which is why the alerts exist. Raise them rather than adding a new mechanism.

| Workspace | Override | From | To | Closes |
| --- | --- | --- | --- | --- |
| `website` | `overrides["js-yaml@4.x"]` | `^4.3.1` | `^4.3.2` | #225 |
| `website` | `overrides.joi` | `^18.2.1` | `^18.2.5` | #211, #212 |
| `website` | new `overrides["svgo@3.x"]` | — | `^3.3.5` | #215, #216 |
| `website` | `overrides["css-minimizer-webpack-plugin"]` chain | `^7.0.4` | keep, but add `overrides["svgo@4.x"] = ^4.1.0` | #213, #214 |

### Wave D — new transitive overrides

| Workspace | Override | Target | Closes |
| --- | --- | --- | --- |
| `website` | `browserslist` | `^4.28.7` | #200, #201 |
| `website` | `fast-uri` | `^3.1.6` | #202, #208, #209, #210 |
| `website` | `qs` | `^6.16.0` | #206, #207 |
| `web` | `browserslist` | `^4.28.7` | #197, #198 |
| `web` | `overrides["js-yaml@4.x"]` | `^4.3.2` | #224 |
| `web` | `baseline-browser-mapping` | `^2.11.0` | #220 |
| `web` | `colord` | `^2.9.4` | #222 |
| `web` | `sanitize-html` | `^2.17.7` | #199 |
| `ui-tui` | `browserslist` | `^4.28.7` | #194 |
| `ui-tui` | `overrides["js-yaml@4.x"]` | `^4.3.2` | #223 |
| `ui-tui` | `baseline-browser-mapping` | `^2.11.0` | #219 |
| `scripts/whatsapp-bridge` | `qs` | `^6.16.0` | #204, #205 |
| `scripts/whatsapp-bridge` | `sharp` | `^0.35.4` | #221 |

Do not hand-edit lockfiles. Raise the override, then regenerate each lockfile with the workspace package manager, and confirm the resolved versions land at or above the fixed versions in section 3.4.

### Wave E — Python dependency (1 item)

| Item | Change | Closes |
| --- | --- | --- |
| `uv.lock` | `tornado` 6.5.7 → 6.5.8 via `uv lock --upgrade-package tornado` | Dependabot #193, #196, #203 and osv-scanner #1307, #1308, #1310 |

Preferred over loosening `python-telegram-bot==22.6`: the exact pin on the direct dependency is intentional, and a targeted package upgrade moves only `tornado`. If `uv` resolves away from the target, add an explicit `tornado>=6.5.8` constraint near the `messaging` extra instead.

### Wave F — re-scan and close out

1. Re-run CodeQL (`main` analysis) and osv-scanner; re-run Bandit and npm audit locally.
2. Confirm the Dependabot count falls to the dismissal-only residue.
3. Apply the dismissals in section 7 with the exact rationale text, choosing a dismissal reason for each (`false positive` or `won't fix`).
4. Record the residual `image-size` / `@docusaurus` cluster as accepted-with-tracking, since no fix exists upstream.

## 7. Dismissal candidates and rationale

### 7.1 — the 45 `py/clear-text-logging-sensitive-data` alerts (alerts #1299, #1302, #1316-#1358) — dismiss candidate

Rationale for dismissal: `.github/codeql/codeql-config.yml` already excludes this query with a written rationale — every log handler routes through `RedactingFormatter` in `xavani_logging.py`, which replaces API keys, tokens, passwords and private keys with `[REDACTED]` before emission, and CodeQL taint-tracks individual `log`/`print` call sites without seeing the formatter above them.

Evidence gathered for this triage:

- The flagged expressions print CLI/cron identifiers, not credentials. Spot-checks: `xavani_cli/cli_commands_mixin.py:2013-2018` prints `job_id`, `schedule`, `skills`, `prompt_preview`, `next_run_at`; `:2081-2085` prints the created job's ID and schedule; `:2150-2159` prints job `name` and ID. `xavani_cli/auth.py:7405` prints an upgrade URL. `xavani_cli/cli_agent_setup_mixin.py:145` prints `base_url` and a source label.
- Bandit, which scans the same tree, raised no HIGH or MEDIUM finding at any of these sites (section 5.1).
- The query is one rule; the 45 alerts are 43 distinct lines. Fixing them one by one would add suppression comments at 43 sites for an already-excluded query.

Do not dismiss before resolving 7.5. If the config is not actually applied, dismissal would hide unanalysed code rather than a known false positive.

### 7.2 — the 2 `actions/untrusted-checkout*` alerts (alerts #1300, #1301) — dismiss candidate

Rationale for dismissal: `.github/codeql/codeql-config.yml` excludes this class with a written rationale (subsequent actions are inlined and not loaded from the checkout), and the file is already listed in `path_filters`.

Two corrections are needed before dismissing:

- The exclusion IDs are `actions/checkout-untrusted` and `actions/untrusted-checkout-toctou`, but the emitted rule IDs are `actions/untrusted-checkout/high` and `actions/untrusted-checkout-toctou/high`. The IDs do not match, so the exclusions cannot be matching these alerts.
- The config comment states the workflow uses `persist-credentials: false`, while `.github/workflows/nix-lockfile-fix.yml` checks out with `persist-credentials: true`. Resolve the discrepancy (either change the workflow or the comment) before the dismissal is defensible.

### 7.3 — `py/cookie-injection` (alert #1359, `xavani_cli/dashboard_auth/cookies.py:352`) — dismiss candidate

Rationale: the cookie value is `base64url(JSON)`. The urlsafe base64 alphabet is a strict subset of the RFC 6265 cookie-octet set, so no `;`, `"` or `\` can reach the header. The docstring at lines 302-322 documents this deliberately, including why padding is stripped. No header-injection path exists.

### 7.4 — `py/url-redirection` (alert #1360, `xavani_cli/dashboard_auth/routes.py:220`) — dismiss candidate

Rationale: the redirect target is built from `_validate_post_login_target(next)` (`routes.py:625`), which requires the decoded value to start with `/`, rejects `//`, rejects `/login`, `/auth/`, `/api/auth/` and `/api/*`, and returns an empty string otherwise. Only same-origin paths can reach `RedirectResponse`, and the surviving value is percent-encoded with `quote(safe_next, safe="")`.

### 7.5 — config-effectiveness finding that gates the dismissals above

`.github/codeql/codeql-config.yml` declares `path_filters` and `query_filters`, but no workflow in `.github/workflows/` references that file, and the API shows the repository is on CodeQL **default setup** (`state: configured`; languages `actions`, `javascript`, `javascript-typescript`, `python`, `ruby`, `typescript`; query suite `default`; last updated 2026-08-01).

Observed analysis results, `code-scanning/analyses`:

| Ref | Created | CodeQL | Python results | Rules |
| --- | --- | --- | --- | --- |
| `refs/heads/main` | 2026-09-11T22:59:11Z | 2.27.0 | 417 | 43 |
| `refs/heads/main` | 2026-09-08T10:15:29Z | 2.26.4 | 417 | 43 |
| `refs/heads/main` | 2026-09-05T20:13:10Z | 2.26.4 | 374 | 43 |
| `refs/pull/118/head` | 2026-09-14T06:54:56Z | 2.27.0 | 2 | 43 |
| `refs/pull/118/head` | 2026-09-14T06:15:19Z – 06:43:03Z (5 runs) | 2.27.0 | 0 | 43 |

Interpretation: `rules_count` is 43 in every analysis, so the query set in effect is the unfiltered default suite, and the `main` analyses continue to produce 374-417 Python results. The exclusions in `codeql-config.yml` are therefore not visibly taking effect on `main`; the low counts on the pull-request refs are not evidence that they are.

Two possible resolutions:

1. Keep default setup but move the filter list into an advanced-setup workflow (`github/codeql-action/init` with `config-file: .github/codeql/codeql-config.yml`), where `path_filters` / `query_filters` are honoured by contract. That also lets the ignored-file list and the rule-ID corrections in 7.2 be verified in the same change.
2. Keep default setup and dismiss the affected alerts individually, accepting that the query keeps re-firing on each `main` analysis.

Option 1 is the only one that stops the 45 alerts from reappearing after dismissal. Confirm the behaviour before starting wave A3.

### 7.6 — explicitly NOT dismissal candidates

| Item | Why not dismissed |
| --- | --- |
| `py/stack-trace-exposure` (#1361, #1362) | The config rationale covers HTTP 500 responses; these are 503 responses that interpolate `str(e)`, a different path. Fix in code. |
| All 32 Dependabot alerts | Fixed versions are published for every one of them; `first_patched_version` was present on all 32, so no advisory requires upstream work. |
| `image-size` / `@docusaurus/*` cluster | Not a dismissal candidate in the "false positive" sense — it is a genuine unfixed upstream advisory. Track as accepted risk with a review date, not as a false positive. |
| `sharp` in `scripts/whatsapp-bridge` | Technically dismissible (local-only one-shot Docker script, already path-excluded from CodeQL), but the fix is a one-line override and the package is genuinely reachable from attacker-supplied media files in that script. Fix instead. |

## 8. Limits of this inventory

- Counts are a point-in-time read of 2026-09-14. Dependabot and CodeQL are both live; the numbers will move on the next `main` analysis.
- No fix was applied and nothing was re-run against the fixed state, so the fix order in section 6 is a proposal, not a verified sequence.
- Fixed-version values come from `security_vulnerability.first_patched_version` on Dependabot alerts, not from a resolve step. Wave F must confirm the resolved versions match.
- No secret scanner ran locally; the zero secret-scanning count is a GitHub-surface reading.
- Bandit is the only local SAST that ran. Semgrep, pip-audit and gitleaks are not installed, so the code-scanning inventory for those classes rests on CodeQL and osv-scanner alone.
- The `website` and `scripts/whatsapp-bridge` workspaces have npm-audit findings that no GitHub alert covers (section 5.2), most of them in the unfixed `image-size` / `@docusaurus` chain. Those are not part of the 96 GitHub alerts and are reported here only as a gap.

---

## Wave execution results (2026-09-14)

### 28b-2a - Python-side fixes (commit f9b621ff)

- Bandit HIGH: 4 -> 0 repo tree. Real fixes: `tools/marketplace.py`
  (member-by-member extract after traversal checks),
  `xavani_cli/cli_commands_mixin.py` (editor launch is argv-only).
  Documented `# nosec B602` + rationale: `xavani_cli/bang_shell.py`,
  `xavani_cli/mcp_catalog.py` (local, user/manifest-supplied commands).
- In-code code-scanning (49): real fixes - generic 503 bodies with
  server-side logging (`dashboard_auth/middleware.py`, `routes.py` x2),
  same-origin redirect guard (`_is_same_origin_path`); cookie value
  assessed and documented; 43 `# nosec B105` markers with per-line
  rationales for diagnostic logging.
- tornado 6.5.7 -> 6.5.8 in uv.lock (transitive via python-telegram-bot).
- CAVEAT: `# nosec` is a Bandit directive; CodeQL does not consume it.
  The 45 `py/clear-text-logging-sensitive-data` alerts need dismissals or
  the advanced-setup switch (runbook below).

### 28b-2b - Node dependencies (commit 58e12f44)

- npm audit 40 -> 18 across website/web/ui-tui/whatsapp-bridge.
- web, ui-tui, whatsapp-bridge: 0. website: 18 remaining, all one chain
  (`image-size@2.0.2` via `@docusaurus/mdx-loader`; no patched release
  exists upstream). No forced majors; vitest pinned ^4.1.11.

### 28a - Adversarial corpus

- Desktop (commit 9918fd2): 74 attack cases; FOUND + FIXED a CRITICAL
  filter bypass (symlinked-prefix spelling disabled every denylist) and a
  HIGH case-variant control-dir write (`.GIT/config`). Both are
  regression-pinned by the tests that found them.
- Agent (commit 62064f0f): 28 cases, all defenses hold; 3 LOW findings
  documented as explicit limitation tests (approval pattern-binding;
  receipt-store local trust; hashline drift warning).

### Owner runbook - closing the CodeQL alerts

Pick either path:

1. **Dismiss the 45 logging alerts** at
   https://github.com/enternovate/xavani-agent/security/code-scanning
   ("Dismiss alert" -> reason "won't fix" -> paste the rationale from this
   file). The account needs the `security_events` scope
   (`gh auth refresh -h github.com -s security_events`), which the current
   `enternovate` token does not carry. Dismiss the 2 `actions/*` alerts the
   same way (design rationale in `.github/codeql/codeql-config.yml`).
2. **Switch to CodeQL advanced setup** (Settings -> Code security ->
   Code scanning -> switch), add a workflow that references
   `.github/codeql/codeql-config.yml` (contents already aligned to the
   emitted rule ids), and let the config suppress the classes it
   documents.

Dependabot counts on GitHub close after this branch merges to `main` and
GitHub rescans; the only expected survivor is the `image-size` chain.
