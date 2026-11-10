import sys, html, json, re, datetime
from collections import defaultdict

NB = " "
n = lambda v: f"{v:,.0f}".replace(",", NB)
pct = lambda v, d=1: f"{v:.{d}f}".replace(".", ",") + NB + "%"
dec = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
sgn = lambda v, d=1: ("+" if v >= 0 else "−") + pct(abs(v), d)
esc = html.escape

DATA = json.load(open(sys.argv[1], encoding="utf-8"))
REF = json.load(open(sys.argv[2], encoding="utf-8"))
OUT = sys.argv[3]
START, END = DATA["start"], DATA["end"]
rows = [dict(r) for r in DATA["rows"]]
for r in rows:
    r["inter"] = r["clics"] + r["reac"] + r["com"] + r["rep"]
    r["eng"] = r["inter"] / r["impr"] * 100
LOGO = REF["logo_svg"]
FAV = REF["favicon_b64"]
KEY = lambda r: "|".join([r["page"], r["date"], r["nom"]])
TEXTS = dict(REF.get("contents", {}))
for k, v in DATA.get("texts", {}).items():
    if k not in TEXTS:
        TEXTS[k] = {"text": v}
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS_L = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
ddmm = lambda d: d[8:10] + "/" + d[5:7]
S = lambda k, rs: sum(r[k] for r in rs)
eng_w = lambda rs: S("inter", rs) / S("impr", rs) * 100
T = S("impr", rows)
by_page = defaultdict(list)
for r in rows:
    by_page[r["page"]].append(r)

SUB_ORDER = ["ELEX", "ADENES France", "ROADIA", "3C", "VERING", "ADENES ACADEMY"]
SUBS, SUB_D0, SUB_D1 = [], {}, {}
for pg in SUB_ORDER + sorted(set(DATA["subs"]) - set(SUB_ORDER)):
    hist = sorted((d, v) for d, v in DATA["subs"].get(pg, []) if START <= d <= END)
    if len(hist) >= 1:
        SUBS.append((pg, hist[0][1], hist[-1][1]))
        SUB_D0[pg], SUB_D1[pg] = hist[0][0], hist[-1][0]
s0, s1 = sum(a for _, a, _ in SUBS), sum(b for _, _, b in SUBS)
BASE = max(set(SUB_D0.values()), key=list(SUB_D0.values()).count)
LAST = max(SUB_D1.values())
g = lambda a, b: (b - a) / a * 100

# Pages proposées dans les menus déroulants (ordre : impressions décroissantes)
PAGES = [k for k, _ in sorted(by_page.items(), key=lambda kv: -S("impr", kv[1]))]
OPTIONS = [("Toutes les pages", None)] + [(p, p) for p in PAGES]


def short(t, k=60):
    t = " ".join(t.replace("<p>", " ").replace("</p>", " ").split())
    return t if len(t) <= k else t[: k - 1].rstrip() + "…"


def hbars(items, fmt="", hi=0):
    """items: (label, valeur, texte)"""
    if not items:
        return ""
    mx = max(v for _, v, _ in items) or 1
    out = ['<div class="bars">']
    for i, (lab, v, txt) in enumerate(items):
        out.append(f'<div class="bar"><span class="lbl">{esc(lab)}</span><span class="track"><span class="fill{" hi" if i == hi else ""}" style="width:{v / mx * 100:.1f}%"></span></span><span class="val">{txt}</span></div>')
    out.append("</div>")
    return "".join(out)


def table(head, body, num_from=1, cls=""):
    th = "".join(f'<th class="{"num" if j >= num_from else ""}">{esc(h)}</th>' for j, h in enumerate(head))
    trs = []
    for r in body:
        tds = "".join(f'<td class="{"num" if j >= num_from else ""}">{c}</td>' for j, c in enumerate(r))
        trs.append(f"<tr>{tds}</tr>")
    return f'<div class="scroll"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'


def variants(grp, fn):
    """Génère une variante par option du menu (Toutes les pages, puis chaque page)."""
    out = []
    for i, (_, p) in enumerate(OPTIONS):
        sub = rows if p is None else by_page[p]
        out.append(f'<div class="var{" on" if i == 0 else ""}" data-grp="{grp}" data-v="{i}">{fn(sub, i)}</div>')
    return "".join(out)


def picker(grp):
    opts = "".join(f'<option value="{i}">{esc(lab)}</option>' for i, (lab, _) in enumerate(OPTIONS))
    return f'<label class="flt">Page LinkedIn <select data-grp="{grp}" aria-label="Filtrer par page LinkedIn">{opts}</select></label>'


# --- Abonnés / publications
subs_sorted = sorted(SUBS, key=lambda x: -g(x[1], x[2]))
subs_bars = hbars([(nm, g(a, b), pct(g(a, b))) for nm, a, b in subs_sorted])
subs_tbl = table(["Page", ddmm(BASE), "Au " + ddmm(LAST), "Gain", "Évol."],
                 [[esc(nm), n(a), n(b), "+" + NB + n(b - a), "+" + pct(g(a, b))] for nm, a, b in SUBS]
                 + [["<strong>Total</strong>", f"<strong>{n(s0)}</strong>", f"<strong>{n(s1)}</strong>", f"<strong>+{NB}{n(s1 - s0)}</strong>", f"<strong>+{pct(g(s0, s1))}</strong>"]], cls="fit")

pages = sorted(by_page.items(), key=lambda kv: -S("impr", kv[1]))
pages_bars = hbars([(k, S("impr", v), n(S("impr", v))) for k, v in pages])
pages_tbl = table(["Page", "Posts", "Impressions", "Réactions", "Commentaires", "Repartages", "Engagement"],
                  [[esc(k), str(len(v)), n(S("impr", v)), n(S("reac", v)), n(S("com", v)), n(S("rep", v)), pct(eng_w(v))] for k, v in pages]
                  + [["<strong>Total</strong>", f"<strong>{len(rows)}</strong>", f"<strong>{n(T)}</strong>", f"<strong>{n(S('reac', rows))}</strong>",
                      f"<strong>{n(S('com', rows))}</strong>", f"<strong>{n(S('rep', rows))}</strong>", f"<strong>{pct(eng_w(rows))}</strong>"]])

# --- Types de publication (filtrable par page)
FMTS = ["Carrousel", "Repartage", "Vidéo", "Image"]


def fmt_block(sub, vi):
    fm_rows = [r for r in sub if r["impr"] > 1 and r["fmt"] in FMTS]
    fstat = []
    for f in FMTS:
        v = [r for r in fm_rows if r["fmt"] == f]
        if v:
            fstat.append(dict(f=f, k=len(v), impr=S("impr", v) / len(v), eng=eng_w(v), ctr=S("clics", v) / S("impr", v) * 100, reac=S("reac", v) / len(v)))
    if not fstat:
        return '<p class="note">Aucun post avec format renseigné pour cette page.</p>'
    fstat.sort(key=lambda d: -d["eng"])
    by_reach = sorted(fstat, key=lambda d: -d["impr"])
    eng = hbars([(f'{d["f"]} ({d["k"]})', d["eng"], pct(d["eng"])) for d in fstat])
    rea = hbars([(f'{d["f"]} ({d["k"]})', d["impr"], n(round(d["impr"]))) for d in by_reach])
    tbl = table(["Format", "Posts", "Impr. / post", "Engagement", "Taux de clic", "Réactions / post"],
                [[esc(d["f"]), str(d["k"]), n(round(d["impr"])), pct(d["eng"]), pct(d["ctr"]), n(round(d["reac"]))] for d in fstat], cls="fit")
    be, br = fstat[0], by_reach[0]
    if len(fstat) == 1:
        msg = f'Un seul format représenté ({esc(be["f"])}) : pas de comparaison possible pour cette page.'
    else:
        msg = f'<strong>{esc(be["f"])}</strong> : meilleur taux d’engagement ({pct(be["eng"])}). ' + (
            f'<strong>{esc(br["f"])}</strong> : plus forte portée ({n(round(br["impr"]))} impressions par post).' if br["f"] != be["f"] else "Il est aussi le format qui porte le plus loin.")
    k = sum(d["k"] for d in fstat)
    small = f" Échantillon réduit ({k} posts) : à lire avec prudence." if k < 10 else ""
    return (f'<div class="grid2"><div><h3>Taux d\'engagement</h3>{eng}</div><div><h3>Impressions moyennes par post</h3>{rea}</div></div>'
            f'{tbl}<div class="msg">{msg}{small}</div>')


fmt_html = variants("fmt", fmt_block)

# --- Rythme mensuel (filtrable par page)
LASTMO = max(r["date"][5:7] for r in rows)
months = [("01", "Janv."), ("02", "Févr."), ("03", "Mars"), ("04", "Avr."), ("05", "Mai"), ("06", "Juin"), ("07", "Juil."), ("08", "Août"), ("09", "Sept."), ("10", "Oct.")]


def months_block(sub, vi):
    by_mo = defaultdict(int)
    cnt = defaultdict(int)
    for r in sub:
        by_mo[r["date"][5:7]] += r["impr"]
        cnt[r["date"][5:7]] += 1
    mx = max(by_mo.values()) if by_mo else 1
    top3 = sorted(by_mo, key=lambda m: -by_mo[m])[:3]
    cols = []
    for m, lab in months:
        v = by_mo.get(m)
        if m > LASTMO:
            cols.append(f'<div class="col"><span class="cv">n/d</span><span class="cb empty"></span><span class="cl">{lab}</span></div>')
        else:
            h = (v or 0) / mx * 100
            cols.append(f'<div class="col"><span class="cv">{n(v or 0)}</span><span class="cb{" hi" if m in top3 and v else ""}" style="height:{max(h, 0.6):.1f}%"></span><span class="cl">{lab}</span></div>')
    return f'<div class="cols">{"".join(cols)}</div>'


months_html = variants("mo", months_block)

# --- Sliders TOP / FLOP (filtrables par page)
top10 = sorted(rows, key=lambda r: -r["impr"])[:10]
flop10 = sorted([r for r in rows if r["impr"] > 1], key=lambda r: r["impr"])[:10]


def clean_title(t):
    return " ".join(t.replace("<p>", " ").replace("</p>", " ").split())


def slider(lst):
    if not lst:
        return '<p class="note">Aucun post pour cette page.</p>'
    cards = []
    for i, r in enumerate(lst, 1):
        known = KEY(r) in TEXTS
        c = TEXTS.get(KEY(r), {})
        title = esc(clean_title(r["nom"]))
        if r["url"]:
            title = f'<a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">{title}</a>'
        txt = (c.get("text") or "").strip()
        if txt:
            body = "".join(f"<p>{esc(par).replace(chr(10), '<br>')}</p>" for par in re.split(r"\n\s*\n", txt) if par.strip())
        elif known:
            body = '<p class="none">Texte de la publication non renseigné dans Notion.</p>'
        else:
            body = '<p class="none">Texte non repris dans cette vue : voir le post sur LinkedIn.</p>'
        vd = (c.get("visual_desc") or "").strip()
        vis = f'<p class="vis">Visuel : {esc(vd)}</p>' if vd else ""
        kp = "".join(f'<div><b>{v}</b><span>{l}</span></div>' for v, l in
                     [(n(r["impr"]), "impressions"), (pct(r["eng"]), "engagement"), (n(r["clics"]), "clics"), (n(r["reac"]), "réactions"), (n(r["com"]), "commentaires"), (n(r["rep"]), "repartages")])
        cards.append(f'''<article class="slide"><div class="rk">{i}</div>
<h3>{title}</h3>
<p class="meta">{esc(r["page"])} · {esc(r["fmt"] or "format n/r")} · {r["date"][8:10]}/{r["date"][5:7]}/{r["date"][:4]}</p>
<div class="kp">{kp}</div>
{vis}<div class="txt">{body}</div></article>''')
    return (f'<div class="slider"><div class="track2">{"".join(cards)}</div>'
            f'<div class="ctrl"><button type="button" data-d="-1" aria-label="Précédent">‹</button><span class="cnt">1 / {len(lst)}</span><button type="button" data-d="1" aria-label="Suivant">›</button></div></div>')


top_html = variants("top", lambda sub, vi: slider(sorted(sub, key=lambda r: -r["impr"])[:10]))
flop_html = variants("flop", lambda sub, vi: slider(sorted([r for r in sub if r["impr"] > 1], key=lambda r: r["impr"])[:10]))

# =====================================================================
# Comparaison avec le PowerPoint « KPIs LinkedIn 2025-2026 » (sept. 2026)
# Périmètre : les 5 pages présentes dans le PowerPoint (hors ADENES ACADEMY et Adenes Monde).
# =====================================================================
P5 = ["ELEX", "ADENES France", "ROADIA", "3C", "VERING"]
# abonnés : S1 2025, S2 2025, S1 2026 (relevé de juillet 2026)
PPT_SUBS, PPT_ACT, PPT_TOT, PPT_ENG_S1_26 = REF["ppt"]["subs"], REF["ppt"]["act"], REF["ppt"]["tot"], REF["ppt"]["eng"]
OCT = {nm: b for nm, a, b in SUBS}
LM = int(LASTMO)
M1, M2 = 6, max(1, LM - 6)
LAB2 = "Juil.–" + MOIS[min(LM, 12) - 1] if LM >= 7 else "Juil.–sept."
ALL = [p for p in DATA["posts_all"] if p["statut"] == "Publié"]
PUBN = {"S1": {p: sum(1 for x in ALL if x["page"] == p and "2026-01-01" <= x["date"] <= "2026-06-30") for p in P5},
        "T3": {p: sum(1 for x in ALL if x["page"] == p and "2026-07-01" <= x["date"] <= f"2026-{max(LM, 7):02d}-31") for p in P5}}


def win(lo, hi, pgs=P5):
    return [r for r in rows if r["page"] in pgs and lo <= r["date"] <= hi]


W1, W2 = win("2026-01-01", "2026-06-30"), win("2026-07-01", f"2026-{max(LM, 7):02d}-31")
sd = lambda a, b: a / b if b else 0


def agg(rs):
    return dict(k=len(rs), impr=S("impr", rs), reac=S("reac", rs), com=S("com", rs), rep=S("rep", rs), eng=eng_w(rs) if rs else 0)


A1, A2 = agg(W1), agg(W2)
pub1, pub2 = sum(PUBN["S1"].values()), sum(PUBN["T3"].values())

# --- A. abonnés
tot = [sum(PPT_SUBS[p][i] for p in P5) for i in range(3)] + [sum(OCT[p] for p in P5)]
sub_rows = []
for p in P5:
    a, b, c = PPT_SUBS[p]
    o = OCT[p]
    sub_rows.append([esc(p), n(a), n(b), n(c), n(o), sgn(g(a, o)), sgn(g(c, o))])
sub_rows.append(["<strong>5 pages</strong>"] + [f"<strong>{n(x)}</strong>" for x in tot] + [f"<strong>{sgn(g(tot[0], tot[3]))}</strong>", f"<strong>{sgn(g(tot[2], tot[3]))}</strong>"])
cmp_subs_tbl = table(["Page", "S1 2025", "S2 2025", "S1 2026", "Au " + ddmm(LAST), "S1 25 → " + ddmm(LAST), "S1 26 → " + ddmm(LAST)], sub_rows, cls="fit")
cmp_subs_bars = hbars([(p, g(PPT_SUBS[p][0], OCT[p]), sgn(g(PPT_SUBS[p][0], OCT[p]))) for p in sorted(P5, key=lambda p: -g(PPT_SUBS[p][0], OCT[p]))])
gr = [g(tot[0], tot[1]), g(tot[1], tot[2]), g(tot[2], tot[3])]
MLAST = max(1, round((datetime.date.fromisoformat(LAST) - datetime.date(int(LAST[:4]), 7, 1)).days / 30.4))
best_sub = max(P5, key=lambda p: g(PPT_SUBS[p][0], OCT[p]))
cmp_tiles_a = (f'<div class="tiles t3"><div class="tile"><b>{sgn(g(tot[0], tot[3]))}</b><span>d\'abonnés sur 5 pages entre S1 2025 et le {ddmm(LAST)}/2026 ({n(tot[0])} → {n(tot[3])})</span></div>'
               f'<div class="tile"><b>{sgn(gr[0])} · {sgn(gr[1])} · {sgn(gr[2])}</b><span>S1→S2 2025 (6 mois) · S2 2025→juillet 2026 (≈6 mois) · juillet→{ddmm(LAST)} (≈{MLAST} mois)</span></div>'
               f'<div class="tile"><b>{esc(best_sub)}</b><span>plus forte croissance depuis S1 2025 ({sgn(g(PPT_SUBS[best_sub][0], OCT[best_sub]))})</span></div></div>')

# --- B. portée et rythme
im_m = (PPT_TOT["impr"][0] / 6, PPT_TOT["impr"][1] / 6, A1["impr"] / M1, A2["impr"] / M2)
pub_m = (sum(PPT_ACT[p]["pubs"][0] for p in P5) / 6, sum(PPT_ACT[p]["pubs"][1] for p in P5) / 6, pub1 / M1, pub2 / M2)
n_posts = (sum(PPT_ACT[p]["pubs"][0] for p in P5), sum(PPT_ACT[p]["pubs"][1] for p in P5), A1["k"], A2["k"])
im_post = (PPT_TOT["impr"][0] / n_posts[0], PPT_TOT["impr"][1] / n_posts[1], A1["impr"] / A1["k"], sd(A2["impr"], A2["k"]))
rea_k = (PPT_TOT["reac"][0] / PPT_TOT["impr"][0] * 1000, PPT_TOT["reac"][1] / PPT_TOT["impr"][1] * 1000, A1["reac"] / A1["impr"] * 1000, sd(A2["reac"], A2["impr"]) * 1000)
cmp_tot_tbl = table(["5 pages", "S1 2025", "S2 2025", "S1 2026", LAB2 + " 2026"], [
    ["Impressions / mois", n(im_m[0]), n(im_m[1]), n(im_m[2]), n(im_m[3])],
    ["Publications / mois", dec(pub_m[0]), dec(pub_m[1]), dec(pub_m[2]), dec(pub_m[3])],
    ["Impressions / post", n(im_post[0]), n(im_post[1]), n(im_post[2]), n(im_post[3])],
    ["Réactions / 1 000 impr.", dec(rea_k[0]), dec(rea_k[1]), dec(rea_k[2]), dec(rea_k[3])],
], cls="fit")
pp_rows = []
for p in P5:
    a, b = PPT_ACT[p]["im"]
    c = S("impr", [r for r in W1 if r["page"] == p]) / M1
    d = S("impr", [r for r in W2 if r["page"] == p]) / M2
    pp_rows.append([esc(p), n(a), n(b), n(c), n(d), sgn(g(a, c), 0)])
pp_rows.append(["<strong>5 pages</strong>"] + [f"<strong>{n(x)}</strong>" for x in im_m] + [f"<strong>{sgn(g(im_m[0], im_m[2]), 0)}</strong>"])
cmp_page_tbl = table(["Impressions / mois", "S1 2025", "S2 2025", "S1 2026", LAB2, "S1 26 vs S1 25"], pp_rows, cls="fit")
fewer, farther = pub_m[2] < pub_m[0], im_post[2] > im_post[0]
cmp_msg_b = ((f"Moins de posts, mais qui portent plus loin : " if fewer and farther else "Rythme et portée : ") +
             f"{dec(pub_m[2])} publications par mois en S1 2026 contre {dec(pub_m[0])} en S1 2025 ({sgn(g(pub_m[0], pub_m[2]), 0)}), "
             f"pour {n(im_post[2])} impressions par post contre {n(im_post[0])} ({sgn(g(im_post[0], im_post[2]), 0)}). " +
             (f"La portée mensuelle reste stable autour de {n(round(im_m[2], -3))} impressions ; " if abs(g(im_m[2], im_m[3])) < 15 else f"La portée mensuelle passe de {n(im_m[2])} à {n(im_m[3])} impressions ({LAB2}) ; ") +
             f"S2 2025 ({n(im_m[1])}) reste le point haut de la période.")

# --- C. engagement et écarts avec le PowerPoint
rk_rows = []
for p in P5:
    a, b = PPT_ACT[p]["im"]
    ra = PPT_ACT[p]["reac"][0] / (a * 6) * 1000
    rb = PPT_ACT[p]["reac"][1] / (b * 6) * 1000
    w1 = [r for r in W1 if r["page"] == p]
    w2 = [r for r in W2 if r["page"] == p]
    rc = S("reac", w1) / S("impr", w1) * 1000
    rd = S("reac", w2) / S("impr", w2) * 1000 if w2 else None
    rk_rows.append([esc(p), dec(ra), dec(rb), dec(rc), dec(rd) if rd is not None else "–"])
rk_rows.append(["<strong>5 pages</strong>"] + [f"<strong>{dec(x)}</strong>" for x in rea_k])
cmp_rea_tbl = table(["Réactions / 1 000 impr.", "S1 2025", "S2 2025", "S1 2026", LAB2], rk_rows, cls="fit")
eng_rows = []
for p in P5:
    w1 = [r for r in W1 if r["page"] == p]
    eng_rows.append([esc(p), pct(PPT_ENG_S1_26[p], 0), pct(eng_w(w1))])
cmp_eng_tbl = table(["Page", "Taux du PowerPoint (S1 2026)", "Recalculé (S1 2026)"], eng_rows, cls="fit")
fm_all = [r for r in rows if r["impr"] > 1 and r["fmt"] in FMTS]
fm_st = sorted([(eng_w([r for r in fm_all if r["fmt"] == f]), f) for f in FMTS if any(r["fmt"] == f for r in fm_all)], reverse=True)
car = dict((f, e) for e, f in fm_st).get("Carrousel")
others = [e for e, f in fm_st if f != "Carrousel"]
if fm_st and fm_st[0][1] == "Carrousel" and others:
    c1 = ("Le carrousel est le format qui fonctionne le mieux.", f"Confirmé : {pct(car)} d'engagement contre {dec(min(others))} à {pct(max(others))} pour les autres formats.")
elif fm_st:
    c1 = ("Le carrousel est le format qui fonctionne le mieux.", f"Non confirmé : {fm_st[0][1]} a le meilleur taux d'engagement ({pct(fm_st[0][0])}).")
else:
    c1 = ("Le carrousel est le format qui fonctionne le mieux.", "Pas assez de posts avec format renseigné.")
slow = gr[2] / MLAST < gr[1] / 6.5
confirm = [
    c1,
    ("Une perte de croissance sur les derniers mois.", ("Confirmé" if slow else "Non confirmé") + f" : {sgn(gr[2])} d'abonnés entre juillet et le {ddmm(LAST)}, contre {sgn(gr[1])} sur les six mois précédents."),
    ("Un rythme de publication fractionné.", ("Confirmé" if fewer else "Non confirmé") + f" : {dec(pub_m[2])} publications par mois en S1 2026 contre {dec(pub_m[0])} en S1 2025 ; {LAB2.lower()} : {dec(pub_m[3])} sur ces 5 pages."),
]
ecarts = REF["ecarts"]
cf_html = "".join(f'<div class="card ok"><h3>{esc(h)}</h3><p>{esc(t)}</p></div>' for h, t in confirm)
ec_html = "".join(f'<div class="card"><h3>{esc(h)}</h3><p>{esc(t)}</p></div>' for h, t in ecarts)

# --- points de vigilance calculés à partir de Notion
vig = []
nokpi = defaultdict(lambda: [0, 0])
for p in DATA["posts_all"]:
    if p["statut"] == "Publié":
        nokpi[p["date"][5:7]][1] += 1
        if not p["kpi"]:
            nokpi[p["date"][5:7]][0] += 1
lines = [f'{MOIS_L[int(m) - 1].capitalize()} : {k} sur {t} sans KPI' for m, (k, t) in sorted(nokpi.items()) if k]
vig.append(("Posts publiés sans KPI saisis", ("; ".join(lines) + ". Ils ne figurent pas dans cette page.") if lines else "Tous les posts publiés ont leurs KPI saisis."))
low = [r for r in rows if r["impr"] <= 1]
bad = sorted([r for r in rows if r.get("eng_saisi") is not None and abs(r["eng_saisi"] * 100 - r["eng"]) > 0.5], key=lambda r: -abs(r["eng_saisi"] * 100 - r["eng"]))
dup = defaultdict(int)
for r in rows:
    if r.get("url"):
        dup[r["url"]] += 1
nd = sum(v for v in dup.values() if v > 1)
txt = []
if low:
    txt.append(f"{len(low)} post(s) à 1 impression ou moins, exclus des formats et des FLOP : " + ", ".join(short(r["nom"], 40) for r in low[:4]) + ".")
if bad:
    txt.append(f"{len(bad)} taux d'engagement saisis dans Notion s'écartent du taux recalculé (plus de 0,5 point), par ex. " + " ; ".join(f'{short(r["nom"], 35)} ({pct(r["eng_saisi"] * 100)} saisi, {pct(r["eng"])} recalculé)' for r in bad[:3]) + ". Cette page recalcule toujours le taux à partir des compteurs.")
if nd:
    txt.append(f"{nd} posts partagent un lien LinkedIn déjà utilisé par un autre post.")
vig.append(("Valeurs à vérifier dans Notion", " ".join(txt) if txt else "Aucune anomalie détectée."))
vig.append(("Abonnés", "Dernier relevé par page : " + ", ".join(f"{p} {ddmm(SUB_D1[p])}" for p, _, _ in SUBS) + f". Premier relevé retenu : {ddmm(BASE)}."))
vig += [tuple(v) for v in REF["vig_static"]]
vig_html = "".join(f'<div class="card"><h3>{esc(h)}</h3><p>{esc(t)}</p></div>' for h, t in vig)

NOTE_LOW = f"{len(low)} post(s) à 1 impression ou moins exclus (valeurs à vérifier dans Notion)." if low else "Aucun post à 1 impression exclu."
FLOP_LOW = (f", hors {len(low)} post(s) à 1 impression ou moins (valeurs à vérifier)" if low else "")
ST_LAB = {"Publié": "publiés", "Annulé": "annulés", "Non traitée": "non traités"}
_pm = defaultdict(lambda: defaultdict(int))
for p in DATA["posts_all"]:
    _pm[p["date"][5:7]][p["statut"]] += 1
NOTE_MO = "Toutes pages, posts planifiés dans Notion : " + " ; ".join(
    f'{MOIS_L[int(m) - 1]} ' + ", ".join(f"{c} {ST_LAB[s]}" for s, c in sorted(v.items(), key=lambda kv: -kv[1]) if s in ST_LAB) for m, v in sorted(_pm.items())) + "."
_dm = [SUB_D1[p] for p in P5 if p in SUB_D1]
_main = max(set(_dm), key=_dm.count)
SUBNOTE = ddmm(_main) + "".join(f" ; {p} {ddmm(SUB_D1[p])}" for p in P5 if p in SUB_D1 and SUB_D1[p] != _main)

CSS = """
:root{--navy:#002F6B;--blue:#76BAD8;--tint:#E8F2F8;--bg:#fff;--ink:#0b2447;--mute:#5a6b82;--line:#d6e1ec;--card:#f4f8fb;--link:#00539f}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;color-scheme:light}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 Calibri,Carlito,"Segoe UI",system-ui,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px}
.band{background:var(--bg);color:var(--ink);padding:48px 0;min-height:100vh;min-height:100svh;display:flex;flex-direction:column;justify-content:center;scroll-snap-align:start;scroll-snap-stop:always}
.band>.wrap{width:100%}
html{scroll-snap-type:y mandatory;scroll-behavior:smooth}
@media(max-width:820px),(max-height:640px){html{scroll-snap-type:y proximity}.band{scroll-snap-stop:normal}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
.band.grey{--bg:#EDF0F4;--card:#fff;--line:#d2dae4;--mute:#56667c}
.band.dark{--bg:#002F6B;--ink:#fff;--mute:#b6c8de;--navy:#fff;--blue:#76BAD8;--card:rgba(255,255,255,.1);--line:rgba(255,255,255,.24);--link:#a9daf0}
.dots{position:fixed;right:14px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:10px;z-index:10}
.dots button{width:12px;height:12px;border-radius:50%;border:2px solid #002F6B;background:#fff;padding:0;cursor:pointer;box-shadow:0 0 0 2px rgba(255,255,255,.7)}
.dots button.on{background:#002F6B;transform:scale(1.25)}
.dots button:focus-visible{outline:3px solid #76BAD8;outline-offset:3px}
@media(max-width:560px){.dots{right:6px;gap:8px}.dots button{width:9px;height:9px}}
header{padding:30px 0 8px}
.logo{display:block;height:46px;width:auto;fill:var(--navy);margin-bottom:22px}
.eyebrow{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--mute);font-weight:700}
h1{font-size:clamp(30px,5vw,46px);line-height:1.1;margin:6px 0 8px;color:var(--navy);font-weight:700}
.sub{color:var(--mute);margin:0}
h2{font-size:24px;color:var(--navy);margin:0 0 4px}
h2 small{display:block;font-size:14px;font-weight:400;color:var(--mute);margin-top:2px}
h3{margin:0 0 6px;font-size:17px;color:var(--navy)}
.hrow{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:10px 20px;margin-bottom:6px}
.flt{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--mute);margin-right:30px}
.flt select{font:inherit;font-size:15px;color:#002F6B;background:#fff;border:1px solid var(--line);border-radius:8px;padding:7px 30px 7px 10px;min-width:190px;cursor:pointer}
.flt select:focus-visible{outline:3px solid var(--blue);outline-offset:2px}
.var{display:none}.var.on{display:block}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:24px 0 36px}
.tiles.t3{margin:16px 0 8px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.tile{background:var(--card);border-radius:14px;padding:18px 18px 16px;border:1px solid var(--line)}
.tile b{display:block;font-size:30px;line-height:1.1;color:var(--navy);font-variant-numeric:tabular-nums}
.tiles.t3 .tile b{font-size:24px}
.tile span{color:var(--mute);font-size:14px}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px;align-items:start;margin-top:8px}
.grid2>div{min-width:0}
@media(max-width:820px){.grid2{grid-template-columns:minmax(0,1fr)}}
.bars{margin:14px 0}
.bar{display:grid;grid-template-columns:130px 1fr 78px;align-items:center;gap:10px;margin:7px 0;font-size:15px}
.bar .lbl{text-align:right;color:var(--ink)}
.bar .track{background:var(--card);border-radius:6px;height:22px;overflow:hidden;display:block}
.bar .fill{display:block;height:100%;background:var(--blue);border-radius:6px}
.bar .fill.hi{background:var(--navy)}
.bar .val{font-weight:700;color:var(--navy);font-variant-numeric:tabular-nums}
@media(max-width:520px){.bar{grid-template-columns:96px 1fr 64px;font-size:14px}}
.scroll{overflow-x:auto;margin:10px 0;border-radius:10px;border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:15px;min-width:520px}
th{background:var(--navy);color:var(--bg);text-align:left;padding:9px 12px;font-weight:700;white-space:nowrap}
td{padding:8px 12px;border-top:1px solid var(--line);white-space:nowrap}
table.fit{min-width:0;font-size:14px}
table.fit th,table.fit td{padding:8px 7px;white-space:normal}
table.fit td:first-child{min-width:70px}
@media(max-width:520px){table.fit{font-size:12.5px}table.fit th,table.fit td{padding:7px 4px}}
tbody tr:nth-child(even){background:var(--card)}
.num{text-align:right;font-variant-numeric:tabular-nums}
a{color:var(--link)}
.cols{display:grid;grid-template-columns:repeat(10,minmax(0,1fr));gap:8px;align-items:end;height:260px;margin:18px 0 6px;padding-top:6px}
.col{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%}
.cv{font-size:12px;font-weight:700;color:var(--navy);margin-bottom:4px;font-variant-numeric:tabular-nums}
.cb{width:100%;background:var(--blue);border-radius:6px 6px 0 0;display:block}
.cb.hi{background:var(--navy)}.cb.empty{height:0}
.cl{font-size:13px;color:var(--mute);margin-top:6px}
@media(max-width:560px){.cv{font-size:9px;white-space:nowrap}.cl{font-size:10px}.cols{gap:3px}}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin-top:14px}
.cards.c3{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.card{background:var(--card);border-radius:14px;padding:14px 16px;border:1px solid var(--line)}
.card.ok{border-left:4px solid var(--blue)}
.card h3{font-size:16px}
.card p{margin:0;font-size:14.5px}
.note{color:var(--mute);font-size:14px;margin:8px 0 0}
.msg{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:14px 0 0}
.slider{margin-top:16px}
.track2{display:flex;gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;padding:2px 2px 12px;scrollbar-width:thin}
.slide{flex:0 0 min(440px,86%);scroll-snap-align:start;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 18px 16px;position:relative;display:flex;flex-direction:column}
.slide h3{padding-right:44px;margin-bottom:2px}
.rk{position:absolute;top:14px;right:14px;width:32px;height:32px;border-radius:50%;background:var(--navy);color:var(--bg);display:flex;align-items:center;justify-content:center;font-weight:700}
.meta{margin:0 0 12px;color:var(--mute);font-size:14px}
.kp{display:grid;grid-template-columns:repeat(3,1fr);gap:8px 10px;margin-bottom:12px}
.kp b{display:block;font-size:18px;color:var(--navy);font-variant-numeric:tabular-nums}
.kp span{font-size:12px;color:var(--mute)}
.vis{font-size:13px;color:var(--mute);margin:0 0 8px}
.txt{border-top:1px solid var(--line);padding-top:10px;max-height:250px;overflow:auto;font-size:14.5px}
.txt p{margin:0 0 8px}
.txt .none{color:var(--mute);font-style:italic}
.ctrl{display:flex;align-items:center;justify-content:center;gap:14px;margin-top:4px}
.ctrl button{width:40px;height:40px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--navy);font-size:24px;line-height:1;cursor:pointer}
.ctrl button:hover{background:var(--navy);color:var(--bg)}
.cnt{min-width:56px;text-align:center;color:var(--mute);font-variant-numeric:tabular-nums}
.sec-h{font-size:18px;color:var(--navy);margin:18px 0 0}
footer{color:var(--mute);font-size:13px;padding:22px 0 0}
"""

JS = r"""<script>
document.querySelectorAll('.slider').forEach(function(s){var t=s.querySelector('.track2'),c=s.querySelector('.cnt'),k=t.children,N=k.length;
function step(){return k[0].getBoundingClientRect().width+14}
function upd(){var i=Math.min(N-1,Math.round(t.scrollLeft/step()));c.textContent=(i+1)+' / '+N}
s.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){t.scrollBy({left:step()*(+b.dataset.d),behavior:'smooth'})})});
t.addEventListener('scroll',upd,{passive:true});});
document.querySelectorAll('select[data-grp]').forEach(function(sel){sel.addEventListener('change',function(){
  document.querySelectorAll('.var[data-grp="'+sel.dataset.grp+'"]').forEach(function(v){var on=v.dataset.v===sel.value;v.classList.toggle('on',on);
    if(on){v.querySelectorAll('.track2').forEach(function(t){t.scrollLeft=0});v.querySelectorAll('.cnt').forEach(function(c){c.textContent='1 / '+(c.closest('.slider').querySelector('.track2').children.length)})}})})});
(function(){var secs=[].slice.call(document.querySelectorAll('.band')),nav=document.querySelector('.dots'),names=['Accueil','Abonnés','Publications','Formats','Rythme mensuel','TOP 10','FLOP 10','2025-2026 : abonnés','2025-2026 : portée et rythme','2025-2026 : engagement','2025-2026 : écarts','Vigilance'];
secs.forEach(function(s,i){var b=document.createElement('button');b.type='button';b.title=names[i]||('Section '+(i+1));b.setAttribute('aria-label',b.title);b.addEventListener('click',function(){s.scrollIntoView({behavior:'smooth',block:'start'})});nav.appendChild(b)});
var bs=nav.children;function mark(){var y=window.innerHeight/2,k=0;secs.forEach(function(s,i){var r=s.getBoundingClientRect();if(r.top<=y)k=i});[].forEach.call(bs,function(b,i){b.classList.toggle('on',i===k)})}
window.addEventListener('scroll',mark,{passive:true});window.addEventListener('resize',mark);mark();
document.addEventListener('keydown',function(e){if(e.target.closest&&(e.target.closest('.track2')||e.target.tagName==='SELECT'))return;var k=e.key;if(k==='ArrowDown'||k==='PageDown'||k==='ArrowUp'||k==='PageUp'){var y=window.innerHeight/2,c=0;secs.forEach(function(s,i){if(s.getBoundingClientRect().top<=y)c=i});var d=(k==='ArrowDown'||k==='PageDown')?1:-1,t=secs[Math.max(0,Math.min(secs.length-1,c+d))];e.preventDefault();t.scrollIntoView({behavior:'smooth',block:'start'})}});
})();
(function(){
if(window.matchMedia&&matchMedia('(prefers-reduced-motion:reduce)').matches)return;
var DUR=1100,ease=function(t){return 1-Math.pow(1-t,3)};
var RX=/^([+−-]?)(\d[\d\s  ]*(?:,\d+)?)(.*)$/;
function parse(el){var t=el.textContent.trim(),m=RX.exec(t);if(!m||/\d/.test(m[3]))return null;
 var raw=m[2],dm=/,(\d+)$/.exec(raw),d=dm?dm[1].length:0,v=parseFloat(raw.replace(/[\s  ]/g,'').replace(',','.'));
 return {p:m[1],v:v,d:d,s:m[3],sp:/[  ]/.test(raw)?' ':(/\s/.test(raw.trim())?' ':'')}}
function fmt(o,x){var a=x.toFixed(o.d).split('.'),i=a[0];if(o.sp)i=i.replace(/\B(?=(\d{3})+(?!\d))/g,o.sp);return o.p+i+(a[1]?','+a[1]:'')+o.s}
var items=[];
document.querySelectorAll('.fill').forEach(function(e){items.push({e:e,k:'w',v:e.style.width});e.style.width='0'});
document.querySelectorAll('.cb:not(.empty)').forEach(function(e){items.push({e:e,k:'h',v:e.style.height});e.style.height='0'});
document.querySelectorAll('.bar .fill,.cb').forEach(function(e){e.style.transition='width 1.1s cubic-bezier(.2,.7,.2,1),height 1.1s cubic-bezier(.2,.7,.2,1)'});
var nums=[];
document.querySelectorAll('.val,.cv,.tile b,.kp b,td.num,.cnt-up').forEach(function(e){var o=parse(e);if(o&&e.children.length===0){nums.push({e:e,o:o,t:e.textContent});}});
nums.forEach(function(n){n.e.textContent=fmt(n.o,0)});
function visible(e){return !e.closest('.var:not(.on)')}
var done=new WeakSet();
function play(root){
 items.forEach(function(i){if(root.contains(i.e)&&visible(i.e)){i.e.getBoundingClientRect();i.e.style[i.k==='w'?'width':'height']=i.v}});
 var t0=performance.now(),mine=nums.filter(function(n){return root.contains(n.e)&&visible(n.e)});
 function f(now){var p=Math.min(1,(now-t0)/DUR),k=ease(p);mine.forEach(function(n){n.e.textContent=p>=1?n.t:fmt(n.o,n.o.v*k)});if(p<1)requestAnimationFrame(f)}
 requestAnimationFrame(f)}
function reset(root){
 items.forEach(function(i){if(root.contains(i.e)){i.e.style[i.k==='w'?'width':'height']='0'}});
 nums.forEach(function(n){if(root.contains(n.e))n.e.textContent=fmt(n.o,0)})}
var io=new IntersectionObserver(function(es){es.forEach(function(en){if(en.isIntersecting&&en.intersectionRatio>=.35){if(!en.target._on){en.target._on=1;play(en.target)}}else if(!en.isIntersecting){if(en.target._on){en.target._on=0;reset(en.target)}}})},{threshold:[0,.35]});
document.querySelectorAll('.band').forEach(function(b){io.observe(b)});
document.querySelectorAll('select[data-grp]').forEach(function(sel){sel.addEventListener('change',function(){
 var v=document.querySelector('.var.on[data-grp="'+sel.dataset.grp+'"]');if(!v)return;reset(v);requestAnimationFrame(function(){requestAnimationFrame(function(){play(v)})})})});
})();
</script>"""

page = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<link rel="icon" type="image/png" href="data:image/png;base64,{FAV}">
<title>KPI LinkedIn 2026</title>
<style>{CSS}</style></head><body>
<nav class="dots" aria-label="Sections"></nav>
<div class="band"><div class="wrap"><header>{LOGO}<div class="eyebrow">ADENES France · Réseaux sociaux</div>
<h1>KPI LinkedIn 2026</h1>
<p class="sub">Publications du 1er janvier au 31 octobre 2026 · Source : Notion · Abonnés : dernier relevé avant le 31/10</p></header>

<div class="tiles">
<div class="tile"><b>{n(s1)}</b><span>abonnés sur 6 pages · +{n(s1 - s0)} (+{pct(g(s0, s1))}) entre le {ddmm(BASE)} et le {ddmm(LAST)}</span></div>
<div class="tile"><b>{len(rows)}</b><span>posts avec KPI saisis, sur {len(ALL)} publiés</span></div>
<div class="tile"><b>{n(T)}</b><span>impressions cumulées</span></div>
<div class="tile"><b>{pct(eng_w(rows))}</b><span>taux d'engagement global</span></div>
</div></div></div>

<section class="band grey"><div class="wrap">
<h2>Abonnés<small>Évolution entre le {ddmm(BASE)} et le dernier relevé ({ddmm(LAST)})</small></h2>
<div class="grid2"><div>{subs_tbl}</div><div>{subs_bars}</div></div>
</div></section>

<section class="band dark"><div class="wrap">
<h2>Publications<small>Impressions cumulées par page et détail des interactions</small></h2>
<div class="grid2"><div>{pages_bars}</div><div></div></div>
{pages_tbl}
<p class="note">Engagement = (clics + réactions + commentaires + repartages) ÷ impressions, cumulé par page. Posts avec KPI saisis uniquement.</p>
</div></section>

<section class="band grey"><div class="wrap">
<div class="hrow"><h2>Types de publication<small>Quels formats fonctionnent le mieux : carrousel, repartage, vidéo, image</small></h2>{picker("fmt")}</div>
{fmt_html}
<p class="note">{NOTE_LOW} Hors format texte et posts sans format renseigné.</p>
</div></section>

<section class="band dark"><div class="wrap">
<div class="hrow"><h2>Rythme mensuel<small>Impressions des posts avec KPI, par mois de publication</small></h2>{picker("mo")}</div>
{months_html}
<p class="note">{NOTE_MO}</p>
</div></section>

<section class="band grey"><div class="wrap">
<div class="hrow"><h2>TOP 10<small>Les posts les plus vus. Faites défiler ; le titre renvoie vers LinkedIn.</small></h2>{picker("top")}</div>
{top_html}
</div></section>

<section class="band dark"><div class="wrap">
<div class="hrow"><h2>FLOP 10<small>Les posts les moins vus{FLOP_LOW}</small></h2>{picker("flop")}</div>
{flop_html}
<p class="note">Textes issus de Notion lorsqu'ils y sont renseignés. Les visuels ne sont pas affichés : ils sont hébergés hors de Notion ou non accessibles.</p>
</div></section>

<section class="band grey"><div class="wrap">
<h2>2025 → 2026 : les abonnés<small>Comparaison avec le PowerPoint « KPIs LinkedIn 2025-2026 » (sept. 2026) · 5 pages : ELEX, ADENES France, ROADIA, 3C, VERING</small></h2>
{cmp_tiles_a}
<div class="grid2"><div>{cmp_subs_tbl}</div><div><h3>Croissance S1 2025 → {ddmm(LAST)}/2026</h3>{cmp_subs_bars}</div></div>
<p class="note">S1 2025, S2 2025 et S1 2026 (relevé de juillet) viennent du PowerPoint ; la dernière colonne est notre dernier relevé ({SUBNOTE}). ADENES ACADEMY et Adenes Monde ne figurent pas dans le PowerPoint.</p>
</div></section>

<section class="band dark"><div class="wrap">
<h2>2025 → 2026 : portée et rythme<small>S1 2025 et S2 2025 : PowerPoint · S1 2026 (janv.–juin) et {LAB2.lower()} 2026 : nos données Notion</small></h2>
<div class="grid2"><div>{cmp_tot_tbl}</div><div>{cmp_page_tbl}</div></div>
<div class="msg">{esc(cmp_msg_b)}</div>
<p class="note">Notre S1 2026 couvre janvier à juin (6 mois) : il reprend les chiffres du PowerPoint et y ajoute les posts de fin juin. Les mois sans KPI saisis sont exclus. Les volumes de publications sont ceux de Notion (statut Publié) ; le PowerPoint les compte autrement (voir page suivante).</p>
</div></section>

<section class="band grey"><div class="wrap">
<h2>2025 → 2026 : engagement<small>Ce que nos chiffres confirment</small></h2>
<div class="grid2"><div>{cmp_rea_tbl}<p class="note">Réactions pour 1 000 impressions : seule mesure d'engagement du PowerPoint pour 2025 (pas de clics), donc seul indicateur comparable d'une période à l'autre.</p></div><div>{cmp_eng_tbl}<p class="note">Le taux du PowerPoint est une moyenne des taux saisis ; le nôtre est recalculé à partir des compteurs.</p></div></div>
<div class="cards c3">{cf_html}</div>
</div></section>

<section class="band dark"><div class="wrap">
<h2>2025 → 2026 : écarts avec le PowerPoint<small>Points à corriger ou à aligner avant de réutiliser ce document</small></h2>
<div class="cards c3">{ec_html}</div>
</div></section>

<section class="band grey"><div class="wrap">
<h2>Points de vigilance</h2>
<div class="cards">{vig_html}</div>
<footer>Page confidentielle, non indexée. Mise à jour : @@UPDATED@@.</footer>
</div></section>
{JS}
</body></html>"""
open(OUT, "w", encoding="utf-8").write(page)
print("ok", len(page), "posts", len(rows))
