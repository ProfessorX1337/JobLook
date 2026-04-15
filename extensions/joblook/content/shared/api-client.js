// Thin wrapper around chrome.runtime messaging — content scripts never fetch()
// directly; the service worker holds the JWT and makes authenticated calls.

export async function bgFetch(path, { method = "GET", body } = {}) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      { type: "api", path, method, body },
      (resp) => {
        if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
        if (!resp || !resp.ok) return reject(new Error(resp?.error || "Request failed"));
        resolve(resp.data);
      }
    );
  });
}

export async function getProfile() {
  return bgFetch("/api/extension/profile");
}

export async function requestAutofill(payload) {
  return bgFetch("/api/extension/autofill", { method: "POST", body: payload });
}
