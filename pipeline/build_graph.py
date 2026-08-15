#!/usr/bin/env python3
"""
build_graph.py — monta o graph.json que o frontend consome.

Fonte de verdade = CSVs em data/sources/ (curadoria manual) + taxonomy.py (curvas/arquétipos).
Se existirem caches de API em data/cache/ (gerados pelos fetch_*.py), os valores atuais
(market cap, PIB, mcap) são sobrepostos por cima dos valores-semente dos CSVs.

Usa apenas a biblioteca padrão — roda sem instalar nada (modo offline por padrão).
"""
import csv, json, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources")
CACHE = os.path.join(ROOT, "data", "cache")
OUT = os.path.join(ROOT, "web", "data", "graph.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from taxonomy import CURVES, ARCH, MACRO_EDGES, YEARS


def read_csv(name):
    path = os.path.join(SRC, name)
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_cache(name):
    path = os.path.join(CACHE, name)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  aviso: cache {name} inválido ({e}) — ignorando")
    return {}


def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def build():
    sectors = [{"id": int(r["id"]), "name": r["name"], "color": r["color"]}
               for r in read_csv("sectors.csv")]

    eq_cache = load_cache("equities.json")
    cx_cache = load_cache("crypto.json")
    mac_cache = load_cache("macro.json")

    # ---------- PRIVADO ----------
    priv_nodes = []
    for r in read_csv("companies.csv"):
        cid = r["id"]
        val = num(r["seed_value_b"])
        if cid in eq_cache and eq_cache[cid].get("value_b"):
            val = round(eq_cache[cid]["value_b"])
        priv_nodes.append({
            "id": cid, "name": r["name"], "sector": int(r["sector"]),
            "type": r["type"], "value": val,
            "m": num(r["momentum"], 1.0), "p": int(num(r["potential"], 60)),
            "ticker": r.get("ticker", ""),
        })

    # ---------- PÚBLICO ----------
    pub_nodes = []
    for r in read_csv("countries.csv"):
        cid = r["id"]
        gdp = num(r["seed_gdp_b"])
        if cid in mac_cache and mac_cache[cid].get("gdp_b"):
            gdp = round(mac_cache[cid]["gdp_b"])
        pub_nodes.append({
            "id": cid, "name": r["name"], "iso3": r["iso3"],
            "cont": int(r["region_id"]), "bloco": int(r["bloco_id"]),
            "type": r["type"], "value": gdp,
            "juros": num(r["juros"]), "desemp": num(r["desemprego"]),
            "idh": num(r["idh"]), "gini": num(r["gini"]),
            "arch": r["arch"], "bank": r["bank"], "m": 1.0,
        })
    regions = _distinct(read_csv("countries.csv"), "region_id", "region_name")
    blocos = _distinct(read_csv("countries.csv"), "bloco_id", "bloco_name")

    # ---------- CRIPTO ----------
    cx_nodes = []
    cx_sectors = []
    for r in read_csv("crypto.csv"):
        cid = r["id"]
        mcap = num(r["seed_mcap_b"]); vol = num(r["vol_b"]); dom = num(r["dominance"])
        c = cx_cache.get(cid, {})
        if c.get("value_b"):
            mcap = round(c["value_b"], 2)
        if c.get("vol_b"):
            vol = round(c["vol_b"], 2)
        if c.get("dominance"):
            dom = round(c["dominance"], 2)
        cx_nodes.append({
            "id": cid, "name": r["name"], "sector": int(r["sector"]),
            "type": r["type"], "value": mcap, "vol": vol, "dom": dom,
            "coingecko_id": r.get("coingecko_id", ""), "m": 1.0,
        })
    cx_sectors = _distinct(read_csv("crypto.csv"), "sector", "sector_name")

    # ---------- RELAÇÕES / NOTÍCIAS ----------
    edges = {"privado": [], "publico": [], "cripto": []}
    for r in read_csv("relations.csv"):
        blk = r["block"]
        if blk not in edges:
            continue
        e = {"s": r["source"], "t": r["target"], "type": r["type"], "year": int(num(r["year"], 2021))}
        amt = r.get("amount_b", "").strip()
        e["amt"] = num(amt) if amt else None
        if r.get("label"):
            e["label"] = r["label"]
        edges[blk].append(e)

    news = {"privado": [], "publico": [], "cripto": []}
    if os.path.exists(os.path.join(SRC, "news.csv")):
        for r in read_csv("news.csv"):
            blk = r["block"]
            if blk in news:
                news[blk].append({"c": r["entity"], "d": r["date"], "hl": r["headline"], "k": r["kind"]})

    graph = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_note": "Valores de mercado/PIB via APIs quando o cache existe; caso contrário, valores-semente dos CSVs. Valuations privados, relações e notícias são curados manualmente.",
        "years": YEARS,
        "sectors": sectors,
        "arch": {k: {str(i): v for i, v in d.items()} for k, d in ARCH.items()},
        "macro_edges": MACRO_EDGES,
        "blocks": {
            "privado": {"curves": _curves("privado"), "nodes": priv_nodes, "edges": edges["privado"], "news": news["privado"]},
            "publico": {"curves": _curves("publico"), "regions": regions, "blocos": blocos, "nodes": pub_nodes, "edges": edges["publico"], "news": news["publico"]},
            "cripto":  {"curves": _curves("cripto"), "sectors": cx_sectors, "nodes": cx_nodes, "edges": edges["cripto"], "news": news["cripto"]},
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=1)

    enriched = []
    if eq_cache: enriched.append(f"{len(eq_cache)} ações")
    if cx_cache: enriched.append(f"{len(cx_cache)} cripto")
    if mac_cache: enriched.append(f"{len(mac_cache)} países")
    tag = ("enriquecido por API: " + ", ".join(enriched)) if enriched else "modo semente (sem cache de API)"
    print(f"OK graph.json escrito em {OUT}")
    print(f"   {len(priv_nodes)} empresas · {len(pub_nodes)} países · {len(cx_nodes)} cripto · {tag}")


def _curves(block):
    return {str(k): {str(y): v for y, v in yr.items()} for k, yr in CURVES[block].items()}


def _distinct(rows, id_key, name_key):
    seen = {}
    for r in rows:
        k = int(num(r[id_key]))
        if k not in seen:
            seen[k] = r[name_key]
    return [{"id": k, "name": seen[k]} for k in sorted(seen)]


if __name__ == "__main__":
    build()
