// Greenhouse adapter. Covers two common hosts:
//   - boards.greenhouse.io/:company/jobs/:id  (embedded board)
//   - :company.greenhouse.io                  (self-hosted embed)
// Greenhouse markup is relatively clean: form#application_form contains
// labeled inputs. Custom questions live under `.application-question`.

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

export const greenhouse = {
  name: "greenhouse",

  matches(url) {
    return /(^|\.)greenhouse\.io/i.test(new URL(url).hostname);
  },

  detectForm() {
    return (
      document.querySelector("form#application_form") ||
      document.querySelector("form[action*='/applications']") ||
      null
    );
  },

  extractJobContext(formRoot) {
    const title =
      document.querySelector("h1.app-title")?.textContent?.trim() ||
      document.querySelector("h1")?.textContent?.trim() ||
      document.title;
    const company =
      document.querySelector(".company-name")?.textContent?.trim() ||
      new URL(location.href).hostname.split(".")[0];
    const location_ =
      document.querySelector(".location")?.textContent?.trim() || "";
    const descriptionEl =
      document.querySelector("#content") ||
      document.querySelector(".content") ||
      document.querySelector("#job_description") ||
      formRoot?.previousElementSibling;
    const description = (descriptionEl?.innerText || "").trim().slice(0, 12000);
    return { url: location.href, title, company, location: location_, description };
  },

  listFields(formRoot) {
    const inputs = formRoot.querySelectorAll("input, select, textarea");
    const fields = [];
    const radiosByName = new Map();

    for (const el of inputs) {
      if (el.type === "hidden" || el.type === "submit" || el.type === "button") continue;
      if (el.type === "file") continue; // resume upload handled separately
      if (el.type === "radio") {
        const group = radiosByName.get(el.name) || [];
        group.push(el);
        radiosByName.set(el.name, group);
        continue;
      }
      fields.push(fieldDescriptor(el));
    }

    for (const [name, group] of radiosByName) {
      const first = group[0];
      fields.push({ ...fieldDescriptor(first), name, type: "radio", group });
    }

    return fields;
  },
};
