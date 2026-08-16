@echo off
REM Atualizar dados REAIS com 1 clique (roda no seu PC, publica sozinho).
REM Puxa: acoes (yfinance) + cripto (CoinGecko) + juros Fed/BCE (FRED) + Selic (BCB).
cd /d %~dp0
echo.
echo [1/3] Instalando dependencias (demora so na primeira vez)...
python -m pip install -q -r pipeline\requirements.txt
echo.
echo [2/3] Buscando dados reais e montando o graph.json...
python pipeline\run.py
echo.
echo [3/3] Publicando no GitHub (o site republica em ~1 min)...
git add web\data\graph.json
git commit -m "chore(data): atualizacao sob demanda" || echo (nada mudou, sem commit)
git push
echo.
echo Pronto!  Site: https://heliocotrinpedroso.github.io/market-graph/
pause
