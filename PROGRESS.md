# PROGRESS — Hospital Copilot

Branche de travail : `feat/platform`. Reprendre à la première phase non cochée.

- [x] 0 — Dépôt créé depuis le code d'Amal, `master` poussé
- [x] A — Audit et refactor sûr (docs/EXISTING.md, app/, tests de non-régression, contracts/, .env.example, docker-compose.yml, README.md)
- [ ] B — Données et auth (modèles SQLModel, SQLite, seed, JWT + rôles, login.html, navigation filtrée)
- [ ] C — Ingestion et simulateur (MQTT + repli HTTP, bus, room_state, simulateur + VitalDB + scénarios, page Machines)
- [ ] D — Extensions 3D (room-live.js, poses, infirmiers, équipements, moniteurs réels, couleur de risque, KPI)
- [ ] E — Agents (6 agents, NEWS2, LLM + Mock, panneau Agents, centres détection/commande, FollowUp, Telegram)
- [ ] F — Documents (patients, historique, rapport médecin, ordonnance, rapport de garde, impression)
- [ ] G — Edge (edge/ complet, posture_map, zones, thermique, capteurs, actionneurs, règles locales, --fake, systemd, tests)
- [ ] H — Démo (bouton « Lancer la démo », scénario bout en bout, docs/demo.md, scripts/run-demo.*)
- [ ] FIN — MORNING_REPORT.md, test d'intégration fall_demo → nurse_resolves, DONE.flag

## Journal
- 2026-10-10 05:40 — Étape 0 terminée (clone, commit initial, push master). Début phase A.
- 2026-10-10 06:05 — Phase A terminée : app/ (config, ws, bus, state, api/demo, contracts, main), 42 tests dashboard + 13 tests CV verts, serveur HTTP 200, contrats + schémas, .env.example, docker-compose, README, docs/EXISTING.md.
