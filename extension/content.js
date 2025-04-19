(async () => {
  const COMM_PASS = "fixedCommPassword";
  const API = "http://localhost:5000";

  const dbPass = prompt("DB password for autofill:");
  if (!dbPass) return;

  const domain = location.hostname.replace(/^www\./, "");
  const res = await fetch(`${API}/api/passwords/${encodeURIComponent(domain)}`, {
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body: JSON.stringify({ db_password: dbPass, password: COMM_PASS })
  });
  const j = await res.json();
  if (!j.iv) return;

  const { username, password } = await decryptJSON(j.iv, j.ciphertext, COMM_PASS);

  const u = document.querySelector(
    'input[type="text"], input[name*="user" i], input[name*="email" i]'
  );
  const p = document.querySelector('input[type="password"]');
  if (u) u.value = username;
  if (p) p.value = password;
})();
