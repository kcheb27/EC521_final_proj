document.addEventListener("DOMContentLoaded", () => {
  const saveBtn = document.getElementById("save");
  const showBtn = document.getElementById("showPassword");
  const loadBtn = document.getElementById("loadFromUSB");
  const saveUSBBtn = document.getElementById("saveToUSB");
  const filePicker = document.getElementById("filePicker");

  saveBtn.addEventListener("click", () => {
    const site = document.getElementById("site").value;
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    chrome.runtime.sendMessage(
      { action: "savePassword", site, username, password },
      (response) => {
        if (response?.status === "success") {
          alert("Password saved!");
        }
      }
    );
  });

  showBtn.addEventListener("click", () => {
    let site = document.getElementById("site").value.trim();

    if (!site) {
      // Get current tab's URL
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs.length > 0) {
          try {
            const url = new URL(tabs[0].url);
            site = url.hostname;
            document.getElementById("site").value = site; // Auto-fill the field

            chrome.runtime.sendMessage({ action: "getPassword", site }, (response) => {
              if (response?.entry) {
                document.getElementById("username").value = response.entry.username;
                document.getElementById("password").value = response.entry.password;
              } else {
                alert(`No password saved for ${site}`);
              }
            });
          } catch (e) {
            alert("Could not extract hostname.");
          }
        }
      });
    } else {
      chrome.runtime.sendMessage({ action: "getPassword", site }, (response) => {
        if (response?.entry) {
          document.getElementById("username").value = response.entry.username;
          document.getElementById("password").value = response.entry.password;
        } else {
          alert(`No password saved for ${site}`);
        }
      });
    }
  });

  loadBtn.addEventListener("click", () => {
    filePicker.click();
  });

  filePicker.addEventListener("change", (event) => {
    const file = event.target.files[0];
    const reader = new FileReader();

    reader.onload = function (e) {
      const text = e.target.result;
      const entries = [];
      const lines = text.split('\n').map(line => line.trim());
      let currentEntry = {};

      for (const line of lines) {
        if (line.startsWith("Website:")) {
          currentEntry.site = line.substring("Website:".length).trim();
        } else if (line.startsWith("Username:")) {
          currentEntry.username = line.substring("Username:".length).trim();
        } else if (line.startsWith("Password:")) {
          currentEntry.password = line.substring("Password:".length).trim();
          if (currentEntry.site && currentEntry.username && currentEntry.password) {
            entries.push(currentEntry);
            currentEntry = {}; // Reset for the next entry
          }
        }
      }

      if (entries.length > 0) {
        chrome.runtime.sendMessage({ action: "importFromUSB", data: entries }, (response) => {
          alert(`Successfully loaded ${entries.length} passwords from USB.`);
        });
      } else {
        alert("No password entries found in the file.");
      }
    };

    reader.readAsText(file);
  });

  saveUSBBtn.addEventListener("click", () => {
    chrome.runtime.sendMessage({ action: "exportToUSB" });
  });
});