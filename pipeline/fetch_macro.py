#!/usr/bin/env python3
"""
fetch_macro.py — macro de países 100% automatizado, sem chave de API.

World Bank (1 chamada em lote por indicador — sem estouro de requisição):
  PIB US$        NY.GDP.MKTP.CD    -> gdp_b
  População      SP.POP.TOTL       -> pop  (milhões)
  Dívida/PIB     GC.DOD.TOTL.GD.ZS -> dividaPib (% do PIB)
  Consumo/PIB    NE.CON.PRVT.ZS    -> consumo   (% do PIB)
  Desemprego     SL.UEM.TOTL.ZS    -> desemp    (%)
  Desigualdade   SI.POV.GINI       -> gini
Juros de política (FRED keyless via curl): Fed (FEDFUNDS), BCE (ECBDFR); Selic via BCB (série 432).

Usa `mrnev=1` (valor mais recente não-vazio) => tolera defasagem anual.
Grava data/cache/macro.json por país. Só IDH segue curado (World Bank não tem HDI).
Uso:  python pipeline/fetch_macro.py   |   Requer: pip install requests
"""
import csv, json, os, sys, time, subprocess

WB_INDICATORS = {
    "gdp_b":     ("NY.GDP.MKTP.CD",    1e9),   # -> bilhões de US$
    "pop":       ("SP.POP.TOTL",       1e6),   # -> milhões de pessoas
    "dividaPib": ("GC.DOD.TOTL.GD.ZS", 1.0),
    "consumo":   ("NE.CON.PRVT.ZS",    1.0),
    "desemp":    ("SL.UEM.TOTL.ZS",    1.0),
    "gini":      ("SI.POV.GINI",       1.0),
}
FRED_RATES = {"eua": "FEDFUNDS", "alemanha": "ECBDFR", "franca": "ECBDFR",
              "italia": "ECBDFR", "espanha": "ECBDFR", "holanda": "ECBDFR"}

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
    iso_set = set(iso_to_id.keys())

    sess = requests.Session()
    sess.headers.update({"User-Agent": "market-graph/1.0"})

    def wb(indicator, tries=3):
        # O World Bank bloqueia o cliente do `requests` (igual ao FRED) mas libera o curl.
        # Rota `country/all` + intervalo de datas é a única estável (o lote `;`+mrnev dá Request Error).
        url = ("https://api.worldbank.org/v2/country/all/indicator/{ind}"
               "?format=json&date=2018:2025&per_page=20000").format(ind=indicator)
        for _ in range(tries):
            try:
                txt = subprocess.run(["curl", "-s", "--max-time", "45", url],
                                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=55).stdout
                if txt and txt.strip().startswith("["):
                    j = json.loads(txt)
                    if isinstance(j, list) and len(j) > 1 and j[1]:
                        return j[1]
            except Exception:
                pass
            time.sleep(1.5)
        return None

    out = {}
    for field, (indicator, div) in WB_INDICATORS.items():
        recs = wb(indicator)
        if not recs:
            print(f"  [World Bank] {field:<10} indisponível agora — mantém semente")
            continue
        best = {}  # iso -> (ano, valor)  => pega o ano mais recente com valor
        for rec in recs:
            iso = rec.get("countryiso3code"); val = rec.get("value"); dt = rec.get("date") or ""
            if iso in iso_set and val is not None and (iso not in best or dt > best[iso][0]):
                best[iso] = (dt, val)
        for iso, (dt, val) in best.items():
            local = iso_to_id[iso]
            out.setdefault(local, {})[field] = round(val / div, 1)
            out[local].setdefault("_years", {})[field] = dt
        print(f"  [World Bank] {field:<10} {indicator:<18} {len(best)} países")

    # ---- JUROS reais (FRED via curl; BCB p/ Selic) ----
    def fred_latest(series):
        try:
            txt = subprocess.run(
                ["curl", "-s", "--max-time", "20",
                 "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25).stdout
            if not txt or "<html" in txt[:200].lower():
                return None
            for line in reversed(txt.strip().splitlines()[1:]):
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
            v = fred_latest(series)
            fred_cache[series] = v
        if v is not None:
            out.setdefault(cid, {})["juros"] = v

    try:
        r = sess.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json", timeout=20)
        if r.status_code == 200 and r.json():
            out.setdefault("brasil", {})["juros"] = round(float(r.json()[-1]["valor"]), 2)
    except Exception:
        pass

    covered = sum(1 for e in out.values() if e.get("gdp_b"))
    for iso, name in iso_to_name.items():
        e = out.get(iso_to_id[iso], {})
        bits = []
        if e.get("gdp_b"): bits.append("PIB $%.0fB" % e["gdp_b"])
        if e.get("pop"): bits.append("%.0fM hab" % e["pop"])
        if e.get("juros") is not None: bits.append("juros %.2f%%" % e["juros"])
        print(f"  {name:<16} {iso}  " + (" · ".join(bits) if bits else "sem dado (semente)"))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {len(out)} países no cache ({covered} com PIB real) -> {OUT}")


if __name__ == "__main__":
    main()
