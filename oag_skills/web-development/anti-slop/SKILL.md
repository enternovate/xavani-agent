---
name: anti-slop
description: >
  Anti-slop TS/JS authoring discipline derived from dmmulroy/anti-slop
  (MIT): opinionated Oxlint rules that reject low-evidence TypeScript and
  JavaScript patterns — chained type assertions, unknown/object leakage,
  widen-then-assert flows, module mocking, Reflect escapes, shape-suffixed
  symbols, and more. Includes bad-vs-good examples for each rule, wiring
  instructions for oxlint config in a JS project, a CI gate recipe, and
  judgment rules for justified exceptions. Use when writing or reviewing
  any TypeScript/JavaScript code; never applies to Python.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [typescript, javascript, oxlint, linting, code-quality, review]
    related_skills: [page-agent]
---

# Anti-Slop (TypeScript/JavaScript Lint Discipline)

You are writing or reviewing TypeScript/JavaScript. Low-evidence patterns —
assertions without proof, `unknown`/`object` leaking across boundaries,
types that widen known facts and re-narrow them later — are slop: they
look typed but carry no evidence. This skill encodes the discipline from
[dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop) (MIT), a set of
opinionated Oxlint rules that reject those patterns mechanically.

**Scope guard: this skill applies to TypeScript/JavaScript only. It never
applies to Python** — Python files are governed by ruff and the repo's own
conventions, not by these rules.

## 1. When to Load This Skill

Load when doing any of:

1. Writing new TypeScript/JavaScript code (application code, tests, tooling).
2. Reviewing or refactoring existing TS/JS code.
3. Wiring lint rules into a JS/TS project's oxlint configuration or CI.

Skip entirely for Python work — do not translate these rules onto Python
code or suggest `as`-cast rules for `.py` files.

## 2. The Slop Patterns (Upstream Rule Catalog)

Each rule below is verified against the upstream README. When writing code,
avoid the pattern; when reviewing, flag it.

| Rule | What it rejects |
|---|---|
| `no-chained-type-assertions` | Nested type assertions that fabricate evidence. |
| `no-conditional-empty-object-spread` | Conditional spreads using `{}` to omit fields. |
| `no-known-value-widening` | Explicit broad target types that discard known value evidence. |
| `no-module-mocking` | Vitest/Jest module mocks in favor of real dependency seams. |
| `no-object-parameters` | The broad `object` type on function inputs. |
| `no-reflect-apply` | `Reflect.apply` in favor of typed function calls. |
| `no-reflect-get` | `Reflect.get` in favor of typed property access or boundary parsing. |
| `no-runtime-typeof` | Ad hoc `typeof` narrowing instead of boundary parsing. |
| `no-shape-in-symbol-names` | `shape` in symbol (type/interface) names. |
| `no-unknown-parameters` | `unknown` inputs except the explicit `cause` convention. |
| `no-unknown-returns` | Function contracts returning `unknown` or `Promise<unknown>`. |
| `no-unknown-type-aliases` | Aliases that merely conceal `unknown`. |
| `no-unsafe-dictionary-type` | Dictionary value contracts based on `unknown`, `any`, `object`, `{}`, or semantic equivalents. |
| `no-widen-then-assert` | Local flows that widen known values and later assert them back. |
| `require-safety-comment-for-type-assertion` | Non-const assertions without a documented checked invariant. |

Effect-specific (opt-in, only in Effect repos):

| Rule | What it rejects |
|---|---|
| `no-service-constructor-imports` | Relative project imports of exported `make<CapabilityName>` constructors outside `*.test.*`/`*.spec.*` files; import the owning Layer and yield the contextual service instead. |

## 3. Bad vs Good

Minimal pairs for the rules where the fix is instructive.

### `no-chained-type-assertions`

```ts
// BAD: assertion stacked on assertion — no evidence produced
const user = input as object as User;

// GOOD: validate at the boundary, then the type is earned
const user = parseUser(input); // returns User or throws
```

### `no-conditional-empty-object-spread`

```ts
// BAD: {} as a conditional omission trick
const options = {
  ...(timeout !== undefined ? { timeout } : {}),
};

// GOOD: explicit optional property
const options: Options = { timeout };
```

### `no-known-value-widening`

```ts
// BAD: the known `start` key is discarded by the annotation
const handlers: Record<string, Handler> = {
  start: startHandler,
};

// GOOD: preserve inference; check shape without widening
const handlers = {
  start: startHandler,
} satisfies Record<string, Handler>;
```

### `no-module-mocking`

```ts
// BAD: vi.mock / jest.mock hides the real module
vi.mock("./user-store");

// GOOD: inject a real dependency seam the caller controls
const store = createInMemoryUserStore();
await syncUsers({ store });
```

### `no-object-parameters`

```ts
// BAD: object carries zero type information
function save(value: object) {}

// GOOD: name the actual contract
function save(value: UserRecord) {}
```

### `no-reflect-apply` / `no-reflect-get`

```ts
// BAD
const value = Reflect.apply(operation, owner, args);
const got = Reflect.get(owner, key);

// GOOD: typed calls and property access
const value = operation.apply(owner, args);
const got = owner[key];
```

### `no-runtime-typeof`

```ts
// BAD: ad hoc narrowing scattered through logic
if (typeof input === "string") {
  useName(input);
}

// GOOD: parse once at the boundary; downstream types are trusted
const name = parseName(input);
useName(name);
```

Schema-free projects may allow `typeof` inside type predicate/assertion
functions via config: `"anti-slop/no-runtime-typeof": ["error", { "allowInTypeGuards": true }]`
(defaults to `false`).

### `no-shape-in-symbol-names`

```ts
// BAD: "shape" says nothing the type system doesn't already know
interface UserShape {
  id: string;
}

// GOOD
interface User {
  id: string;
}
```

### `no-unknown-parameters` / `no-unknown-returns` / `no-unknown-type-aliases`

```ts
// BAD: unknown smuggled through signatures and aliases
function handle(input: unknown) {}
function loadUser(): unknown {
  return input;
}
type ExternalValue = unknown;

// GOOD: concrete contracts; `unknown` only as the documented `cause` convention
function handle(input: UserInput) {}
function loadUser(): User {
  return parsed;
}
type FetchError = { cause: unknown };
```

### `no-unsafe-dictionary-type`

```ts
// BAD: dictionary values typed as unknown/any/object/{}
type Metadata = Record<string, unknown>;
type OtherMetadata = { [key: string]: object };

// GOOD: a real value contract
type Metadata = Record<string, string | number | boolean>;
```

### `no-widen-then-assert`

```ts
// BAD: widen, then assert back — the round trip proves nothing
const loaded: User = loadUser();
const stored: unknown = loaded;
const user = stored as User;

// GOOD: keep the known type; no widening, no assertion
const loaded: User = loadUser();
```

### `require-safety-comment-for-type-assertion`

```ts
// BAD: bare non-const assertion with no justification
const userId = value as UserId;

// GOOD: the checked invariant is documented immediately before
// SAFETY: parseUserId validated the identifier before branding it.
const userId = value as UserId;
```

## 4. Wiring Guide (oxlint)

Upstream anti-slop is meant to be **vendored, not pinned as an npm
dependency**: copy `src/` into your repository (e.g.
`tools/oxlint/anti-slop/`), read the rules, and adjust them to your team's
standards. Install current versions of `oxlint` and `@oxlint/plugins`.

Register the copied entry point in `oxlint.config.ts`:

```ts
import { defineConfig } from "oxlint";

export default defineConfig({
  ignorePatterns: [
    // agent/assistant asset dirs — never lint generated or vendored agent files
    ".agent/**", ".agents/**", ".claude/**", ".codex/**",
    ".continue/**", ".cursor/**", ".gemini/**", ".opencode/**",
    ".pi/**", ".roo/**", ".windsurf/**",
    "tools/oxlint/anti-slop/**",
  ],
  jsPlugins: [
    { name: "anti-slop", specifier: "./tools/oxlint/anti-slop/index.ts" },
  ],
  rules: {
    "anti-slop/no-chained-type-assertions": "error",
    "anti-slop/no-conditional-empty-object-spread": "error",
    "anti-slop/no-known-value-widening": "error",
    "anti-slop/no-module-mocking": "error",
    "anti-slop/no-object-parameters": "error",
    "anti-slop/no-reflect-apply": "error",
    "anti-slop/no-reflect-get": "error",
    "anti-slop/no-runtime-typeof": "error",
    "anti-slop/no-shape-in-symbol-names": "error",
    "anti-slop/no-unknown-parameters": "error",
    "anti-slop/no-unknown-returns": "error",
    "anti-slop/no-unknown-type-aliases": "error",
    "anti-slop/no-unsafe-dictionary-type": "error",
    "anti-slop/no-widen-then-assert": "error",
    "anti-slop/require-safety-comment-for-type-assertion": "error",
  },
});
```

The same `ignorePatterns`, `jsPlugins`, and rules work under `lint` in a
Vite+ config; merge the ignore patterns into Vite+'s `fmt.ignorePatterns`
too so `vp check` does not reformat the vendored plugin. Preserve existing
ignores; add other project-local agent tooling dirs you actually find —
do not blanket-ignore every dot-directory.

Agent-skill install path (when the project prefers it):

```bash
npx skills add dmmulroy/anti-slop --skill install-anti-slop
```

Then ask the coding agent to install/configure anti-slop in the current
repository; the bundled skill copies the plugin, installs current Oxlint
dependencies, merges the config, and enables every generic rule.

### Optional Effect rules

Only in repositories that use Effect — register the second plugin and
enable `anti-slop-effect/no-service-constructor-imports`. Projects without
Effect must not inherit Effect architecture policy.

### CI gate

Add oxlint to CI so violations block merge, e.g. in GitHub Actions:

```yaml
- name: Lint (oxlint, anti-slop rules)
  run: npx oxlint --config oxlint.config.ts
```

Treat any new violation as a review failure; fix the code or record a
deliberate exception (section 5). Never widen the ruleset silently to make
CI green.

## 5. Judgment: When a "Slop" Pattern Is Justified

The rules are opinionated, not moral law. A pattern is justified when it is
the *cheapest honest encoding* of a real constraint, not a shortcut around
typing. Common justified cases and how to mark them:

1. **True boundaries.** Data arriving from outside the type system (raw
   JSON, network responses, env vars, `postMessage`) is genuinely
   `unknown` until parsed. The fix is a parse at the boundary — not
   sprinkling `as` casts. If a rule fires on boundary-parsing code
   (e.g. a schema validator's internals, a type-guard function), that is
   the escape hatch: use the rule's options (like `allowInTypeGuards`)
   or scope an inline suppression to that file.
2. **Third-party seams you don't own.** Interfacing with untyped or
   loosely typed libraries may require one assertion at the adapter edge.
   Allowed only with a safety comment (which
   `require-safety-comment-for-type-assertion` demands anyway).
3. **Test doubles where module mocking is the only seam.** Prefer
   dependency injection; if a legacy module leaves no seam and refactoring
   is out of scope for the change, a scoped `vi.mock` with a comment is
   acceptable as a deliberate exception.
4. **Error causes.** `cause: unknown` is an explicit upstream convention
   and exempt under `no-unknown-parameters`.

Marking deliberate exceptions — in order of preference:

- **Rule options** when the rule provides one (e.g. `allowInTypeGuards`),
  set in `oxlint.config.ts` with a one-line why-comment.
- **Inline suppression** (`// oxlint-disable-next-line anti-slop/...`)
  with a `// WHY:` line naming the invariant or constraint.
- **Config-level ignore** for a whole directory only for generated or
  vendored code — never for hand-written application code.

An exception without a written reason is slop too. If you cannot state the
invariant that makes the pattern safe, it is not an exception — it is a bug.

## 6. Review Checklist

When reviewing TS/JS code, verify:

1. No chained assertions, no widen-then-assert round trips.
2. `unknown`/`object`/`any` do not leak across signatures; dictionaries
   have real value types.
3. Every non-const `as` carries a safety comment stating the checked
   invariant.
4. Runtime data is parsed at the boundary once, not `typeof`-narrowed
   ad hoc throughout.
5. Tests use injected seams, not module mocks, unless a documented
   exception applies.
6. oxlint runs in CI with the anti-slop rules enabled and any
   suppressions carry reasons.

## 7. Attribution

- Upstream: [dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop) —
  "Opinionated Oxlint rules that reject low-evidence and low-signal
  TypeScript and JavaScript patterns."
- License: MIT. Rule names, descriptions, and examples above are derived
  from the upstream README.
