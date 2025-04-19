const API = "http://localhost:5000";
const COMM_PASS = "fixedCommPassword";   // ← 与后端一致

const qs = id => document.getElementById(id);

qs("saveBtn").onclick = async () => {
  const dbPass = qs("dbPass").value.trim();
  const site   = qs("site").value.trim();
  const user   = qs("user").value.trim();
  const pwd    = qs("pwd").value.trim();
  if (!dbPass || !site || !user || !pwd) return alert("Fill all fields.");
  /* 加密业务字段 */
  const enc = await encryptJSON({ url: site, username: user, password: pwd }, COMM_PASS);
  enc.db_password = dbPass;            // 供后端派生 DB key
  const r = await fetch(`${API}/api/passwords`, {
    method: "POST", headers: { "Content-Type":"application/json" },
    body: JSON.stringify(enc)
  });
  const j = await r.json();
  alert(j.status === "added" ? "Saved." : JSON.stringify(j));
};

qs("showBtn").onclick = async () => {
  const dbPass = qs("dbPass").value.trim();
  const site   = qs("site").value.trim();
  if (!dbPass || !site) return alert("Need site & db password");
  const r = await fetch(`${API}/api/passwords/${encodeURIComponent(site)}`, {
    method:"POST", headers:{ "Content-Type":"application/json" },
    body: JSON.stringify({ db_password: dbPass, password: COMM_PASS })
  });
  const j = await r.json();
  if (!j.iv) return alert("Not found.");
  const dec = await decryptJSON(j.iv, j.ciphertext, COMM_PASS);
  qs("user").value = dec.username;
  qs("pwd").value  = dec.password;
};
