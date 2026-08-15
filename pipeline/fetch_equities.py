#!/usr/bin/env python3
"""
fetch_equities.py — market cap atual das empresas públicas via yfinance (grátis, sem chave).
Lê os tickers de data/sources/companies.csv e grava data/cache/equities.json (em USD).

- Converte o market cap para USD quando a ação é listada em outra moeda (KRW, HKD, SAR, EUR...).
- Trata unidades menores (GBp/pence, ZAc). Faz retry e ignora valores implausíveis.
- Empresas privadas (sem ticker) são ignoradas — valuation vem do CSV (curadoria).

Uso:  python pipeline/fetch_equities.py
Requer: pip install yfinance
"""
import csv, json, os, sys, time, logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "companies.csv")
OUT = os.path.join(ROOT, "data", "cache", "equities.json")
MAX_USD_B = 15000  # nenhuma empresa vale > $15T; acima disso = erro de moeda -> descarta


def main():
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance não instalado. Rode: pip install -r pipeline/requirements.txt")
        sys.exit(1)
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    fx = {"USD": 1.0}

    def fx_rate(base):
        base = base.upper()
        if base in fx:
            return fx[base]
        px = None
        for pair, invert in ((f"{base}USD=X", False), (f"USD{base}=X", True)):
            try:
                t = yf.Ticker(pair)
                try:
                    px = t.fast_info.get("last_price") or t.fast_info.get("lastPrice")
                except Exception:
                    px = None
                if not px:
                    h = t.history(period="5d")
                    if len(h):
                        px = float(h["Close"].iloc[-1])
                if px:
                    fx[base] = (1.0 / px) if invert else float(px)
                    return fx[base]
            except Exception:
                continue
        fx[base] = None
        return None

    def to_usd(mc, cur):
        # yfinance reporta marketCap na moeda MAIOR mesmo quando o preço é em pence (GBp).
        # Então NÃO dividimos por 100: só mapeamos GBp->GBP, ZAc->ZAR para pegar o câmbio.
        raw = cur or "USD"
        base = {"GBp": "GBP", "GBX": "GBP", "ZAc": "ZAR"}.get(raw, raw.upper())
        r = fx_rate(base)
        if r is None:
            return None
        return mc * r

    def info_with_retry(tk, tries=3):
        for i in range(tries):
            try:
                info = yf.Ticker(tk).info
                if info and info.get("marketCap"):
                    return info
            except Exception:
                pass
            time.sleep(0.8)
        return None

    rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8")) if r.get("ticker")]
    out = {}
    for r in rows:
        tk = r["ticker"].strip()
        if not tk:
            continue
        info = info_with_retry(tk)
        if not info:
            print(f"  {r['name']:<18} {tk:<11} (sem dado — mantém semente)")
            continue
        mc = info["marketCap"]
        usd = to_usd(mc, info.get("currency"))
        if usd is None or usd > MAX_USD_B * 1e9 or usd <= 0:
            print(f"  {r['name']:<18} {tk:<11} (moeda {info.get('currency')} não convertida — mantém semente)")
            continue
        vb = round(usd / 1e9, 1)
        # rede de segurança: desvio grosseiro vs semente curada = provável erro de dado/moeda
        seed = float(r.get("seed_value_b") or 0)
        if seed > 0 and (vb / seed > 3 or vb / seed < 0.33):
            print(f"  {r['name']:<18} {tk:<11} ${vb:>9}B  (fora de faixa vs semente {seed:.0f} — mantém semente)")
            continue
        out[r["id"]] = {"value_b": vb, "name": info.get("shortName") or r["name"], "ticker": tk, "currency": info.get("currency")}
        print(f"  {r['name']:<18} {tk:<11} ${vb:>9}B")
        time.sleep(0.15)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {len(out)} ações -> {OUT}")


if __name__ == "__main__":
    main()
