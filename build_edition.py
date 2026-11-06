#!/usr/bin/env python3
"""Édition quotidienne : flux RSS réels -> data/AAAA-MM-JJ.json (+ data/index.json).
Rien n'est inventé : médias, liens et dates viennent des flux ; l'IA (optionnelle) ne peut citer que des ids fournis.
Usage : python scripts/build_edition.py [--check] [--no-llm]"""
import json, os, re, sys, html, datetime as dt, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = {"User-Agent": "Mozilla/5.0 (compatible; ActualiteVraiment/1.0)"}
SECTIONS = ["France", "International", "Géopolitique", "Économie", "Société", "Environnement et sciences"]
HOURS = 36
STOP = re.compile(r"people|célébrit|télé-réalité|buzz|football|ligue 1|tennis|rugby|horoscope|recette|soldes|bon plan|concours", re.I)

CHARTE = """Tu es rédacteur en chef d'un briefing quotidien en français, neutre, pluraliste et rigoureux.
Sélectionne 8 à 12 informations de réelle portée politique, économique, géopolitique, sociale, diplomatique, environnementale ou historique. Exclus people, faits divers sans portée, buzz, sport, contenus commerciaux, titres racoleurs. Privilégie l'importance, pas la popularité ; ne force aucune rubrique.
Fiabilité : le résumé (100 à 150 mots) ne contient que des faits présents dans les articles fournis. Aucune citation ni aucun chiffre absents des extraits. Le contexte et l'approfondissement peuvent s'appuyer sur des connaissances générales solidement établies ; ce qui est incertain, contesté ou non confirmé va dans « incertitudes » ou « controverses ». Distingue faits, analyses et hypothèses. Signale les divergences entre médias. Ne cite que des ids d'articles fournis, jamais d'URL. Ne suppose pas que le lecteur connaît le contexte.
Rubriques autorisées : SECTIONS_ICI.
Réponds UNIQUEMENT par un JSON de la forme : {"resume_jour":str,"items":[{"id":"s1","rubrique":str,"importance":1|2|3,"titre":str,"resume":str,"pourquoi":str,"contexte":str,"acteurs":[{"nom":str,"role":str}],"divergences":str,"sources":[ids],"approfondir":{"chronologie":[{"date":str,"texte":str}],"origines":str,"causes":{"immediates":[str],"structurelles":[str]},"acteurs_interets":[{"nom":str,"interet":str}],"rapports_de_force":str,"consequences":{"court_terme":[str],"long_terme":[str]},"controverses":[str],"incertitudes":[str],"lectures":[ids]}}],"a_surveiller":[{"quand":str,"quoi":str}],"glossaire":[{"terme":str,"definition":str}]}""".replace("SECTIONS_ICI", ", ".join(SECTIONS))


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return r.read()


def post(url, body, headers):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def txt(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def when(s):
    if not s: return None
    try: d = parsedate_to_datetime(s)
    except Exception:
        try: d = dt.datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception: return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def parse(raw, f):
    out = []
    for e in ET.fromstring(raw).iter():
        if e.tag.split("}")[-1] not in ("item", "entry"): continue
        v = {c.tag.split("}")[-1]: c for c in e}
        link = ((v["link"].get("href") or v["link"].text or "") if "link" in v else "").strip()
        d = next((when(v[k].text) for k in ("pubDate", "published", "updated", "date") if k in v and when(v[k].text)), None)
        title = txt(v["title"].text) if "title" in v else ""
        if not (title and d and link.startswith("http")): continue   # sans titre, date ou lien valide : écarté
        s = next((txt(v[k].text) for k in ("description", "summary", "encoded", "content") if k in v and v[k].text), "")
        out.append({"media": f["nom"], "acces": f["acces"], "hint": f.get("rubrique"), "titre": title, "url": link,
                    "date": d.astimezone(dt.timezone.utc).isoformat(timespec="minutes"), "extrait": s[:420]})
    return out


def collect(feeds):
    now, items, seen = dt.datetime.now(dt.timezone.utc), [], set()
    for f in feeds:
        try: got = parse(get(f["url"]), f)
        except Exception as ex:
            print(f"KO  {f['url']} : {ex}", file=sys.stderr); continue
        print(f"OK  {f['url']} : {len(got)} entrées")
        for i in got:
            if i["url"] in seen or (now - dt.datetime.fromisoformat(i["date"])).total_seconds() > HOURS * 3600: continue
            seen.add(i["url"]); i["id"] = f"a{len(items)}"; items.append(i)
    return items


def src(b): return {k: b[k] for k in ("media", "titre", "url", "date", "acces")}
def tokens(t): return set(re.findall(r"[a-zàâçéèêëîïôûùüœ]{4,}", t.lower()))
def close(a, b): return len(a["_t"] & b["_t"]) >= max(2, .4 * min(len(a["_t"]), len(b["_t"])))


def basic_edition(items):
    """Sans IA : revue de presse. Regroupe par recoupement entre médias ; aucune synthèse rédigée."""
    items = [i for i in items if not STOP.search(i["titre"])]
    for i in items: i["_t"] = tokens(i["titre"])
    rel = lambda a: [b for b in items if b is a or (b["media"] != a["media"] and close(a, b))]
    ranked = sorted(items, key=lambda a: (len({b["media"] for b in rel(a)}), a["date"]), reverse=True)
    out, used = [], []
    for a in ranked:
        if any(close(a, u) for u in used): continue
        r = rel(a); used += r
        out.append({"id": f"s{len(out)+1}", "rubrique": a["hint"] or "International", "titre": a["titre"],
                    "resume": a["extrait"], "sources": [src(b) for b in r[:4]]})
        if len(out) == 12: break
    return {"mode": "revue", "items": out}


def llm(system, user):
    if os.getenv("ANTHROPIC_API_KEY"):
        r = post("https://api.anthropic.com/v1/messages",
                 {"model": os.getenv("LLM_MODEL", "claude-sonnet-5-5"), "max_tokens": 16000, "system": system,
                  "messages": [{"role": "user", "content": user}]},
                 {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
        t = "".join(b.get("text", "") for b in r["content"])
    else:
        m = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                 {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"parts": [{"text": user}]}],
                  "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 32000}},
                 {"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        t = r["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(re.search(r"\{.*\}", t, re.S).group(0))


def llm_edition(items, byid):
    top = sorted(items, key=lambda i: i["date"], reverse=True)[:220]
    lines = "\n".join(f"{i['id']} | {i['media']} | {i['date'][:16]} | {i['titre']} | {i['extrait'][:200]}" for i in top)
    ed, good = llm(CHARTE, "Articles disponibles (id | média | date UTC | titre | extrait) :\n" + lines), []
    for it in ed.get("items", []):
        ids = list(dict.fromkeys(i for i in it.get("sources", []) if i in byid))   # ids inconnus = écartés
        if it.get("rubrique") not in SECTIONS or not it.get("titre") or not ids: continue
        it["sources"] = [src(byid[i]) for i in ids]
        a = it.setdefault("approfondir", {})
        a["lectures"] = [src(byid[i]) for i in dict.fromkeys(a.get("lectures", [])) if i in byid]
        good.append(it)
    return {"mode": "briefing", "resume_jour": ed.get("resume_jour", ""), "items": good[:12],
            "a_surveiller": ed.get("a_surveiller", []), "glossaire": ed.get("glossaire", [])}


def main():
    feeds = json.loads((ROOT / "scripts/feeds.json").read_text("utf-8"))
    items = collect(feeds)
    if "--check" in sys.argv: print(f"{len(items)} articles récents au total."); return
    if not items: sys.exit("Aucun article récupéré : aucune édition publiée (rien n'est inventé).")
    byid, ed = {i["id"]: i for i in items}, None
    if "--no-llm" not in sys.argv and (os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY")):
        try: ed = llm_edition(items, byid)
        except Exception as ex: print("IA indisponible, repli en revue de presse :", ex, file=sys.stderr)
    if not ed or not ed["items"]: ed = basic_edition(items)
    today = dt.datetime.now(ZoneInfo("Europe/Paris")).date().isoformat()
    ed.update({"date": today, "genere_le": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "articles_analyses": len(items)})
    DATA.mkdir(exist_ok=True)
    (DATA / f"{today}.json").write_text(json.dumps(ed, ensure_ascii=False, indent=1), "utf-8")
    days = sorted((p.stem for p in DATA.glob("20??-??-??.json")), reverse=True)
    idx = [{"date": d, "n": len(json.loads((DATA / f"{d}.json").read_text("utf-8"))["items"])} for d in days]
    (DATA / "index.json").write_text(json.dumps({"editions": idx}, ensure_ascii=False), "utf-8")
    print(f"Édition {today} : {len(ed['items'])} informations ({ed['mode']}).")


if __name__ == "__main__":
    main()
