#!/usr/bin/env python3
"""
fetch_news.py — notícias automáticas via GDELT DOC 2.0 (grátis, sem chave de API).

GDELT rate-limita chamadas rápidas e rejeita queries OR muito longas. Então:
consultamos UMA entidade por vez, com pausa, e só as entidades MAIS RELEVANTES
(maior valor em cada bloco) — que são as que interessam numa live. Casamos por
título (nome da entidade no título). Casamento é heurístico (pode ter ruído).

Uso:  python pipeline/fetch_news.py   |   Requer: pip install requests
"""
import csv, json, os, subprocess, time
from urllib.parse import urlencode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources")
OUT = os.path.join(ROOT, "data", "cache", "news.json")
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
PER_ENTITY = 2
SLEEP = 5.5                       # GDELT exige no MÁXIMO 1 requisição a cada 5s (senão HTTP 429)
TOPN = {"privado": 22, "publico": 12, "cripto": 8}   # ~42 entidades ⇒ ~4 min


def read_csv(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0


def kind_of(title):
    t = title.lower()
    if any(w in t for w in ("acqui", "merger", "buys", "acquire", "compra")): return "deal"
    if any(w in t for w in ("raises", "funding", "round", "invest")): return "funding"
    if any(w in t for w in ("launch", "unveil", "releases", "lança")): return "product"
    if any(w in t for w in ("rate", "inflation", "gdp", "central bank", "juros", "pib")): return "macro"
    return "news"


def main():
    def top(rows, val_col, block):
        rows = sorted(rows, key=lambda r: num(r.get(val_col)), reverse=True)[:TOPN[block]]
        return [(block, r["id"], r["name"]) for r in rows]

    ents = (top(read_csv("companies.csv"), "seed_value_b", "privado")
            + top(read_csv("countries.csv"), "seed_gdp_b", "publico")
            + top(read_csv("crypto.csv"), "seed_mcap_b", "cripto"))

    def fetch(name):
        # GDELT responde melhor via curl; query por entidade (o corpo do artigo casa com o termo).
        url = GDELT + "?" + urlencode({"query": '"%s"' % name, "mode": "artlist", "maxrecords": "8",
                                       "format": "json", "sort": "datedesc", "timespan": "3m"})
        try:
            txt = subprocess.run(["curl", "-s", "--max-time", "25", url],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout
            if txt and txt.strip().startswith("{"):
                return json.loads(txt).get("articles", []) or []
        except Exception:
            pass
        return []

    news = {"privado": [], "publico": [], "cripto": []}
    covered = 0
    for block, eid, name in ents:
        arts = fetch(name)
        picked, seen = 0, set()
        for a in arts:
            title = (a.get("title") or "").strip()
            # GDELT já filtrou pela entidade na query (relevância por corpo, não título) — não exigimos o nome no título
            if not title or title in seen:
                continue
            seen.add(title)
            d = a.get("seendate", "")
            date = ("%s-%s-%s" % (d[0:4], d[4:6], d[6:8])) if len(d) >= 8 else ""
            news[block].append({"c": eid, "d": date, "hl": title, "k": kind_of(title),
                                "src": a.get("domain", ""), "url": a.get("url", "")})
            picked += 1
            if picked >= PER_ENTITY:
                break
        if picked:
            covered += 1
        time.sleep(SLEEP)

    total = sum(len(v) for v in news.values())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(news, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {total} notícias · {covered}/{len(ents)} entidades cobertas -> {OUT}")


if __name__ == "__main__":
    main()
