#!/usr/bin/env python3
"""
run.py — orquestrador do pipeline.

  python pipeline/run.py            # busca todas as fontes e reconstrói o graph.json
  python pipeline/run.py --offline  # NÃO busca nada; reconstrói só a partir dos CSVs
  python pipeline/run.py --only crypto        # busca só cripto e reconstrói
  python pipeline/run.py --only equities,macro

Rode antes de cada live para atualizar os números. O graph.json final vai para web/data/.
"""
import argparse, subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
FETCHERS = {
    "equities": "fetch_equities.py",
    "crypto": "fetch_crypto.py",
    "macro": "fetch_macro.py",
    "news": "fetch_news.py",
}


def run(script):
    print(f"\n=== {script} ===")
    return subprocess.call([sys.executable, os.path.join(HERE, script)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="pula os fetchers de API")
    ap.add_argument("--only", default="", help="lista separada por vírgula: equities,crypto,macro")
    args = ap.parse_args()

    if not args.offline:
        targets = args.only.split(",") if args.only else list(FETCHERS)
        for t in targets:
            t = t.strip()
            if t in FETCHERS:
                run(FETCHERS[t])
            elif t:
                print(f"aviso: fonte desconhecida '{t}'")
    else:
        print("modo offline — reconstruindo a partir dos CSVs (sem chamadas de API)")

    print("\n=== build_graph.py ===")
    run("build_graph.py")


if __name__ == "__main__":
    main()
