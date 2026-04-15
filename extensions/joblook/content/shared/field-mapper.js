// Score candidate form fields against the canonical profile path and return
// the best match. Heuristics only — adapters may override with hard selectors.

import { FIELD_ALIASES } from "./profile-schema.js";

function normalize(s) {
  return (s || "")
    .toLowerCase()
    .replace(/[*_\-–—]/g, " ")
    .replace(/[^a-z0-9 ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function candidateStrings(field) {
  return [field.name, field.id, field.label, field.placeholder, field.ariaLabel]
    .filter(Boolean)
    .map(normalize);
}

function scoreAlias(strings, alias) {
  const a = normalize(alias);
  let best = 0;
  for (const s of strings) {
    if (!s) continue;
    if (s === a) best = Math.max(best, 100);
    else if (s.includes(a)) best = Math.max(best, 70);
    else if (a.includes(s) && s.length >= 3) best = Math.max(best, 40);
  }
  return best;
}

export function mapField(field) {
  const strings = candidateStrings(field);
  let bestPath = null;
  let bestScore = 0;
  for (const [path, aliases] of Object.entries(FIELD_ALIASES)) {
    for (const alias of aliases) {
      const s = scoreAlias(strings, alias);
      if (s > bestScore) {
        bestScore = s;
        bestPath = path;
      }
    }
  }
  return bestScore >= 70 ? { path: bestPath, score: bestScore } : null;
}
