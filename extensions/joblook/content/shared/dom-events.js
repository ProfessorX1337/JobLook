// React/Vue-aware setters. Naive `el.value = x` is ignored by frameworks that
// track values via their own internal setters. We bypass via the native
// property descriptor and then dispatch bubbling input/change/blur events.

function nativeValueSetter(el) {
  const proto = Object.getPrototypeOf(el);
  const desc = Object.getOwnPropertyDescriptor(proto, "value");
  return desc && desc.set ? desc.set.bind(el) : (v) => { el.value = v; };
}

export function setInputValue(el, value) {
  const str = value == null ? "" : String(value);
  nativeValueSetter(el)(str);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  el.dispatchEvent(new Event("blur", { bubbles: true }));
}

export function setSelectValue(el, value) {
  const str = value == null ? "" : String(value);
  const match = Array.from(el.options).find((o) =>
    o.value === str || o.text.trim().toLowerCase() === str.trim().toLowerCase()
  );
  if (!match) return false;
  nativeValueSetter(el)(match.value);
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}

export function setCheckbox(el, desired) {
  if (el.checked === Boolean(desired)) return;
  el.click();
}

export function setRadioGroup(group, value) {
  const str = String(value).toLowerCase();
  for (const radio of group) {
    const label = labelTextFor(radio).toLowerCase();
    if (radio.value.toLowerCase() === str || label === str) {
      if (!radio.checked) radio.click();
      return true;
    }
  }
  return false;
}

export function labelTextFor(el) {
  if (el.labels && el.labels.length) return el.labels[0].textContent.trim();
  if (el.getAttribute("aria-label")) return el.getAttribute("aria-label").trim();
  const byId = el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
  if (byId) return byId.textContent.trim();
  const wrap = el.closest("label");
  if (wrap) return wrap.textContent.trim();
  return "";
}
