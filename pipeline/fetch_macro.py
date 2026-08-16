#!/usr/bin/env python3
"""
fetch_macro.py — PIB (World Bank) + JUROS reais (FRED / BCB), tudo sem chave de API.
- PIB nominal US$: World Bank NY.GDP.MKTP.CD (lote, fail-fast).
- Juros de política: FRED via fredgraph CSV (keyless) — Fed (FEDFUNDS) e BCE (ECBDFR, zona do euro);
  Selic do Brasil via API do BCB (série 432). Demais países: juros seguem curados no CSV.
Grava data/cache/macro.json com gdp_b e/ou juros por país. Desemprego/IDH seguem curados.
Uso:  python pipeline/fetch_macro.py    |   Requer: pip install requests
"""
import csv, json, os, sys, time

# país -> série FRED (taxa de política, %). BCE é a mesma taxa p/ toda a zona do euro.
FRED_RATES = {"eua":"FEDFUNDS","alemanha":"ECBDFR","franca":"ECBDFR","italia":"ECBDFR","espanha":"ECBDFR","holanda":"ECBDFR"}

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

    # ---- JUROS reais ----
    def fred_latest(series):
        try:
            r = sess.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series, timeout=20)
            if r.status_code != 200:
                return None
            for line in reversed(r.text.strip().splitlines()[1:]):
                parts = line.split(",")
                if len(parts) >= 2:
                    try:
                        return round(float(parts[1]), 2)
                    except ValueError:
                        continue
        except Exception:
            return None
        return None

    fred_cache = {}
    for cid, series in FRED_RATES.items():
        if cid not in iso_to_id.values():
            continue
        v = fred_cache.get(series)
        if v is None:
            v = fred_latest(series); fred_cache[series] = v
        if v is not None:
            out.setdefault(cid, {})["juros"] = v
            print(f"  juros {cid:<10} {series:<10} {v}%")

    # Selic (Brasil) via BCB (série 432 = meta Selic, % a.a.)
    try:
        r = sess.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json", timeout=20)
        if r.status_code == 200 and r.json():
            sel = round(float(r.json()[-1]["valor"]), 2)
            out.setdefault("brasil", {})["juros"] = sel
            print(f"  juros brasil     BCB-432    {sel}%")
    except Exception:
        pass

    for iso, name in iso_to_name.items():
        loc = iso_to_id[iso]
        e = out.get(loc, {})
        gdp = ("$%.0fB" % e["gdp_b"]) if e.get("gdp_b") else "PIB curado"
        jr = (" · juros %.2f%%" % e["juros"]) if e.get("juros") is not None else ""
        print(f"  {name:<16} {iso}  {gdp}{jr}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {len(out)} países c/ dado real -> {OUT}")


if __name__ == "__main__":
    main()
