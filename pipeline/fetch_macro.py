#!/usr/bin/env python3
"""
fetch_macro.py — PIB nominal (US$) por país via API do Banco Mundial (grátis, sem chave).
Indicador NY.GDP.MKTP.CD. Lê iso3 de data/sources/countries.csv -> data/cache/macro.json.

Juros/desemprego/IDH continuam vindo do CSV (curadoria) nesta fase — o Banco Mundial
tem defasagem nesses indicadores e o Fed/BCs mudam a taxa com frequência.
Evolução: FRED (juros EUA), OECD e World Bank WDI para os demais.

Uso:  python pipeline/fetch_macro.py
Requer: pip install requests
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "countries.csv")
OUT = os.path.join(ROOT, "data", "cache", "macro.json")
WB = "https://api.worldbank.org/v2/country/{iso3}/indicator/NY.GDP.MKTP.CD?format=json&per_page=5&mrnev=1"


def main():
    try:
        import requests
    except ImportError:
        print("requests não instalado. Rode: pip install -r pipeline/requirements.txt")
        sys.exit(1)

    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    out = {}
    for r in rows:
        iso = r.get("iso3", "").strip()
        if not iso:
            continue
        try:
            data = requests.get(WB.format(iso3=iso), timeout=30).json()
            val = None
            if isinstance(data, list) and len(data) > 1 and data[1]:
                for rec in data[1]:
                    if rec.get("value"):
                        val = rec["value"]; year = rec["date"]; break
            if val:
                out[r["id"]] = {"gdp_b": round(val / 1e9, 1), "year": year, "iso3": iso}
                print(f"  {r['name']:<16} {iso}  ${out[r['id']]['gdp_b']:>9}B  ({year})")
            else:
                print(f"  {r['name']:<16} {iso}  (sem dado — mantém semente)")
        except Exception as e:
            print(f"  {r['name']:<16} {iso}  ERRO: {e}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {len(out)} países -> {OUT}")


if __name__ == "__main__":
    main()
