// Ashby adapter. Covers:
//   - jobs.ashbyhq.com (hosted board)
//   - :company.ashbyhq.com (self-hosted)
// Ashby uses GraphQL-loaded forms, so the DOM structure depends on
// whether the form has been hydrated. Key selectors:
//   - ashbyhq.com always uses a <form> with an id like "application-form"
//   - Custom questions live inside elements with data-testid attributes

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

export const ashby = {
  name: "ashby",

  matches(url) {
    return /ashbyhq\.com/i.test(new URL(url).hostname);
  },

  detectForm() {
    return (
      document.querySelector("form[id*='application']") ||
      document.querySelector("form[data-testid='application-form']") ||
      document.querySelector("form[action*='apply']") ||
      document.querySelector("form") ||
      null
    );
  },

  extractJobContext(formRoot) {
    // Job title: heading with data-testid or h1
    const title =
      document.querySelector("[data-testid='job-title']")?.textContent?.trim() ||
      document.querySelector("h1[data-testid='title']")?.textContent?.trim() ||
      document.querySelector("h1")?.textContent?.trim() ||
      document.title;

    // Company: logo alt text, or meta
    const company =
      document.querySelector("[data-testid='company-name']")?.textContent?.trim() ||
      document.querySelector("img[alt*='logo']")?.alt?.replace(/logo/i, "").trim() ||
      new URL(location.href).hostname.split(".")[1] || "";

    // Location
    const location =
      document.querySelector("[data-testid='location']")?.textContent?.trim() ||
      document.querySelector(".ashby-location")?.textContent?.trim() || "";

    // Job description: the posting content area
    const descriptionEl =
      document.querySelector("[data-testid='job-description']") ||
      document.querySelector(".job-description") ||
      document.querySelector("#job-description") ||
      formRoot?.previousElementSibling;
    const description = (descriptionEl?.innerText || "").trim().slice(0, 12000);

    return { url: location.href, title, company, location, description };
  },

  listFields(formRoot) {
    const fields = [];
    const radiosByName = new Map();

    // Ashby uses data-testid on wrapper divs for each question
    const questionWrappers = formRoot.querySelectorAll(
      "[data-testid^='question'], [data-testid^='field'], [data-testid*='input']"
    );

    if (questionWrappers.length > 0) {
      for (const wrapper of questionWrappers) {
        const labelEl = wrapper.querySelector("label") || wrapper.querySelector("h3") || wrapper;
        const label = labelEl?.textContent?.trim() || "";

        const el =
          wrapper.querySelector("input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea");

        if (!el) continue;

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

    // Fallback: grab all form inputs
    if (fields.length === 0) {
      const inputs = formRoot.querySelectorAll(
        "input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea"
      );
      for (const el of inputs) {
        if (el.type === "file") continue;
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
