# Rapport du matin — Hospital Copilot (HackCure)

Branche : `feat/platform` (dépôt `Firas-Bennani/Hospital_copilot`). `master` = code d'origine d'Amal intact.
Tout a été fait en autonomie dans la nuit du 10/10/2026 ; décisions dans `DECISIONS.md`, blocages dans `BLOCKERS.md`, avancement dans `PROGRESS.md`.

## 1. Lancer la plateforme (une seule commande)

```powershell
# Windows
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\run-demo.ps1 -Reset          # crée .venv si besoin, copie .env.example → .env, démarre http://localhost:8000
# option : .\scripts\run-demo.ps1 -Edge   → lance aussi un faux Raspberry Pi (edge --fake) pour la chambre 101
```
```bash
# Linux / macOS
./scripts/run-demo.sh --reset           # ./scripts/run-demo.sh 8000 --edge pour le faux Pi
```
À la main : `cd dashboard && ..\.venv\Scripts\uvicorn server:app --host 0.0.0.0 --port 8000` (le point d'entrée `server:app` est conservé).

Tests : `.venv\Scripts\python -m pytest dashboard/tests computer_vision/tests edge/tests simulator/tests -q`
(132 tests : 84 dashboard dont le test d'intégration `fall_demo → nurse_resolves`, 13 vision, 24 edge, 11 simulateur).

## 2. Identifiants (mot de passe commun `hackcure2026`, variable `DEMO_PASSWORD`)

| Identifiant | Rôle | Ce qu'il voit / fait |
|---|---|---|
| `owner` | Propriétaire | Tout + gestion des utilisateurs |
| `medecin` | Médecin généraliste | Tout : rapports, ordonnances (signer, imprimer), commandes |
| `medecin_garde` | Médecin de garde | Idem médecin ; destinataire des escalades |
| `infirmier` | Infirmier | 3D + commandes d'équipements, centre de commande (plans, « Marquer résolu »), rapport de garde, patients (modifier), documents en lecture |
| `receptionniste` | Réceptionniste | Patients (CRUD, admission/sortie), vues en lecture |
| `pharmacien` | Pharmacien | Pharmacie (CRUD médicaments, traitements) + jumeau 3D seulement |

## 3. Ce qui marche / est simulé / manque

**Fonctionne (vérifié par tests + captures Playwright dans `docs/screenshots/`)**
- Jumeau 3D d'origine intact (boutons de démo, Demo/Real, CCTV, zoom) + extensions additives : poses `sitting_up / sitting_edge / standing / walking / sitting_chair / absent (badge WC / Hors chambre)`, icône d'expression, halo thermique, avatar infirmier, fenêtre / radiateur / clim / veilleuse animés, étiquettes potence + moniteur avec **vraies constantes**, liseré de risque vert/orange/rouge/violet, bandeau KPI.
- Ingestion MQTT (aiomqtt, auto-reconnexion) **et** repli HTTP `POST /api/ingest`, validation JSON Schema (`contracts/`), `room_state` temps réel.
- Simulateur : chambres 102–104 + appareils des 4 chambres, 8 scénarios YAML, VitalDB (si réseau + paquet) sinon synthétique ; **embarqué** dans le serveur (zéro processus en plus) et autonome (`simulator/sim.py`).
- 6 agents (Vision, Vitals + NEWS2, Environment, Risk + plan LLM/mock, FollowUp, Report) : journal temps réel (📥 → 🧠 → ✅), dédup, escalades, résolution **vérifiée**, levée automatique des signaux transitoires.
- Notifications in-app (cloche + toasts) ; **Telegram** actif avec le `.env` déposé par l'équipe (vérifié : messages reçus `200 OK` pendant la démo `full_demo`).
- Auth JWT cookie, 6 rôles, permissions côté serveur + UI filtrée, audit de toute modification.
- Dossier patient, historique, pharmacie (stock/péremption/allergènes), ordonnance avec **alerte allergie**, rapport médecin (brouillon IA), rapport de garde IA (avec **humeur**), pages d'impression A4 (`/print/prescription/{id}`, `/print/report/{id}`, `/print/shift/{id}`).
- Edge Raspberry Pi complet avec simulation automatique de tout le matériel absent ; `--fake` testé de bout en bout sur PC (règles locales, alarme, commandes aller-retour via MQTT ou long-poll HTTP).

**Simulé / dégradé (par choix, voir DECISIONS.md)**
- LLM : le `.env` de l'équipe active `LLM_PROVIDER=anthropic` (`claude-sonnet-5-5`) — explications et plans rédigés par Claude, vérifiés en direct ; sans clé, `LLM_PROVIDER=mock` produit des textes à partir des vraies valeurs. Le SDK est chargé hors boucle et préchauffé (un blocage de ~55 s au premier risque a été corrigé dans la nuit).
- Pas de broker cette nuit (Docker Desktop arrêté) : tout a tourné en repli HTTP. `docker compose up -d` active Mosquitto sans autre changement.
- Poids YOLO absents du dépôt : l'edge bascule sur le modèle pose pré-entraîné (téléchargement Ultralytics) puis `--fake`. Le chemin « poids entraînés » (`CanonicalPipeline` → `computer_vision/src`) est codé mais n'a pas pu être exécuté sans les `.pt`.
- Caméra thermique, DHT22, GPIO : pilotes écrits, simulés ici (pas de Pi).
- Aperçu caméra 101 : proxy MJPEG flouté si `EDGE_CAMERA_URL` ; sinon vue schématique.

**Attention — `.env`** : le fichier `.env` présent à la racine (non commité) contient la clé Anthropic, le jeton Telegram et des variables `N8N_*` d'un autre module (ignorées ici). Ne pas le pousser sur GitHub.

**Manque / à faire si temps**
- Tests réels sur le Pi (voir §4), calibration du lit, FER+ (`python edge/download_ferplus.py`).
- SQL Server : supporté par `DATABASE_URL=mssql+pyodbc://…` mais non testé (pas de serveur dispo).
- Les chaînes internes de `dashboard-ui.js` (journal legacy) restent en anglais (fichier existant non réécrit).

## 4. Brancher le vrai Raspberry Pi 5 (chambre 101)

```bash
sudo apt install -y python3-venv libatlas-base-dev libcamera-apps i2c-tools   # + raspi-config : I2C on, caméra on
git clone https://github.com/Firas-Bennani/Hospital_copilot.git && cd Hospital_copilot && git checkout feat/platform
python3 -m venv .venv && .venv/bin/pip install -r edge/requirements.txt
python edge/download_ferplus.py                     # optionnel (expression)
nano edge/config/room101.yaml                       # server.url = http://<PC>:8000 ; mqtt.host = <PC> ou "" (HTTP seul)
.venv/bin/python edge/main.py --show                 # test avec fenêtre ; Ctrl+C
sudo cp edge/systemd/hackcure-edge.service /etc/systemd/system/ && sudo systemctl enable --now hackcure-edge
```
- **Calibration du lit / zones** : `python edge/calibrate_zones.py --source 0` → clic pour dessiner `bed`, `n` pour passer à `bathroom_door` puis `exit`, `s` pour sauver dans `room101.yaml`. Le point testé est le bas-centre de la boîte (ou les hanches avec un modèle pose), hystérésis 2 s.
- **Thermique** : MLX90640 sur I²C (SDA GPIO2, SCL GPIO3, 3,3 V). Calibration : `calibration_offset_c` dans le yaml ou `ThermalCamera.calibrate(ref)` ; `calibrated=false` tant que rien n'est réglé.
- **Câblage GPIO (BCM)** : DHT22 → GPIO4 ; bouton d'appel → GPIO22 (vers GND, pull-up interne) ; contact de porte → GPIO5 ; buzzer → GPIO17 ; veilleuse (LED/relais) → GPIO27 ; LED chauffage → GPIO23 ; LED clim → GPIO24 ; servo fenêtre → GPIO18 (PWM, alim 5 V séparée, masse commune).
- Côté serveur : rien à changer. Dès que l'edge parle (`source: edge-*`), la chambre 101 passe en vision réelle et le simulateur embarqué ne garde que les appareils. `EDGE_CAMERA_URL=http://<pi>:8080/stream` pour l'aperçu flouté.
- Sans broker : l'edge interroge `GET /api/edge/commands` ; avec Mosquitto : abonnement `hackcure/room/101/cmd/+`.

## 5. Script de démo de 3 minutes
Voir `docs/demo.md` (minuté). Résumé : zoom 101 → **Lancer la démo → full_demo** → lever (risque « lever non accompagné », veilleuse) → chute (chambre violette, VisionAgent → RiskAgent critical + plan, notifications) → centre de commande (plan coché) → infirmier entre (avatar, in_progress, StaffVisit) → sort → FollowUpAgent vérifie → résolu → fièvre (halo, VitalsAgent) → rapport de garde + impression → ordonnance avec alerte allergie.

## 6. Résumé de BLOCKERS.md
| Blocage | Repli |
|---|---|
| Docker Desktop arrêté → pas de Mosquitto | Repli HTTP + simulateur embarqué ; MQTT optionnel (`docker compose up -d`) |
| Poids YOLO absents du dépôt | Repli pose pré-entraîné puis `--fake` ; pipeline canonique codé mais non exécuté |
| Pas de Pi / capteurs / Telegram / clé Anthropic | Simulation automatique ; Telegram et Anthropic activés par variables d'environnement |
| `computer_vision/src/datasets/` absent du dépôt source (ignoré par `.gitignore`) | Module `harmonize.py` reconstruit (tests CV verts) ; données `computer_vision/data/**` intactes |
