# KPI-LinkedIn

Page KPI LinkedIn chiffrée (`index.html`), régénérée chaque jour depuis Notion par GitHub Actions.

- `scripts/sync.py` : lit les bases Notion « Social Media Posts » et « Abonnés », génère la page, la chiffre.
- `scripts/site.py` : mise en page et calculs. `scripts/protect.py` : chiffrement AES-256-GCM.
- `scripts/reference.enc` : chiffres 2025 du PowerPoint et textes de référence, chiffrés avec le mot de passe de la page.
- `.github/workflows/sync.yml` : exécution quotidienne (et manuelle).

Secrets GitHub requis : `NOTION_TOKEN` (intégration Notion partagée avec les deux bases) et `KPI_PASSWORD`.
