# 🏠 Observatoire des Prix Immobiliers — Maroc  (MUBAWAB  + AGENZ.MA )
## Indice Hédonique des Prix Résidentiels à partir de données web(AYA BERRADY)

> Projet de data engineering et statistiques officielles expérimentales  
> Méthodologie: IMF RPPI Handbook · Eurostat HPPI Guide · OECD

---

## Architecture du projet

```
rppi_maroc/(AYA BERRADY)
├── config/
│   └── settings.py          ← configuration centrale (URLs, paramètres, phases)
├── ingestion/
│   ├── pipeline.py           ← orchestrateur Phase 3
│   └── scrapers/
│       ├── base_scraper.py   ← classe abstraite
│       └── mubawab_scraper.py ← source confirmée
        ├──agenz_scraper.py
├── processing/
│   └── cleaner.py            ← Phase 5: ETL + qualité des données
├── database/
│   └── models.py             ← 4 tables: raw, clean, price_index, logs
├── analytics/
│   ├── eda/
│   │   └── exploratory.py    ← Phase 6: analyse exploratoire
│   ├── hedonic/
│   │   └── model.py          ← Phase 7-8: modèle hédonique semi-log OLS
│   ├── index/
│   │   └── rppi.py           ← Phase 9: construction de l'indice
│   ├── spatial/              ← Phase 10: analyse spatiale
│   ├── validation/           ← Phase 11: validation
│   └── bias/                 ← Phase 12: biais
├── dashboard/
│   └── app.py                ← Phase 14: Streamlit dashboard
├── utils/
│   ├── helpers.py
│   └── logger.py
├── data/
│   ├── raw/                  ← snapshots CSV bruts
│   ├── clean/                ← données nettoyées
│   ├── exports/              ← RPPI, EDA, modèles
│   └── snapshots/            ← versioning historique
├── docs/                     ← documentation par phase
├── main.py                   ← runner principal
├── setup_mac.sh              ← installation Mac en 1 clic
└── requirements.txt
```

---

## Installation (AYA BERRADY)

```bash
# Cloner / extraire le projet
cd rppi_maroc

# Setup automatique (crée venv, installe, initialise DB)
chmod +x setup_mac.sh
./setup_mac.sh

# Activer l'environnement
source venv/bin/activate
```

---

## Exécution (AYA BERRADY)

```bash
# Phase 3 — Collecte des données (~20 min, 5 villes × 15 pages) (MUBAWAB  + AGENZ.MA )
python main.py --ingest { ingest for both mubawab(1) , agenz(2) OR ,ingest  source -- (1)/(2)

# Phase 5 — Nettoyage et enrichissement
python main.py --clean

# Phase 6 — Analyse exploratoire
python main.py --ed
# Phase 7-9 — Modèle hédonique + RPPI
python main.py --hedonic

# Phase 9 — Calcul de l'indice
python main.py --index

# Phase 14 — Dashboard (http://localhost:8501)
python main.py --dashboard

# Pipeline complet
python main.py
```

---

## Modèle hédonique (Phase 7-9)(AYA BERRADY)

**Formule semi-log OLS** (IMF RPPI Handbook):

```
ln(P_it) = α + β·X_it + Σγ_t·D_t + ε_it
```

Où:
- `P_it` = prix de l'annonce i à la période t
- `X_it` = surface, pièces, type, ville
- `D_t` = indicatrices temporelles (base = 2024-Q1)
- `γ_t` → **RPPI_t = 100 × exp(γ_t)**

---

## Sources de données

| Source | Méthode | Statut |
|--------|---------|--------|
| Mubawab.ma | requests + BeautifulSoup | ✅ Confirmé |

---

## Villes couvertes

Casablanca · Rabat · Marrakech · Tanger · Fès

---

## Indicateurs produits

- RPPI national (base 100 = 2024-Q1)
- RPPI par ville (Casablanca, Rabat)
- RPPI location vs vente
- Prix moyen / médian par m²
- Dashboard temps réel

---

## Références méthodologiques

- IMF (2013). *Handbook on Residential Property Price Indices*
- Eurostat (2013). *Handbook on Residential Property Price Indices*
- OECD (2020). *Residential Property Price Indicators*
- UNECE (2019). *Guidelines on Web Scraping for Official Statistics*
