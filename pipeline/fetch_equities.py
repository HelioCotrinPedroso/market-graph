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

    def get_mc(tk, tries=4):
        t = yf.Ticker(tk)
        for i in range(tries):
            try:
                info = t.info
                if info and info.get("marketCap"):
                    return {"mc": info["marketCap"], "cur": info.get("currency"), "name": info.get("shortName"),
                            "dte": info.get("debtToEquity"), "td": info.get("totalDebt")}
            except Exception:
                pass
            # fallback: fast_info (market_cap direto, ou preço × ações)
            try:
                fi = t.fast_info
                mc = None
                try: mc = fi.get("market_cap")
                except Exception: mc = None
                if not mc:
                    try:
                        px = fi.get("last_price"); sh = fi.get("shares")
                        if px and sh: mc = px * sh
                    except Exception: pass
                if mc:
                    cur = None
                    try: cur = fi.get("currency")
                    except Exception: cur = None
                    return {"mc": mc, "cur": cur, "name": None}
            except Exception:
                pass
            time.sleep(1.0)
        return None

    rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8")) if r.get("ticker")]
    out = {}
    for r in rows:
        tk = r["ticker"].strip()
        if not tk:
            continue
        info = get_mc(tk)
        if not info:
            print(f"  {r['name']:<18} {tk:<11} (sem dado — mantém semente)")
            continue
        mc = info["mc"]
        usd = to_usd(mc, info.get("cur"))
        if usd is None or usd > MAX_USD_B * 1e9 or usd <= 0:
            print(f"  {r['name']:<18} {tk:<11} (moeda {info.get('cur')} não convertida — mantém semente)")
            continue
        vb = round(usd / 1e9, 1)
        # rede de segurança: desvio grosseiro vs semente curada = provável erro de dado/moeda
        seed = float(r.get("seed_value_b") or 0)
        if seed > 0 and (vb / seed > 3 or vb / seed < 0.33):
            print(f"  {r['name']:<18} {tk:<11} ${vb:>9}B  (fora de faixa vs semente {seed:.0f} — mantém semente)")
            continue
        rec = {"value_b": vb, "name": info.get("name") or r["name"], "ticker": tk, "currency": info.get("cur")}
        # alavancagem (dívida/patrimônio, %) e dívida total em USD B
        if info.get("dte") is not None:
            try: rec["d2e"] = round(float(info["dte"]), 1)
            except (TypeError, ValueError): pass
        if info.get("td"):
            td_usd = to_usd(info["td"], info.get("cur"))
            if td_usd and td_usd > 0:
                rec["debt_b"] = round(td_usd / 1e9, 1)
        out[r["id"]] = rec
        print(f"  {r['name']:<18} {tk:<11} ${vb:>9}B")
        time.sleep(0.15)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"OK {len(out)} ações -> {OUT}")


if __name__ == "__main__":
    main()
