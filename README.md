# Hospital Copilot — HackCure

Plateforme de supervision de clinique autour d'un **jumeau numérique 3D** (Three.js), d'une **chambre réelle instrumentée**
(Raspberry Pi 5 + vision), d'**appareils médicaux simulés** et de **6 agents IA** (aide à la décision validée par un humain).

> Données patients fictives. Les suggestions IA sont une aide à la décision : un soignant valide toujours.

## Démarrage rapide (un seul processus, sans Pi, sans broker, sans clé LLM)

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
cd dashboard
..\.venv\Scripts\uvicorn server:app --host 0.0.0.0 --port 8000
```
```bash
# Linux / macOS
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
cd dashboard && ../.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
```
Ouvrir <http://localhost:8000> → page de connexion. Comptes de démo (mot de passe `hackcure2026`, voir `.env.example`) :
`owner`, `medecin`, `medecin_garde`, `infirmier`, `receptionniste`, `pharmacien`.

Le simulateur embarqué alimente les appareils des 4 chambres et les chambres virtuelles 102–104 ; le bouton
**« Lancer la démo »** joue les scénarios (`fall_demo`, `nurse_resolves`, `fever_101`, …).

## Options
| Besoin | Commande |
|---|---|
| Broker MQTT (Mosquitto) | `docker compose up -d` — le serveur s'y connecte automatiquement, sinon repli HTTP `POST /api/ingest` |
| SQL Server | `docker compose --profile mssql up -d` + `DATABASE_URL=mssql+pyodbc://...` dans `.env` (`pip install pyodbc`) |
| LLM réel | `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY=...` (modèle `LLM_MODEL`, défaut `claude-sonnet-5-5`) |
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` |
| Simulateur autonome | `python simulator/sim.py --server http://localhost:8000 --scenario normal_night --speed 5` |
| Edge Raspberry Pi | `python edge/main.py --fake --server http://localhost:8000` (PC) ; voir `MORNING_REPORT.md` pour le vrai Pi |
| Webcam PC → 3D | `python dashboard/camera_loop.py --source 0` (poids YOLO requis) |

## n8n (orchestration réelle)
`npx n8n`, puis `.\n8n\import.ps1` (ou `./n8n/import.sh`) : crée les credentials et active les 4 workflows (`risk-triage`, `risk-verify`,
`shift-report`, `pharmacy-alerts`). La plateforme leur délègue la réponse aux risques et reprend la main seule si n8n est arrêté.
Voir `n8n/README.md`.

## Tests
```bash
.venv/Scripts/python -m pytest dashboard/tests computer_vision/tests edge/tests simulator/tests -q
```

## Structure
Voir `PROMPT.md` (spécification complète), `docs/EXISTING.md` (audit de l'existant), `contracts/mqtt-topics.md`
(contrats de messages), `PROGRESS.md`, `DECISIONS.md`, `BLOCKERS.md`.
