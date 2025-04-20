// popup.js – UI logic for UPass popup (refactored layout)

/**
 * Create a cryptographically–secure random password.
 * @param {number} len Desired length (default 16)
 * @returns {string}
 */
function generateSecurePassword(len = 16) {
  const charset =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()-_=+[]{}<>?";
  const bytes = new Uint32Array(len);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (v) => charset[v % charset.length]).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  const qs = (id) => document.getElementById(id);

  /* ---------------- toggle master‑key visibility ---------------- */
  const masterKeyInput = qs("masterKey");
  const toggleMasterKeyButton = qs("toggleMasterKey");

  toggleMasterKeyButton?.addEventListener("click", () => {
    const isHidden = masterKeyInput.type === "password";
    masterKeyInput.type = isHidden ? "text" : "password";
    toggleMasterKeyButton.textContent = isHidden ? "Hide" : "Show";
  });

  /* ---------------- toggle password visibility ---------------- */
  const passwordInput = qs("password");
  const togglePasswordButton = qs("togglePassword");

  togglePasswordButton?.addEventListener("click", () => {
    const isHidden = passwordInput.type === "password";
    passwordInput.type = isHidden ? "text" : "password";
    togglePasswordButton.textContent = isHidden ? "Hide" : "Show";
  });

  /* ---------------- secure‑password generator ---------------- */
  const genBtn = qs("generate");
  if (genBtn) {
    genBtn.addEventListener("click", async () => {
      const pw = generateSecurePassword();
      passwordInput.value = pw;         // fill main password field
      try {
        await navigator.clipboard.writeText(pw);
        genBtn.textContent = "Copied!";
        setTimeout(() => (genBtn.textContent = "Generate"), 1500);
      } catch {
        alert("Generated and filled password (copy failed – clipboard permissions?)");
      }
    });
  }

  /* ---------------- load saved master key ---------------- */
  chrome.storage.local.get("masterKey", ({ masterKey }) => {
    if (masterKey) masterKeyInput.value = masterKey;
  });

  /* ---------------- set master key ---------------- */
  qs("setKey").onclick = () => {
    const key = masterKeyInput.value.trim();
    if (key.length < 6) return alert("Key must be at least 6 characters.");

    chrome.storage.local.set({ masterKey: key }, () => alert("Key saved."));

    chrome.runtime.sendMessage({ action: "checkAndInitUSB" }, (resp) => {
      if (!resp) return;
      const msg = resp.message || "";
      switch (resp.status) {
        case "usbMissing":
        case "missingKey":
        case "created":
        case "encrypted":
        case "error":
          alert(msg);
          if (["usbMissing", "error"].includes(resp.status)) window.close();
          break;
      }
    });
  };

  /* ---------------- save credentials ---------------- */
  qs("save").onclick = () => {
    const payload = {
      action: "savePassword",
      site: qs("site").value.trim(),
      username: qs("username").value,
      password: passwordInput.value
    };
    if (!payload.site || !payload.username || !payload.password) {
      return alert("Site, username, and password are required.");
    }

    chrome.runtime.sendMessage(payload, (resp) => {
      if (!resp) return alert("No response from background.");

      switch (resp.status) {
        case "success":
          alert("Password saved!");
          break;
        case "overwritten":
          alert("Existing password overwritten.");
          break;
        case "exists": {
          const ok = confirm(
            `Credentials already stored for “${payload.site}”.\nOverwrite existing entry?`
          );
          if (ok) chrome.runtime.sendMessage({ ...payload, force: true });
          break;
        }
        default:
          alert(`Error: ${resp.message || "unknown"}`);
      }
    });
  };

  /* ---------------- show credentials ---------------- */
  qs("showPassword").onclick = () => {
    let site = qs("site").value.trim();

    const fill = (entry) => {
      qs("username").value = entry.username;
      passwordInput.value = entry.password;
    };

    const fetchCred = (host) =>
      chrome.runtime.sendMessage({ action: "getPassword", site: host }, (r) => {
        r?.entry ? fill(r.entry) : alert(`No password saved for ${host}`);
      });

    if (site) {
      fetchCred(site);
    } else {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        try {
          site = new URL(tabs[0].url).hostname;
          qs("site").value = site;
          fetchCred(site);
        } catch {
          alert("Unable to detect current site.");
        }
      });
    }
  };

  /* ---------------- clear master key ---------------- */
  qs("clearMasterKey")?.addEventListener("click", async () => {
    try {
      await chrome.storage.local.remove("masterKey");
      alert("Master key cleared.");
    } catch (err) {
      console.error(err);
      alert("Error clearing master key – see console for details.");
    }
  });
});
