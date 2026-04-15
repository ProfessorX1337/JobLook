const $ = (id) => document.getElementById(id);

async function send(msg) {
  return new Promise((resolve) => chrome.runtime.sendMessage(msg, resolve));
}

async function sendToTab(tabId, msg) {
  return new Promise((resolve) => chrome.tabs.sendMessage(tabId, msg, resolve));
}

async function currentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function renderAuth() {
  const { signedIn } = await send({ type: "auth:status" });
  const { api_base } = await chrome.storage.local.get("api_base");
  const dashboard = (api_base || "http://localhost:8000") + "/app/connect-extension";
  $("auth").innerHTML = signedIn
    ? `<span>Signed in</span><button class="secondary" id="signout">Sign out</button>`
    : `<a href="${dashboard}" target="_blank">Connect extension</a>`;
  if (signedIn) {
    $("signout").addEventListener("click", async () => {
      await send({ type: "auth:signOut" });
      renderAuth();
    });
  }
}

async function renderDetect() {
  const tab = await currentTab();
  const resp = await sendToTab(tab.id, { type: "content:detect" }).catch(() => null);
  if (!resp?.ok) {
    $("detect").textContent = "This page isn't a supported ATS.";
    $("fill-btn").disabled = true;
    return;
  }
  $("detect").textContent = resp.hasForm
    ? `Detected ${resp.adapter} application form.`
    : `${resp.adapter || "Unknown"} — no form found.`;
  $("fill-btn").disabled = !resp.hasForm;
}

$("fill-btn").addEventListener("click", async () => {
  $("result").textContent = "Filling…";
  const tab = await currentTab();
  const resp = await sendToTab(tab.id, { type: "content:fillStandard" });
  if (!resp?.ok) {
    $("result").textContent = "Error: " + (resp?.error || "unknown");
    return;
  }
  $("result").textContent =
    `Filled ${resp.filled.length}, skipped ${resp.skipped.length}, unknown ${resp.unknown.length}.`;
});

renderAuth();
renderDetect();
