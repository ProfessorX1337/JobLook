// Holds the JWT, talks to the backend, and receives the connect-extension
// token from the dashboard via externally_connectable messages.

const DEFAULT_API = "http://localhost:8000";

chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === "install") {
    chrome.tabs.create({ url: chrome.runtime.getURL("welcome/welcome.html") });
  }
});

async function getApiBase() {
  const { api_base } = await chrome.storage.local.get("api_base");
  return api_base || DEFAULT_API;
}

async function getJwt() {
  const { jwt } = await chrome.storage.local.get("jwt");
  return jwt || null;
}

async function apiRequest(path, { method = "GET", body } = {}) {
  const base = await getApiBase();
  const jwt = await getJwt();
  if (!jwt) return { ok: false, error: "not_signed_in" };

  const res = await fetch(`${base}${path}`, {
    method,
    headers: {
      "Authorization": `Bearer ${jwt}`,
      "Content-Type": body ? "application/json" : undefined,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    await chrome.storage.local.remove("jwt");
    return { ok: false, error: "unauthorized" };
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    return { ok: false, error: text || `http_${res.status}` };
  }
  const data = await res.json().catch(() => null);
  return { ok: true, data };
}

// Content-script and popup messaging.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "api") {
    apiRequest(msg.path, { method: msg.method, body: msg.body }).then(sendResponse);
    return true;
  }
  if (msg?.type === "auth:status") {
    getJwt().then((jwt) => sendResponse({ signedIn: !!jwt }));
    return true;
  }
  if (msg?.type === "auth:signOut") {
    chrome.storage.local.remove("jwt").then(() => sendResponse({ ok: true }));
    return true;
  }
});

// Receive JWT from the dashboard's connect-extension page.
chrome.runtime.onMessageExternal.addListener((msg, sender, sendResponse) => {
  const origin = sender.origin || sender.url || "";
  const allowed =
    origin.startsWith("https://joblook.ai") || origin.startsWith("http://localhost:");
  if (!allowed) return sendResponse({ ok: false, error: "origin_not_allowed" });

  if (msg?.type === "joblook:connect" && typeof msg.token === "string") {
    const apiBase = origin.startsWith("http://localhost:") ? origin : "https://api.joblook.ai";
    chrome.storage.local.set({ jwt: msg.token, api_base: apiBase }).then(() =>
      sendResponse({ ok: true })
    );
    return true;
  }
  sendResponse({ ok: false, error: "unknown_message" });
});
