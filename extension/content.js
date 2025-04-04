document.addEventListener("DOMContentLoaded", () => {
    const passwordFields = document.querySelectorAll("input[type='password']");
  
    // Autofill the password if available
    if (passwordFields.length > 0) {
      chrome.runtime.sendMessage({ action: "getPassword", site: window.location.hostname }, (response) => {
        if (response.password) {
          passwordFields[0].value = response.password;
        }
      });
    }
  
    // Add a button to alert the password on the page
    const alertButton = document.createElement('button');
    alertButton.textContent = 'Show Password';
    alertButton.style.position = 'fixed';
    alertButton.style.bottom = '10px';
    alertButton.style.right = '10px';
    alertButton.style.padding = '10px';
    alertButton.style.backgroundColor = '#f44336';
    alertButton.style.color = 'white';
    alertButton.style.border = 'none';
    alertButton.style.cursor = 'pointer';
    document.body.appendChild(alertButton);
  
    alertButton.addEventListener('click', () => {
      chrome.runtime.sendMessage({ action: "getPassword", site: window.location.hostname }, (response) => {
        if (response.password) {
          alert(`Password for ${window.location.hostname}: ${response.password}`);
        } else {
          alert(`No password saved for ${window.location.hostname}`);
        }
      });
    });
  });


// Autofill Script
// Get the site's hostname
const hostname = window.location.hostname;

// Ask background for saved credentials
chrome.runtime.sendMessage({ action: "getPassword", site: hostname }, (response) => {
  if (response?.entry) {
    const { username, password } = response.entry;

    // Flexible username/email selector
    const usernameField = document.querySelector(
      'input[type="text"], input[type="email"], input[name*="user" i], input[name*="email" i], input[name*="login" i], input[name="username"]'
    );

    // Password field
    const passwordField = document.querySelector('input[type="password"]');

    if (usernameField) {
      usernameField.value = username;
      usernameField.dispatchEvent(new Event("input", { bubbles: true }));
    }

    if (passwordField) {
      passwordField.value = password;
      passwordField.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }
});
  