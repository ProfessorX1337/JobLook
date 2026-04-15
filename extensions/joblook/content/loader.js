// Classic content script entry point. MV3 content scripts can't declare
// `"type": "module"` in the manifest, so we dynamic-import the real logic.

(async () => {
  try {
    const url = chrome.runtime.getURL("content/main.js");
    const mod = await import(url);
    await mod.run();
  } catch (e) {
    console.error("[JobLook] loader failed", e);
  }
})();
