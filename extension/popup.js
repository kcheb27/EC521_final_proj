document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("save").addEventListener("click", () => {
      const site = document.getElementById("site").value;
      const password = document.getElementById("password").value;
      
      chrome.runtime.sendMessage({ action: "savePassword", site, password }, (response) => {
        if (response.status === "success") {
          alert("Password saved!");
        }
      });
    });
  });
  
  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("showPassword").addEventListener("click", () => {
        const site = document.getElementById("site").value;
        chrome.runtime.sendMessage({ action: "getPassword", site }, (response) => {
        if (response.password) {
            alert(`Password for ${site}: ${response.password}`);
        } else {
            alert(`No password saved for ${site}`);
        }
        });
    });
  });
    