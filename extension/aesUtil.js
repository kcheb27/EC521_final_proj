/* PBKDF2 → AES‑CBC – no salt (matches backend) */
async function deriveKey(pass) {
    const base = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(pass),
      { name: "PBKDF2" },
      false,
      ["deriveKey"]
    );
    return crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: new Uint8Array(0), iterations: 100000, hash: "SHA-256" },
      base,
      { name: "AES-CBC", length: 256 },
      false,
      ["encrypt", "decrypt"]
    );
  }
  
  function pad(data) {
    const padLen = 16 - (data.length % 16);
    const out = new Uint8Array(data.length + padLen);
    out.set(data);
    out.fill(padLen, data.length);
    return out;
  }
  function unpad(arr) {
    return arr.slice(0, arr.length - arr[arr.length - 1]);
  }
  
  async function encryptJSON(obj, pass) {
    const key = await deriveKey(pass);
    const iv = crypto.getRandomValues(new Uint8Array(16));
    const plain = pad(new TextEncoder().encode(JSON.stringify(obj)));
    const buf = await crypto.subtle.encrypt({ name: "AES-CBC", iv }, key, plain);
    return {
      iv: btoa(String.fromCharCode(...iv)),
      ciphertext: btoa(String.fromCharCode(...new Uint8Array(buf))),
      password: pass            // communication password echo
    };
  }
  
  async function decryptJSON(ivB64, ctB64, pass) {
    const key = await deriveKey(pass);
    const iv = Uint8Array.from(atob(ivB64), c => c.charCodeAt(0));
    const ct = Uint8Array.from(atob(ctB64), c => c.charCodeAt(0));
    const plain = await crypto.subtle.decrypt({ name: "AES-CBC", iv }, key, ct);
    const un = unpad(new Uint8Array(plain));
    return JSON.parse(new TextDecoder().decode(un));
  }
  