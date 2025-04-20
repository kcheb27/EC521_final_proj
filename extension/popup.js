/* popup.js – UI logic for UPass popup */

document.addEventListener("DOMContentLoaded", () => {
  const qs = (id) => document.getElementById(id);

  /* ---------On start, check for usb device--------- */

  chrome.runtime.sendMessage({ action: "checkAndInitUSB" }, (resp) => {
    if (!resp) return;
  
    switch (resp.status) {
      case "usbMissing":
        console.log("usb missing");
        alert(resp.message);
        window.close();
        break;
  
      case "missingKey":
        console.log("masterkey missing");
        alert("Please set a password first. Then re-open extension window to finish initialization.")
        break;
  
      case "created":
        console.log("Database created and encrypted.");
        alert("Database created and encrypted.")
        break;
  
      case "encrypted":
        console.log("Existing database. Encrypted.");
        alert("Existing database. Encrypted.")
        break;
  
      case "error":
        alert(resp.message);
        window.close();
        break;
  
      case "ok":
        console.log("usb db setup already done. check and init usb OK.");
        break;
    }
  });
  
  

  /* ----------- master‑key handling ----------- */
  chrome.storage.local.get("masterKey", ({ masterKey }) => {
    if (masterKey) qs("masterKey").value = masterKey;
  });

  qs("setKey").onclick = () => {
    const key = qs("masterKey").value.trim();
    if (key.length < 6 ) {
      return alert("Key must be longer than 6 characters.");
    }
    chrome.storage.local.set({ masterKey: key }, () => alert("Key saved."));
  };

  /* ----------- save credentials ----------- */
  qs("save").onclick = () => {
    const payload = {
      action: "savePassword",
      site: qs("site").value.trim(),
      username: qs("username").value,
      password: qs("password").value
    };
    if (!payload.site || !payload.username || !payload.password) {
      return alert("Site, username, and password are required.");
    }

    chrome.runtime.sendMessage(payload, handleSaveResponse);

    function handleSaveResponse(resp) {
      if (!resp) return alert("No response from background.");

      switch (resp.status) {
        case "success":
          alert("Password saved!");
          break;

        case "overwritten":
          alert("Existing password overwritten.");
          break;

        case "exists":
          if (
            confirm(
              `Credentials already stored for “${payload.site}”.\n` +
                "Overwrite existing entry?"
            )
          ) {
            chrome.runtime.sendMessage(
              { ...payload, force: true },
              (r2) => {
                if (r2?.status === "overwritten" || r2?.status === "success") {
                  alert("Password overwritten.");
                } else {
                  alert(`Error: ${r2?.message || "unknown"}`);
                }
              }
            );
          }
          break;

        default:
          alert(`Error: ${resp.message || "unknown"}`);
      }
    }
  };

  /* ----------- show credentials ----------- */
  qs("showPassword").onclick = () => {
    let site = qs("site").value.trim();

    const fill = (entry) => {
      qs("username").value = entry.username;
      qs("password").value = entry.password;
    };

    const fetchCred = (host) =>
      chrome.runtime.sendMessage(
        { action: "getPassword", site: host },
        (r) => {
          r?.entry
            ? fill(r.entry)
            : alert(`No password saved for ${host}`);
        }
      );

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

  /* ----------- import from USB (plain‑text dump) ----------- */

  // const loadBtn = document.getElementById("loadFromUSB");
  // const fileInput = document.getElementById("filePicker");

  // if (loadBtn && fileInput) {
  //   loadBtn.onclick = () => fileInput.click();
  // } else {
  //   console.warn("Missing DOM elements: loadFromUSB or filePicker");
  // }
  // qs("loadFromUSB").onclick = () => qs("filePicker").click();

  // qs("filePicker").onchange = (ev) => {
  //   const file = ev.target.files[0];
  //   if (!file) return;

  //   const reader = new FileReader();
  //   reader.onload = (e) => {
  //     const entries = [];
  //     let current = {};
  //     e.target.result
  //       .split("\n")
  //       .map((l) => l.trim())
  //       .forEach((line) => {
  //         if (line.startsWith("Website:")) {
  //           current.site = line.slice(8).trim();
  //         } else if (line.startsWith("Username:")) {
  //           current.username = line.slice(9).trim();
  //         } else if (line.startsWith("Password:")) {
  //           current.password = line.slice(9).trim();
  //           if (current.site && current.username && current.password) {
  //             entries.push(current);
  //             current = {};
  //           }
  //         }
  //       });

  //     if (!entries.length) return alert("No entries found in the file.");

  //     chrome.runtime.sendMessage(
  //       { action: "importFromUSB", data: entries },
  //       (r) => {
  //         if (r?.status === "imported") {
  //           alert(`Imported ${r.count} passwords.`);
  //         } else {
  //           alert(`Error: ${r?.message || "unknown"}`);
  //         }
  //       }
  //     );
  //   };
  //   reader.readAsText(file);
  // };


  /* ----------- export to USB ----------- */
  qs("saveToUSB")?.addEventListener("click", () =>
    chrome.runtime.sendMessage({ action: "exportToUSB" })
  );
});
