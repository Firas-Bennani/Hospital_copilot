# PROGRESS — Hospital Copilot

Branche de travail : `feat/platform`. Reprendre à la première phase non cochée.

- [x] 0 — Dépôt créé depuis le code d'Amal, `master` poussé
- [x] A — Audit et refactor sûr (docs/EXISTING.md, app/, tests de non-régression, contracts/, .env.example, docker-compose.yml, README.md)
- [x] B — Données et auth (modèles SQLModel, SQLite, seed, JWT + rôles, login.html, navigation filtrée)
- [x] C — Ingestion et simulateur (MQTT + repli HTTP, bus, room_state, simulateur + VitalDB + scénarios, page Machines)
- [ ] D — Extensions 3D (room-live.js, poses, infirmiers, équipements, moniteurs réels, couleur de risque, KPI)
- [ ] E — Agents (6 agents, NEWS2, LLM + Mock, panneau Agents, centres détection/commande, FollowUp, Telegram)
- [ ] F — Documents (patients, historique, rapport médecin, ordonnance, rapport de garde, impression)
- [ ] G — Edge (edge/ complet, posture_map, zones, thermique, capteurs, actionneurs, règles locales, --fake, systemd, tests)
- [ ] H — Démo (bouton « Lancer la démo », scénario bout en bout, docs/demo.md, scripts/run-demo.*)
- [ ] FIN — MORNING_REPORT.md, test d'intégration fall_demo → nurse_resolves, DONE.flag

## Journal
- 2026-10-10 05:40 — Étape 0 terminée (clone, commit initial, push master). Début phase A.
- 2026-10-10 06:05 — Phase A terminée : app/ (config, ws, bus, state, api/demo, contracts, main), 42 tests dashboard + 13 tests CV verts, serveur HTTP 200, contrats + schémas, .env.example, docker-compose, README, docs/EXISTING.md.
- 2026-10-10 06:40 — Phase B terminée : models.py (28 tables), db.py, seed.py (4 patients, 4 chambres, 32 appareils, 25 médicaments, 6 utilisateurs, 2 anciennes admissions), auth JWT cookie + 17 permissions, api/auth + api/users, login.html, nav.js/Views (vues par-dessus le canvas), api.js, auth.js, platform.css, onglets Agents/Journal, hook `hackcure:ws` dans app.js. 55 tests verts.
- 2026-10-10 07:30 — Phase C terminée : ingest/handler.py (validation, room_state, projection 3D, persistance échantillonnée, bus, WS coalescé), POST /api/ingest (lots), client MQTT optionnel (aiomqtt, repli auto), simulator/ (engine, 8 scénarios YAML, vitaldb_replay avec repli synthétique, sim.py HTTP/MQTT), simulateur embarqué (app/sim/embedded.py), API devices/rooms/scenario, vue « Paramètres des machines » (Chart.js). 62 tests dashboard + 11 simulateur verts.
