#!/usr/bin/env python3
"""
fetch_crypto.py — market cap / volume / dominância via CoinGecko (grátis, sem chave).
Lê os coingecko_id de data/sources/crypto.csv e grava data/cache/crypto.json.

Uso:  python pipeline/fetch_crypto.py
Requer: pip install requests
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "crypto.csv")
OUT = os.path.join(ROOT, "data", "cache", "crypto.json")
API = "https://api.coingecko.com/api/v3/coins/markets"


def main():
    try:
        import requests
    except ImportError:
        print("requests não instalado. Rode: pip install -r pipeline/requirements.txt")
        sys.exit(1)

    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    ids = [r["coingecko_id"] for r in rows if r.get("coingecko_id")]
    by_cg = {r["coingecko_id"]: r["id"] for r in rows if r.get("coingecko_id")}

    # dominância total de mercado (para converter mcap -> %)
    total_mcap = None
    try:
        g = requests.get("https://api.coingecko.com/api/v3/global", timeout=30).json()
        total_mcap = g["data"]["total_market_cap"]["usd"]
    except Exception as e:
        print(f"  aviso: global mcap indisponível ({e}) — dominância mantém semente")

    out = {}
    try:
        params = {"vs_currency": "usd", "ids": ",".join(ids), "per_page": 250, "page": 1}
        data = requests.get(API, params=params, timeout=40).json()
        for c in data:
            local = by_cg.get(c["id"])
            if not local:
                continue
            mc = c.get("market_cap") or 0
            entry = {"value_b": round(mc / 1e9, 2), "vol_b": round((c.get("total_volume") or 0) / 1e9, 2)}
            if total_mcap:
                entry["dominance"] = round(mc / total_mcap * 100, 2)
            out[local] = entry
            print(f"  {c['id']:<16} ${entry['value_b']:>8}B  vol ${entry['vol_b']}B")
    except Exception as e:
        print(f"ERRO ao consultar CoinGecko: {e}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {len(out)} ativos -> {OUT}")


if __name__ == "__main__":
    main()
