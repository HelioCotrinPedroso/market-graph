#!/usr/bin/env python3
"""
serve.py — rodar a plataforma localmente com um comando.

  python serve.py            # reconstrói o graph.json (offline) e serve em :8000
  python serve.py --port 9000
  python serve.py --no-build # não reconstrói, só serve

Não precisa instalar nada (usa só a biblioteca padrão). Para dados REAIS de mercado,
rode antes: pip install -r pipeline/requirements.txt && python pipeline/run.py
"""
import argparse, functools, http.server, os, socketserver, subprocess, sys, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()

    if not args.no_build:
        print("Reconstruindo web/data/graph.json (modo offline)...")
        subprocess.call([sys.executable, os.path.join(HERE, "pipeline", "build_graph.py")])

    web = os.path.join(HERE, "web")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=web)
    socketserver.TCPServer.allow_reuse_address = True
    url = f"http://localhost:{args.port}"
    print(f"\nServindo {web}\n  {url}   (Ctrl+C para parar)\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    with socketserver.TCPServer(("", args.port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nParado.")


if __name__ == "__main__":
    main()
