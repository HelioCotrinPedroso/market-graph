# Terminal Macro do Ecossistema

Plataforma analítica em **grafo** para um canal de investidores em tecnologia — narrada ao vivo.
Três mundos que se conectam pela camada de **setor**:

- **Privado** — economia corporativa por setor (Tecnologia, Semicondutores, Energia, Financeiro, Saúde, Indústria & Defesa, Consumo, Commodities).
- **Público** — países: PIB, Fed/juros, emprego, IDH, comércio, compra de títulos e tensões; agrupável por continente ou bloco de poder (G7, UE, BRICS+, Golfo/OPEP…).
- **Cripto** — ativos digitais (L1, L2, DeFi, Stablecoins, RWA, Memecoins, IA-cripto).
- **Macro** — visão dos 3 blocos e os fluxos entre eles.
- **Setores** — grafo multicamada país → setor → empresa (a ponte entre público e privado).

Cada bolha = tamanho (valuation/PIB/market cap) · arestas = fluxo de capital/relações · timeline com replay 2021→2026 · lentes trocáveis · radar de notícias navegável.

> ⚠️ **Dados ilustrativos por padrão.** Rode o pipeline para substituir por números reais de mercado.

## Arquitetura

```
Fontes grátis (APIs)          Curadoria (CSV)              Frontend estático
────────────────────          ──────────────              ─────────────────
yfinance  → ações             companies/countries         web/index.html
CoinGecko → cripto      +     crypto/relations/news   →   carrega web/data/graph.json
World Bank → PIB              (data/sources/*.csv)        (sem backend, sem build)
        │                            │
        └────────► pipeline/build_graph.py ──► web/data/graph.json
```

Sem servidor e sem framework: o frontend é HTML+SVG+JS puro que consome um `graph.json`.
Se o `graph.json` não existir, ele cai para os dados embutidos (sempre funciona).

## Estrutura

```
data/sources/     CSVs editáveis à mão (fonte de verdade da curadoria)
  sectors.csv       taxonomia de 8 setores + cores
  companies.csv     empresas (ticker p/ públicas, valuation-semente p/ privadas)
  countries.csv     países: região, bloco, PIB, juros, desemprego, IDH, arquétipo, banco central
  crypto.csv        ativos + id do CoinGecko
  relations.csv     arestas (investimento, fornecimento, comércio, títulos, tensão…)
  news.csv          manchetes por entidade (radar de notícias)
data/cache/       saídas dos fetchers de API (regeráveis; fora do git)
pipeline/         taxonomy.py (curvas/arquétipos) + fetch_*.py + build_graph.py + run.py
web/              index.html (o terminal) + data/graph.json (gerado)
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r pipeline/requirements.txt
```

## Rodar

**Antes de cada live**, atualize os números e reconstrua o `graph.json`:

```bash
python pipeline/run.py                 # busca ações + cripto + PIB e reconstrói
python pipeline/run.py --offline       # só reconstrói dos CSVs (sem internet)
python pipeline/run.py --only crypto   # atualiza só uma fonte
```

Depois sirva o frontend (precisa ser via HTTP para o `fetch` do JSON funcionar):

```bash
python -m http.server 8000 --directory web
# abra http://localhost:8000
```

## Rodar com Docker

Sobe a plataforma num container (o `graph.json` é reconstruído no start):

```bash
docker compose up --build      # http://localhost:8000
```

Para atualizar com **dados reais** de mercado dentro do container (precisa de internet):

```bash
docker compose run --rm pipeline     # busca ações/cripto/PIB e regrava web/data/graph.json
docker compose up                    # sobe já com os dados atualizados
```

Sem docker-compose, direto no Docker:

```bash
docker build -t market-graph .
docker run --rm -p 8000:8000 market-graph
```

## Deploy (GitHub Pages) — dados sob demanda

O site é estático (`web/`) e vai para o **GitHub Pages** de graça. Os dados **não** são
atualizados em tempo real nem por agenda — você atualiza **quando quiser**.

**1. Criar o repositório e enviar** (uma vez):

```bash
cd D:\market-graph
git remote add origin https://github.com/<seu-usuario>/market-graph.git
git push -u origin main
```

**2. Ligar o Pages**: no GitHub, `Settings → Pages → Build and deployment → Source: GitHub Actions`.
No free, o Pages exige repositório **público** (privado só no GitHub Pro).

Pronto: a cada `push` na `main`, o workflow **Deploy** publica o site.
URL: `https://<seu-usuario>.github.io/market-graph/`.

**Atualizar os dados (sob demanda)** — duas formas, ambas manuais:

- **Pelo GitHub** (sem instalar nada): aba `Actions → Atualizar dados (sob demanda) → Run workflow`.
  Ele roda o pipeline, faz commit do `graph.json` novo e o site republica sozinho.
- **Localmente** (mais confiável p/ o Yahoo): `docker compose run --rm pipeline` e depois
  `git add web/data/graph.json && git commit -m "dados" && git push`.

### Outras opções de hospedagem

Qualquer host de site estático serve — conecte o repo e configure **Output/Publish directory = `web`**
(sem build). Ex.: Cloudflare Pages (aceita repo privado) ou Netlify. No caso da Vercel, o plano
grátis (Hobby) é apenas para uso **não-comercial**.

## Fontes de dados

| Bloco | Métrica | Fonte | Chave |
|---|---|---|---|
| Privado | market cap (ações) | yfinance (Yahoo) | não |
| Privado | valuation (privadas) | curadoria em `companies.csv` | — |
| Cripto | market cap / volume / dominância | CoinGecko | não |
| Público | PIB nominal | World Bank (NY.GDP.MKTP.CD) | não |
| Público | juros / desemprego / IDH | curadoria em `countries.csv` | — |

## Roteiro (próximos)

- Juros reais: FRED (EUA) + OECD/World Bank para os demais.
- Histórico ano a ano (yfinance/World Bank) para as curvas do replay virem de dados reais.
- Composição do PIB por setor com dados oficiais (hoje via arquétipos econômicos).
- M&A / rodadas automatizadas (imprensa + SEC filings) para as arestas.
- Deploy contínuo (GitHub Actions roda o pipeline + publica no GitHub Pages/Vercel).

## Aviso

Projeto pessoal para conteúdo. Não é recomendação de investimento. Valores privados e
relações são estimativas curadas; os automatizados dependem da disponibilidade das APIs.
