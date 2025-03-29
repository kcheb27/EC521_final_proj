/* background.js */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "savePassword") {
    chrome.storage.local.set({ [request.site]: request.password }, () => {
      sendResponse({ status: "success" });
    });
    return true;
  }
  if (request.action === "getPassword") {
    chrome.storage.local.get(request.site, (data) => {
      sendResponse({ password: data[request.site] || "" });
    });
    return true;
  }
});