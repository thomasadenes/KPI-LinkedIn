"""Synchronisation Notion -> page chiffrée index.html.

Variables d'environnement : NOTION_TOKEN, KPI_PASSWORD.
Option --fixture DOSSIER : lit des réponses Notion enregistrées (tests hors ligne).
Option --out FICHIER : fichier de sortie (défaut index.html à la racine du dépôt).
"""
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
import protect  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DS = os.environ.get("POSTS_DS", "2b685b85-3c98-819a-a4c8-000be1ab0080")
SUBS_DS = os.environ.get("SUBS_DS", "2ed85b85-3c98-8061-84bb-000b072914e0")
START = os.environ.get("KPI_START", "2026-01-01")
END = os.environ.get("KPI_END", "2026-10-31")
PAGE_MAP = {"ADENES Fr": "ADENES France"}
EXCLUDED = {"batifive"}
MOIS_L = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
API = "https://api.notion.com/v1"
VERSION = "2025-09-03"

args = sys.argv[1:]
FIXTURE = args[args.index("--fixture") + 1] if "--fixture" in args else None
OUT = args[args.index("--out") + 1] if "--out" in args else os.path.join(ROOT, "index.html")
PW = os.environ["KPI_PASSWORD"]


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(6):
        rq = urllib.request.Request(API + path, data=data, method=method, headers={
            "Authorization": "Bearer " + os.environ["NOTION_TOKEN"], "Notion-Version": VERSION, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(rq, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(float(e.headers.get("Retry-After") or 2 * (attempt + 1)))
                continue
            raise RuntimeError(f"Notion {e.code} sur {path} : {e.read()[:300]!r}")
    raise RuntimeError("Notion : trop de tentatives")


def query_all(ds, flt=None):
    if FIXTURE:
        return json.load(open(os.path.join(FIXTURE, "posts.json" if ds == POSTS_DS else "subs.json"), encoding="utf-8"))
    out, cursor = [], None
    while True:
        body = {"page_size": 100}
        if flt:
            body["filter"] = flt
        if cursor:
            body["start_cursor"] = cursor
        r = call("POST", f"/data_sources/{ds}/query", body)
        out += r["results"]
        if not r.get("has_more"):
            return out
        cursor = r["next_cursor"]


def plain(rt):
    return "".join(x.get("plain_text", "") for x in rt or [])


def prop(page, name):
    return page["properties"].get(name) or {}


def num(page, name):
    return prop(page, name).get("number")


def sel(page, name):
    s = prop(page, name).get("select")
    return s["name"] if s else None


def day(page, name):
    d = prop(page, name).get("date")
    return d["start"][:10] if d and d.get("start") else None


# --- 1. publications
posts = query_all(POSTS_DS, {"and": [
    {"property": "Date de publication", "date": {"on_or_after": START}},
    {"property": "Date de publication", "date": {"on_or_before": END}}]})
rows, posts_all = [], []
for p in posts:
    page = sel(p, "Page")
    page = PAGE_MAP.get(page, page)
    date = day(p, "Date de publication")
    if not page or not date or page.lower() in EXCLUDED or not (START <= date <= END):
        continue
    nom = plain(prop(p, "Nom").get("title")).strip()
    impr = num(p, "Impressions")
    statut = (prop(p, "Statut").get("status") or {}).get("name")
    posts_all.append({"page": page, "date": date, "statut": statut, "kpi": bool(impr)})
    if impr and impr > 0:
        z = lambda k: num(p, k) or 0
        rows.append({"id": p["id"], "page": page, "date": date, "fmt": sel(p, "Format"), "nom": nom,
                     "url": prop(p, "URL").get("url"), "impr": impr, "clics": z("Clics"), "reac": z("Réactions"),
                     "com": z("Commentaires"), "rep": z("Repartages"), "eng_saisi": num(p, "Taux d'engagement")})
rows.sort(key=lambda r: (r["date"], r["page"], r["nom"]), reverse=True)

# --- 2. abonnés
subs = defaultdict(list)
for p in query_all(SUBS_DS):
    page, d, v = sel(p, "Page"), day(p, "Date de données"), num(p, "Abonnés")
    if page and d and v is not None and page.lower() not in EXCLUDED:
        subs[PAGE_MAP.get(page, page)].append([d, v])

# --- 3. textes des posts affichés dans les TOP / FLOP (ceux déjà connus sont repris du référentiel chiffré)
ref = json.loads(protect.unseal(json.load(open(os.path.join(ROOT, "scripts", "reference.enc"))), PW))
key = lambda r: "|".join([r["page"], r["date"], r["nom"]])
need = {}
for pg in [None] + sorted({r["page"] for r in rows}):
    sub = [r for r in rows if pg is None or r["page"] == pg]
    for r in sorted(sub, key=lambda r: -r["impr"])[:10] + sorted([r for r in sub if r["impr"] > 1], key=lambda r: r["impr"])[:10]:
        if key(r) not in ref["contents"]:
            need[key(r)] = r["id"]


def page_text(pid):
    if FIXTURE:
        return None
    parts, cursor = [], None
    while True:
        r = call("GET", f"/blocks/{pid}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else ""))
        for b in r["results"]:
            t = b.get(b["type"], {})
            if isinstance(t, dict) and "rich_text" in t:
                parts.append(plain(t["rich_text"]))
        if not r.get("has_more"):
            break
        cursor = r["next_cursor"]
    text = "\n".join(parts).strip()
    return text[:1800]


texts = {}
for k, pid in need.items():
    try:
        txt = page_text(pid)
        if txt is not None:
            texts[k] = txt
    except RuntimeError as e:  # un texte manquant ne doit pas bloquer la synchronisation
        print("texte ignoré :", k, e)
    time.sleep(0.34)

today = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
data = {"start": START, "end": END, "rows": rows, "posts_all": posts_all, "subs": subs, "texts": texts}
tmp = tempfile.mkdtemp()
dj, rj, hj = (os.path.join(tmp, x) for x in ("data.json", "ref.json", "kpi.html"))
json.dump(data, open(dj, "w", encoding="utf-8"), ensure_ascii=False)
json.dump(ref, open(rj, "w", encoding="utf-8"), ensure_ascii=False)
subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "site.py"), dj, rj, hj], check=True)
html = open(hj, encoding="utf-8").read()

# --- 4. publication seulement si le contenu a changé (le sel du chiffrement change à chaque exécution)
digest = hashlib.sha256(html.encode()).hexdigest()
state = os.path.join(ROOT, ".sync-state")
if os.path.exists(OUT) and os.path.exists(state) and open(state).read().strip() == digest:
    print("Aucun changement dans Notion : page inchangée.")
    sys.exit(0)
html = html.replace("@@UPDATED@@", f"{today.day} {MOIS_L[today.month - 1]} {today.year}")
open(OUT, "w", encoding="utf-8").write(protect.protected_page(html, PW, ref["favicon_b64"]))
open(state, "w").write(digest + "\n")
print(f"index.html régénéré : {len(rows)} posts avec KPI, {len(posts_all)} posts planifiés, mise à jour du {today}")
