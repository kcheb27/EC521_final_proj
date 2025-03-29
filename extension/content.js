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
  