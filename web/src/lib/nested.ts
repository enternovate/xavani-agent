const DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"]);

export function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const p of parts) {
    if (DANGEROUS_KEYS.has(p)) return undefined;
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur;
}

export function setNestedValue(obj: Record<string, unknown>, path: string, value: unknown): Record<string, unknown> {
  const clone = structuredClone(obj);
  const parts = path.split(".");
  let cur: Record<string, unknown> = clone;
  for (let i = 0; i < parts.length - 1; i++) {
    const key = parts[i];
    if (DANGEROUS_KEYS.has(key)) return clone;
    if (cur[key] == null || typeof cur[key] !== "object") {
      cur[key] = {};
    }
    cur = cur[key] as Record<string, unknown>;
  }
  const lastKey = parts[parts.length - 1];
  if (!DANGEROUS_KEYS.has(lastKey)) {
    cur[lastKey] = value;
  }
  return clone;
}
