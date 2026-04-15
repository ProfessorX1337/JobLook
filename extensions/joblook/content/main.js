// Top-level content-script logic. Picks an adapter by URL, listens for
// popup/service-worker commands, and drives fill operations.

import { greenhouse } from "./adapters/greenhouse.js";
import { mapField } from "./shared/field-mapper.js";
import { getPath } from "./shared/profile-schema.js";
import {
  setCheckbox,
  setInputValue,
  setRadioGroup,
  setSelectValue,
} from "./shared/dom-events.js";
import { getProfile } from "./shared/api-client.js";

const ADAPTERS = [greenhouse];

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
      results.unknown.push(field);
      continue;
    }
    const value = getPath(profile, mapping.path);
    if (value === undefined || value === null || value === "") {
      results.skipped.push({ field, path: mapping.path, reason: "empty" });
      continue;
    }
    try {
      applyValue(field, value);
      results.filled.push({ field, path: mapping.path });
    } catch (e) {
      results.skipped.push({ field, path: mapping.path, reason: String(e) });
    }
  }

  return { ok: true, adapter: adapter.name, ...results };
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
      return true; // async response
    }
    if (msg?.type === "content:detect") {
      const adapter = pickAdapter(location.href);
      const formRoot = adapter?.detectForm?.();
      sendResponse({ ok: true, adapter: adapter?.name || null, hasForm: !!formRoot });
      return true;
    }
  });
}
