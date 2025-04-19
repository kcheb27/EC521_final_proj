chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "savePassword") {
    const { site, username, password } = request;
    chrome.storage.local.get("passwords", (data) => {
      const passwords = data.passwords || {};
      passwords[site] = { username, password };
      chrome.storage.local.set({ passwords }, () => {
        sendResponse({ status: "success" });
      });
    });
    return true;
  }

  if (request.action === "getPassword") {
    const { site } = request;
    chrome.storage.local.get("passwords", (data) => {
      const entry = data.passwords?.[site];
      sendResponse({ entry });
    });
    return true;
  }

  if (request.action === "importFromUSB") {
    const newData = request.data;
    const importedPasswords = {};
  
    newData.forEach(({ site, username, password }) => {
      importedPasswords[site] = { username, password };
    });
  
    // Merge with existing passwords (optional — if you don’t want to overwrite)
    chrome.storage.local.get("passwords", (data) => {
      const existingPasswords = data.passwords || {};
      const mergedPasswords = { ...existingPasswords, ...importedPasswords };
  
      chrome.storage.local.set({ passwords: mergedPasswords }, () => {
        sendResponse({ status: "imported", count: newData.length });
      });
    });
  
    return true;
  }

  if (request.action === "exportToUSB") {
    chrome.storage.local.get("passwords", (data) => {
      // Format as plain text
      let txtContent = "=== Saved Passwords ===\n\n";
      
      const entries = Object.entries(data.passwords || {});
      
      if (entries.length === 0) {
        txtContent += "No passwords stored yet.";
      } else {
        entries.forEach(([site, {username, password}], index) => {
          txtContent += `Entry #${index + 1}\n`;
          txtContent += `Website: ${site}\n`;
          txtContent += `Username: ${username}\n`;
          txtContent += `Password: ${password}\n\n`;
        });
        txtContent += `=== Total: ${entries.length} passwords ===`;
      }

      // Create download using chrome.downloads API
      chrome.downloads.download({
        url: "data:text/plain;charset=utf-8," + encodeURIComponent(txtContent),
        filename: "my_passwords.txt",
        saveAs: true,
        conflictAction: "uniquify"
      }, () => {
        if (chrome.runtime.lastError) {
          console.error("Download failed:", chrome.runtime.lastError);
          sendResponse({ status: "error", message: chrome.runtime.lastError.message });
        } else {
          sendResponse({ status: "success" });
        }
      });
    });
    return true;
  }
});