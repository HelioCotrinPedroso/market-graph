#!/usr/bin/env python3
"""
fetch_equities.py — market cap atual das empresas públicas via yfinance (grátis, sem chave).
Lê os tickers de data/sources/companies.csv e grava data/cache/equities.json.
Empresas privadas (sem ticker) são ignoradas — seu valuation vem do CSV (curadoria).

Uso:  python pipeline/fetch_equities.py
Requer: pip install yfinance   (ver requirements.txt)
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "companies.csv")
OUT = os.path.join(ROOT, "data", "cache", "equities.json")


def main():
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance não instalado. Rode: pip install -r pipeline/requirements.txt")
        sys.exit(1)

    rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8")) if r.get("ticker")]
    out = {}
    for r in rows:
        tk = r["ticker"].strip()
        if not tk:
            continue
        try:
            info = yf.Ticker(tk).info
            mc = info.get("marketCap")
            if mc:
                out[r["id"]] = {
                    "value_b": round(mc / 1e9, 1),
                    "price": info.get("currentPrice"),
                    "name": info.get("shortName") or r["name"],
                    "ticker": tk,
                }
                print(f"  {r['name']:<18} {tk:<10} ${out[r['id']]['value_b']:>8}B")
            else:
                print(f"  {r['name']:<18} {tk:<10} (sem marketCap — mantém semente)")
        except Exception as e:
            print(f"  {r['name']:<18} {tk:<10} ERRO: {e}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {len(out)} ações -> {OUT}")


if __name__ == "__main__":
    main()
