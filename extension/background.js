// background.js – service‑worker (Manifest v3)
// Talks to FastAPI backend at http://127.0.0.1:5000
//
// 🔒 Security update (2025‑04‑21):
//   • After five consecutive failed decryption attempts the service‑worker
//     now FREEZES the whole extension for 60 s instead of blocking only
//     the getPassword route.

const API_BASE = "http://127.0.0.1:5000";

/* ---------- helper ---------- */
async function getMasterKey() {
  const { masterKey } = await chrome.storage.local.get("masterKey");
  return masterKey || "";
}

/* ---------- lockout / freeze state ---------- */
let failCounts  = 0;              // consecutive failed decryptions
const MAX_FAILS = 5;              // threshold before freeze engages
const FREEZE_MS = 60_000;         // 60‑second freeze duration
let freezeUntil = 0;              // Epoch ms until which *all* messages are refused

/* ---------- message router ---------- */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  const now = Date.now();

  // Global freeze check — refuses *every* action while active
  if (now < freezeUntil) {
    const wait = Math.ceil((freezeUntil - now) / 1000);
    sendResponse({
      status: "frozen",
      message: `Too many failed attempts. Extension locked for ${wait} s.`
    });
    return true; // Keep message channel alive for async callers
  }

  switch (request.action) {
    /* -------- save / overwrite credentials -------- */
    case "savePassword":
      (async () => {
        try {
          const key = await getMasterKey();
          if (!key) throw new Error("Master key not set.");

          const body = {
            site: request.site,
            username: request.username,
            password: request.password,
            masterKey: key,
            ...(request.force ? { force: true } : {})
          };

          const res  = await fetch(`${API_BASE}/savePassword`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
          });
          const data = await res.json(); // {status: ...}
          sendResponse(data);
        } catch (e) {
          sendResponse({ status: "error", message: e.message });
        }
      })();
      return true;

    /* -------- retrieve credentials -------- */
    case "getPassword":
      (async () => {
        try {
          const key = await getMasterKey();
          if (!key) throw new Error("Master key not set.");

          const r = await fetch(
            `${API_BASE}/getPassword/${encodeURIComponent(request.site)}?key=${key}`
          );

          if (r.status === 500) {
            // Decryption failed => increment counter
            failCounts += 1;

            if (failCounts >= MAX_FAILS) {
              // Engage global freeze
              freezeUntil = Date.now() + FREEZE_MS;
              setTimeout(() => {
                failCounts  = 0;
                freezeUntil = 0;
              }, FREEZE_MS);
            }

            throw new Error("Incorrect passphrase. Decryption failed.");
          }

          // Successful response — reset counters
          failCounts  = 0;
          freezeUntil = 0;

          const data = await r.json(); // { entry: {...} | null }
          sendResponse(data);
        } catch (e) {
          sendResponse({ entry: null, message: e.message });
        }
      })();
      return true;

    /* -------- import list from text file -------- */
    case "importFromUSB":
      (async () => {
        try {
          const key = await getMasterKey();
          if (!key) throw new Error("Master key not set.");
          const r = await fetch(`${API_BASE}/importFromUSB`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              items: request.data,
              masterKey: key
            })
          });
          const data = await r.json(); // { status, count }
          sendResponse(data);
        } catch (e) {
          sendResponse({ status: "error", message: e.message });
        }
      })();
      return true;

    /* -------- export & trigger download -------- */
    case "exportToUSB":
      (async () => {
        try {
          const key = await getMasterKey();
          if (!key) throw new Error("Master key not set.");
          const r = await fetch(`${API_BASE}/exportToUSB?key=${key}`);
          const txt = await r.text();
          const url =
            "data:text/plain;charset=utf-8," + encodeURIComponent(txt);
          chrome.downloads.download(
            {
              url,
              filename: "my_passwords.txt",
              saveAs: true,
              conflictAction: "uniquify"
            },
            () => {
              if (chrome.runtime.lastError) {
                sendResponse({
                  status: "error",
                  message: chrome.runtime.lastError.message
                });
              } else {
                sendResponse({ status: "success" });
              }
            }
          );
        } catch (e) {
          sendResponse({ status: "error", message: e.message });
        }
      })();
      return true;

    /* -------- checkAndInitUSB -------- */
    case "checkAndInitUSB":
      (async () => {
        try {
          // Step 1: Get usb status (whether it's plugged in)
          const statusRes = await fetch(`${API_BASE}/usbStatus`);
          if (!statusRes.ok) {
            throw new Error("Unable to connect to backend.");
          }
          const status = await statusRes.json();

          // Step 2: If no USB detected
          if (!status.usbFound) {
            sendResponse({
              status: "usbMissing",
              message: "USB device not found."
            });
            return;
          }

          // Step 3: Fetch password
          const { masterKey } = await chrome.storage.local.get("masterKey"); // actually password
          if (!masterKey || masterKey.length < 6) {
            sendResponse({
              status: "missingKey",
              message:
                "Please set a password first. Then refresh to finish initialization."
            });
            return;
          }

          // Step 4: Setup USB (create db + encrypt)
          if (!status.encrypted && status.dbExists) {
            const encryptRes = await fetch(`${API_BASE}/encryptUSB`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ masterKey })
            });

            const r = await encryptRes.json();
            if (!encryptRes.ok || r.status !== "success") {
              throw new Error(r.message || "Failed to encrypt existing DB.");
            }

            sendResponse({
              status: "encrypted",
              message: "Existing database encrypted."
            });
            return;
          }

          // Don't change the order of checking the above block and the block below
          if (!status.dbExists) {
            const setupRes = await fetch(`${API_BASE}/setupUSB`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ masterKey })
            });

            const r = await setupRes.json();
            if (!setupRes.ok || r.status !== "success") {
              throw new Error(r.message || "Failed to create and encrypt DB.");
            }

            sendResponse({
              status: "created",
              message: "Database created and encrypted."
            });
            return;
          }

          sendResponse({ status: "ok", message: "USB and DB are ready." });
        } catch (e) {
          console.error("USB setup err:", e);
          sendResponse({ status: "error", message: e.message });
        }
      })();
      return true;
  }
});
