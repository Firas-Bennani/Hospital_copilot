# PROGRESS — Hospital Copilot

Branche de travail : `feat/platform`. Reprendre à la première phase non cochée.

- [x] 0 — Dépôt créé depuis le code d'Amal, `master` poussé
- [x] A — Audit et refactor sûr (docs/EXISTING.md, app/, tests de non-régression, contracts/, .env.example, docker-compose.yml, README.md)
- [x] B — Données et auth (modèles SQLModel, SQLite, seed, JWT + rôles, login.html, navigation filtrée)
- [x] C — Ingestion et simulateur (MQTT + repli HTTP, bus, room_state, simulateur + VitalDB + scénarios, page Machines)
- [x] D — Extensions 3D (room-live.js, poses, infirmiers, équipements, moniteurs réels, couleur de risque, KPI)
- [x] E — Agents (6 agents, NEWS2, LLM + Mock, panneau Agents, centres détection/commande, FollowUp, Telegram)
- [x] F — Documents (patients, historique, rapport médecin, ordonnance, rapport de garde, impression)
- [ ] G — Edge (edge/ complet, posture_map, zones, thermique, capteurs, actionneurs, règles locales, --fake, systemd, tests)
- [ ] H — Démo (bouton « Lancer la démo », scénario bout en bout, docs/demo.md, scripts/run-demo.*)
- [ ] FIN — MORNING_REPORT.md, test d'intégration fall_demo → nurse_resolves, DONE.flag

## Journal
- 2026-10-10 05:40 — Étape 0 terminée (clone, commit initial, push master). Début phase A.
- 2026-10-10 06:05 — Phase A terminée : app/ (config, ws, bus, state, api/demo, contracts, main), 42 tests dashboard + 13 tests CV verts, serveur HTTP 200, contrats + schémas, .env.example, docker-compose, README, docs/EXISTING.md.
- 2026-10-10 06:40 — Phase B terminée : models.py (28 tables), db.py, seed.py (4 patients, 4 chambres, 32 appareils, 25 médicaments, 6 utilisateurs, 2 anciennes admissions), auth JWT cookie + 17 permissions, api/auth + api/users, login.html, nav.js/Views (vues par-dessus le canvas), api.js, auth.js, platform.css, onglets Agents/Journal, hook `hackcure:ws` dans app.js. 55 tests verts.
- 2026-10-10 07:30 — Phase C terminée : ingest/handler.py (validation, room_state, projection 3D, persistance échantillonnée, bus, WS coalescé), POST /api/ingest (lots), client MQTT optionnel (aiomqtt, repli auto), simulator/ (engine, 8 scénarios YAML, vitaldb_replay avec repli synthétique, sim.py HTTP/MQTT), simulateur embarqué (app/sim/embedded.py), API devices/rooms/scenario, vue « Paramètres des machines » (Chart.js). 62 tests dashboard + 11 simulateur verts.
- 2026-10-10 08:20 — Phase D terminée : scene.js (+setMonitorVitals, setRoomRiskColor, getRoomGroup, getRoomConfig — additif), avatars.js (+poses sitting_up/sitting_edge/standing/walking/sitting_chair/absent, icône d expression, halo thermique, badge WC/Hors chambre, marche animée), staff-avatars.js, equipment.js (fenêtre, radiateur, clim, veilleuse, étiquettes potence/moniteur), room-live.js, kpi-bar.js + /api/kpi, scripts/screenshot.py (Playwright). Captures dans docs/screenshots/, aucune erreur JS, boutons de démo existants vérifiés (04-legacy-fall-102.png).
- 2026-10-10 09:40 — Phase E terminée : clinical/news2.py (+tests), agents/ (base avec redémarrage, Vision, Vitals, Environment, Risk, FollowUp, Report, llm Mock/Anthropic, plans de secours, prompts FR), notify (in-app + Telegram), commands.py (MQTT → sim embarqué → virtuel), API risks/commands/agents/notifications/staff, panneau Agents, cloche, bouton « Lancer la démo », vues Détection / Commande / Personnel. 66 tests dashboard verts (dont boucle Vision→Risk→FollowUp).
- 2026-10-10 10:40 — Phase F terminée : API dossier patient (/api/records : CRUD, admission, sortie, historique), pharmacie (médicaments, traitements, alertes, conflits allergie), ordonnances (alerte allergie, signature forcée 409, impression), rapports médecin (brouillon IA, édition, signature), rapports de garde (génération IA, validation), pages /print/* (Jinja2 + print.css), caméra 101 (proxy MJPEG flouté optionnel, sinon schéma), vues Patients / Pharmacie / Historique / Rapport / Ordonnance / Rapport de garde / Caméras / Utilisateurs. 83 tests verts.
