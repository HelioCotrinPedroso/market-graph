#!/usr/bin/env python3
"""
fetch_macro.py — PIB nominal (US$) por país via API do Banco Mundial (grátis, sem chave).
Indicador NY.GDP.MKTP.CD. Faz UMA chamada em lote (todos os países), com retry — bem
mais robusto do que uma chamada por país. Lê iso3 de countries.csv -> data/cache/macro.json.

Juros/desemprego/IDH seguem vindo do CSV (curadoria) nesta fase.
Uso:  python pipeline/fetch_macro.py    |   Requer: pip install requests
"""
import csv, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "countries.csv")
OUT = os.path.join(ROOT, "data", "cache", "macro.json")


def main():
    try:
        import requests
    except ImportError:
        print("requests não instalado. Rode: pip install -r pipeline/requirements.txt")
        sys.exit(1)

    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    iso_to_id = {r["iso3"]: r["id"] for r in rows if r.get("iso3")}
    iso_to_name = {r["iso3"]: r["name"] for r in rows if r.get("iso3")}

    sess = requests.Session()
    sess.headers.update({"Accept": "application/json", "User-Agent": "market-graph/1.0"})

    def get_json(url, tries=2):
        # fail-fast: PIB é anual; se o World Bank não responder rápido, mantemos as sementes.
        for _ in range(tries):
            try:
                r = sess.get(url, timeout=12)
                if r.status_code == 200 and r.text.strip().startswith("["):
                    return r.json()
            except Exception:
                pass
            time.sleep(0.5)
        return None

    out = {}
    base = "https://api.worldbank.org/v2/country/{c}/indicator/NY.GDP.MKTP.CD?format=json&mrnev=1&per_page=1000"
    data = get_json(base.format(c=";".join(iso_to_id.keys())))
    if isinstance(data, list) and len(data) > 1 and data[1]:
        for rec in data[1]:
            iso = rec.get("countryiso3code")
            local = iso_to_id.get(iso)
            if local and rec.get("value"):
                out[local] = {"gdp_b": round(rec["value"] / 1e9, 1), "year": rec["date"], "iso3": iso}
    if not out:
        print("  Banco Mundial indisponível agora — PIB mantém as sementes curadas (dado anual).")

    for iso, name in iso_to_name.items():
        loc = iso_to_id[iso]
        if loc in out:
            print(f"  {name:<16} {iso}  ${out[loc]['gdp_b']:>9}B  ({out[loc]['year']})")
        else:
            print(f"  {name:<16} {iso}  (sem dado — mantém semente)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {len(out)} países -> {OUT}")


if __name__ == "__main__":
    main()
