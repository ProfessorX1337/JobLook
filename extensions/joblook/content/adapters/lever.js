// Lever adapter. Covers:
//   - .lever.co (self-hosted board)
//   - jobs.lever.co (hosted board)
// Lever uses a mix of structured fields and custom questions.
// Custom questions are inside `.application-question` blocks with
// a label + textarea/select/input.

import { labelTextFor } from "../shared/dom-events.js";

function fieldDescriptor(el) {
  const base = {
    el,
    id: el.id || "",
    name: el.name || "",
    label: labelTextFor(el),
    placeholder: el.placeholder || "",
    ariaLabel: el.getAttribute("aria-label") || "",
    required: el.required || el.getAttribute("aria-required") === "true",
  };
  if (el.tagName === "SELECT") return { ...base, type: "select" };
  if (el.tagName === "TEXTAREA") return { ...base, type: "textarea" };
  if (el.type === "checkbox") return { ...base, type: "checkbox" };
  if (el.type === "radio") return { ...base, type: "radio" };
  return { ...base, type: el.type || "text" };
}

export const lever = {
  name: "lever",

  matches(url) {
    return /lever\.(co|io|us)/i.test(new URL(url).hostname);
  },

  detectForm() {
    return (
      document.querySelector("form[class*='application']") ||
      document.querySelector("form[data-qa='apply-form']") ||
      document.querySelector("form[action*='apply']") ||
      document.querySelector("form") ||
      null
    );
  },

  extractJobContext(formRoot) {
    // Job title: inside the main heading or meta tag
    const title =
      document.querySelector("h1[data-qa='job-title']")?.textContent?.trim() ||
      document.querySelector("h1")?.textContent?.trim() ||
      document.title;

    // Company name: in the nav brand or a meta tag
    const company =
      document.querySelector("[data-qa='company-name']")?.textContent?.trim() ||
      document.querySelector("a[class*='company']")?.textContent?.trim() ||
      new URL(location.href).hostname.split(".")[1] || "";

    // Location
    const location =
      document.querySelector("[data-qa='job-location']")?.textContent?.trim() ||
      document.querySelector(".lever-location")?.textContent?.trim() || "";

    // Job description: the main posting content
    const descriptionEl =
      document.querySelector("[data-qa='job-description']") ||
      document.querySelector(".job-description") ||
      document.querySelector("#job-description") ||
      document.querySelector(".lever-form-description") ||
      formRoot?.previousElementSibling;
    const description = (descriptionEl?.innerText || "").trim().slice(0, 12000);

    return { url: location.href, title, company, location, description };
  },

  listFields(formRoot) {
    const fields = [];
    const radiosByName = new Map();

    // Lever wraps most fields in a .lever-form-field div with a label
    // Custom questions use .application-question class
    const wrappers = formRoot.querySelectorAll(
      ".lever-form-field, .application-question, .field-wrapper"
    );

    if (wrappers.length > 0) {
      for (const wrapper of wrappers) {
        const labelEl =
          wrapper.querySelector("label") ||
          wrapper.querySelector("[data-qa*='label']") ||
          wrapper.querySelector("h3") ||
          wrapper;
        const label = labelEl?.textContent?.trim() || "";

        const el =
          wrapper.querySelector("input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea");

        if (!el || el.type === "file") continue;

        if (el.type === "radio") {
          const group = radiosByName.get(el.name) || [];
          group.push(el);
          radiosByName.set(el.name, group);
          continue;
        }

        fields.push({
          ...fieldDescriptor(el),
          label: label || labelTextFor(el),
        });
      }
    }

    // Fallback: grab all form inputs directly
    if (fields.length === 0) {
      const inputs = formRoot.querySelectorAll(
        "input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea"
      );
      for (const el of inputs) {
        if (el.type === "file" || el.type === "checkbox") continue;
        if (el.type === "radio") {
          const group = radiosByName.get(el.name) || [];
          group.push(el);
          radiosByName.set(el.name, group);
          continue;
        }
        fields.push(fieldDescriptor(el));
      }
    }

    // Handle radio groups
    for (const [name, group] of radiosByName) {
      const first = group[0];
      fields.push({
        ...fieldDescriptor(first),
        name,
        type: "radio",
        group,
      });
    }

    return fields;
  },
};
