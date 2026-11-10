"""Chiffrement AES-256-GCM (clé PBKDF2-SHA256, 600 000 itérations), déchiffré côté navigateur."""
import base64, json, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 600_000
b64 = lambda x: base64.b64encode(x).decode()
unb64 = lambda s: base64.b64decode(s)


def _key(pw, salt, it):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=it).derive(pw.encode())


def seal(data: bytes, pw: str) -> dict:
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    return {"s": b64(salt), "v": b64(iv), "i": ITER, "c": b64(AESGCM(_key(pw, salt, ITER)).encrypt(iv, data, None))}


def unseal(p: dict, pw: str) -> bytes:
    return AESGCM(_key(pw, unb64(p["s"]), p["i"])).decrypt(unb64(p["v"]), unb64(p["c"]), None)


TEMPLATE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<meta name="referrer" content="no-referrer">
<link rel="icon" type="image/png" href="data:image/png;base64,__FAV__">
<title>Accès protégé</title>
<style>
:root{--navy:#002F6B;--bg:#fff;--ink:#0b2447;--mute:#5a6b82;--line:#c9d8e6}
@media (prefers-color-scheme:dark){:root{--bg:#0a1626;--ink:#e6eef8;--mute:#9db0c7;--line:#2a4566;--navy:#8cc8e6}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font:16px/1.5 Calibri,Carlito,"Segoe UI",system-ui,sans-serif;padding:16px}
form{width:100%;max-width:380px}
h1{font-size:26px;color:var(--navy);margin:0 0 6px}
p{margin:0 0 18px;color:var(--mute)}
label{display:block;font-weight:700;margin-bottom:6px}
input{width:100%;padding:12px 14px;font:inherit;color:var(--ink);background:transparent;border:1.5px solid var(--line);border-radius:10px}
input:focus{outline:2px solid var(--navy);outline-offset:1px}
button{margin-top:14px;width:100%;padding:12px;font:inherit;font-weight:700;color:#fff;background:#002F6B;border:0;border-radius:10px;cursor:pointer}
@media (prefers-color-scheme:dark){button{background:#8cc8e6;color:#0a1626}}
button[disabled]{opacity:.6;cursor:wait}
#err{min-height:24px;margin:10px 0 0;color:#b3261e;font-size:15px}
@media (prefers-color-scheme:dark){#err{color:#ffb4ab}}
</style></head><body>
<form id="f" autocomplete="off">
<h1>Accès protégé</h1>
<p>Saisissez le mot de passe pour afficher la page.</p>
<label for="pw">Mot de passe</label>
<input id="pw" type="password" autocomplete="current-password" autofocus required>
<button id="go" type="submit">Afficher</button>
<div id="err" role="alert" aria-live="polite"></div>
</form>
<script>
const P=__PAYLOAD__;
const b64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function dec(pw){
  const km=await crypto.subtle.importKey('raw',new TextEncoder().encode(pw),'PBKDF2',false,['deriveKey']);
  const key=await crypto.subtle.deriveKey({name:'PBKDF2',salt:b64(P.s),iterations:P.i,hash:'SHA-256'},km,{name:'AES-GCM',length:256},false,['decrypt']);
  const pt=await crypto.subtle.decrypt({name:'AES-GCM',iv:b64(P.v)},key,b64(P.c));
  return new TextDecoder().decode(pt);
}
document.getElementById('f').addEventListener('submit',async e=>{
  e.preventDefault();
  const go=document.getElementById('go'),err=document.getElementById('err'),inp=document.getElementById('pw');
  err.textContent='';go.disabled=true;go.textContent='Vérification…';
  try{
    if(!window.crypto||!crypto.subtle)throw new Error('nocrypto');
    const html=await dec(inp.value);
    document.open();document.write(html);document.close();
  }catch(x){
    err.textContent=(x&&x.message==='nocrypto')?'Ce navigateur ne permet pas le déchiffrement (utilisez la version https).':'Mot de passe incorrect.';
    go.disabled=false;go.textContent='Afficher';inp.select();
  }
});
</script></body></html>
"""


def protected_page(html: str, pw: str, fav_b64: str) -> str:
    payload = json.dumps(seal(html.encode("utf-8"), pw))
    return TEMPLATE.replace("__PAYLOAD__", payload).replace("__FAV__", fav_b64)
