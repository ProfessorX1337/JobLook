// Top-level content-script logic. Picks an adapter by URL, listens for
// popup/service-worker commands, and drives fill operations.

import { greenhouse } from "./adapters/greenhouse.js";
import { lever } from "./adapters/lever.js";
import { ashby } from "./adapters/ashby.js";
import { mapField } from "./shared/field-mapper.js";
import { getPath } from "./shared/profile-schema.js";
import {
  setCheckbox,
  setInputValue,
  setRadioGroup,
  setSelectValue,
} from "./shared/dom-events.js";
import { getProfile, postAutofill } from "./shared/api-client.js";

const ADAPTERS = [greenhouse, lever, ashby];

function pickAdapter(url) {
  return ADAPTERS.find((a) => a.matches(url)) || null;
}

async function fillStandardFields() {
  const adapter = pickAdapter(location.href);
  if (!adapter) return { ok: false, error: "No adapter for this page" };

  const formRoot = adapter.detectForm();
  if (!formRoot) return { ok: false, error: "No application form detected" };

  const profile = await getProfile().catch(() => null);
  if (!profile) return { ok: false, error: "Not signed in — connect the extension from joblook.ai/app" };

  const fields = adapter.listFields(formRoot);
  const results = { filled: [], skipped: [], unknown: [] };

  for (const field of fields) {
    const mapping = mapField(field);
    if (!mapping) {
      results.unknown.push(_fieldMeta(field));
      continue;
    }
    const value = getPath(profile, mapping.path);
    if (value === undefined || value === null || value === "") {
      results.skipped.push({ field: _fieldMeta(field), path: mapping.path, reason: "empty" });
      continue;
    }
    try {
      applyValue(field, value);
      results.filled.push({ field: _fieldMeta(field), path: mapping.path });
    } catch (e) {
      results.skipped.push({ field: _fieldMeta(field), path: mapping.path, reason: String(e) });
    }
  }

  return { ok: true, adapter: adapter.name, ...results };
}

/**
 * Fill custom long-form questions via the /api/extension/autofill endpoint.
 * Groups fields by question text, sends to backend, applies answers.
 */
async function fillCustomAnswers() {
  const adapter = pickAdapter(location.href);
  if (!adapter) return { ok: false, error: "No adapter for this page" };

  const formRoot = adapter.detectForm();
  if (!formRoot) return { ok: false, error: "No application form detected" };

  const profile = await getProfile().catch(() => null);
  if (!profile) return { ok: false, error: "Not signed in" };

  // Only import crypto temporarily for hashing
  const { subtle } = window.crypto;
  const encoder = new TextEncoder();

  async function sha256(text) {
    const buf = await subtle.digest("SHA-256", encoder.encode(text));
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
      .slice(0, 64);
  }

  const jobCtx = adapter.extractJobContext(formRoot);
  const jobCtxHash = await sha256(jobCtx.description || "");

  // Collect all custom (non-standard) fields — ones that map to custom_answers
  const customFields = adapter.listFields(formRoot).filter((f) => {
    const mapping = mapField(f);
    // A field is "custom" if it has no direct profile mapping or maps to custom_answers
    if (!mapping) return true;
    return mapping.path.startsWith("custom_answers");
  });

  if (customFields.length === 0) {
    return { ok: true, adapter: adapter.name, filled: 0, skipped: 0, answers: [] };
  }

  const questions = customFields.map((f) => ({
    question: f.label || f.placeholder || f.name || "unknown question",
  }));

  const payload = {
    questions,
    job_context_hash: jobCtxHash,
  };

  let responses;
  try {
    responses = await postAutofill(payload);
  } catch (e) {
    return { ok: false, error: "Autofill API error: " + String(e) };
  }

  const { results: answers } = responses;
  const results = { filled: [], skipped: [], unknown: [] };

  for (let i = 0; i < customFields.length; i++) {
    const field = customFields[i];
    const answer = answers?.[i];

    if (!answer || !answer.answer) {
      results.skipped.push({ field: _fieldMeta(field), reason: "no answer returned" });
      continue;
    }

    // Mark source for transparency
    const sourceLabel = answer.source || "unknown";

    try {
      applyValue(field, answer.answer);
      results.filled.push({ field: _fieldMeta(field), source: sourceLabel });
    } catch (e) {
      results.skipped.push({ field: _fieldMeta(field), reason: String(e) });
    }
  }

  return { ok: true, adapter: adapter.name, ...results };
}

function _fieldMeta(field) {
  return {
    label: field.label || "",
    name: field.name || "",
    id: field.id || "",
    type: field.type || "text",
  };
}

function applyValue(field, value) {
  const el = field.el;
  if (!el) throw new Error("Missing element");
  switch (field.type) {
    case "select":
      if (!setSelectValue(el, value)) throw new Error("No matching option");
      return;
    case "checkbox":
      setCheckbox(el, Boolean(value));
      return;
    case "radio":
      if (!setRadioGroup(field.group || [], value)) throw new Error("No matching radio");
      return;
    default:
      setInputValue(el, value);
  }
}

export async function run() {
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type === "content:fillStandard") {
      fillStandardFields()
        .then((r) => sendResponse(r))
        .catch((e) => sendResponse({ ok: false, error: String(e) }));
      return true;
    }
    if (msg?.type === "content:fillCustom") {
      fillCustomAnswers()
        .then((r) => sendResponse(r))
        .catch((e) => sendResponse({ ok: false, error: String(e) }));
      return true;
    }
    if (msg?.type === "content:detect") {
      const adapter = pickAdapter(location.href);
      const formRoot = adapter?.detectForm?.();
      const fieldCount = formRoot ? adapter.listFields(formRoot).length : 0;
      sendResponse({
        ok: true,
        adapter: adapter?.name || null,
        hasForm: !!formRoot,
        fieldCount,
      });
      return true;
    }
  });
}
