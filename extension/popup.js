document.addEventListener("DOMContentLoaded", () => {
  const qs = (id) => document.getElementById(id);

  /* ---------- master‑key handling ---------- */
  chrome.storage.local.get("masterKey", ({ masterKey }) => {
    if (masterKey) qs("masterKey").value = masterKey;
  });

  qs("setKey").onclick = () => {
    const key = qs("masterKey").value.trim();
    if (key.length !== 64 || !/^[0-9a-fA-F]+$/.test(key)) {
      return alert("Key must be 64 hexadecimal characters.");
    }
    chrome.storage.local.set({ masterKey: key }, () => alert("Key saved."));
  };

  /* ---------- save credentials ---------- */
  qs("save").onclick = () => {
    chrome.runtime.sendMessage(
      {
        action: "savePassword",
        site: qs("site").value.trim(),
        username: qs("username").value,
        password: qs("password").value
      },
      (r) => {
        if (r?.status === "success") alert("Password saved!");
        else alert(`Error: ${r?.message || "unknown"}`);
      }
    );
  };

  /* ---------- show credentials ---------- */
  qs("showPassword").onclick = () => {
    let site = qs("site").value.trim();

    const fillFields = (entry) => {
      qs("username").value = entry.username;
      qs("password").value = entry.password;
    };

    const fetchSite = (hostname) =>
      chrome.runtime.sendMessage(
        { action: "getPassword", site: hostname },
        (resp) => {
          resp?.entry
            ? fillFields(resp.entry)
            : alert(`No password saved for ${hostname}`);
        }
      );

    if (site) {
      fetchSite(site);
    } else {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const url = tabs[0]?.url;
        if (!url) return;
        try {
          site = new URL(url).hostname;
          qs("site").value = site;
          fetchSite(site);
        } catch {
          alert("Unable to extract hostname.");
        }
      });
    }
  };

  /* ---------- import from USB ---------- */
  qs("loadFromUSB").onclick = () => qs("filePicker").click();

  qs("filePicker").onchange = (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const entries = [];
      let current = {};
      e.target.result
        .split("\n")
        .map((l) => l.trim())
        .forEach((line) => {
          if (line.startsWith("Website:")) {
            current.site = line.slice(8).trim();
          } else if (line.startsWith("Username:")) {
            current.username = line.slice(9).trim();
          } else if (line.startsWith("Password:")) {
            current.password = line.slice(9).trim();
            if (current.site && current.username && current.password) {
              entries.push(current);
              current = {};
            }
          }
        });
      if (!entries.length) return alert("No entries found in file.");
      chrome.runtime.sendMessage(
        { action: "importFromUSB", data: entries },
        (resp) =>
          alert(
            resp?.status === "imported"
              ? `Imported ${resp.count} passwords.`
              : `Error: ${resp?.message || "unknown"}`
          )
      );
    };
    reader.readAsText(file);
  };

  /* ---------- export to USB ---------- */
  qs("saveToUSB").onclick = () =>
    chrome.runtime.sendMessage({ action: "exportToUSB" });
});
