# PROGRESS V2 — Hospital Copilot

Branche de travail : `feat/v2` (créée depuis `feat/platform`, qui reste la version de démo sûre).
Reprendre à la première étape non cochée. Ordre de priorité : 0 → 1 → 6 → 3 → 2 → 4 → 7 → 8 → 5, étape 9 au fil de l'eau, puis 10.

- [x] 0 — Intégrer les derniers travaux d'Amal (re-jouable, voir `AMAL_SYNC.md`)
- [ ] 1 — Corrections : environnement (commande → 3D) et résolution de tous les scénarios
- [ ] 2 — Bouton « Dossier médical » (5 à 15 ans d'historique)
- [ ] 3 — Fièvre vraie ≠ simple hausse de température (FeverAgent, `fever-pathway`)
- [ ] 4 — Diagnostics live, ordonnance de traitement, plan d'administration, rappels
- [ ] 5 — Ambulance en temps réel (GPS) + chambre réservée
- [ ] 6 — SpO2 de premier plan (oxymètre, règles, `desaturation_103`)
- [ ] 7 — Psychologie : rôle `psychiatrist`, questionnaires, PsychAgent
- [ ] 8 — PredictionAgent (bouton « Prédictions »)
- [ ] 9 — Tous les agents dans n8n (au fil de l'eau)
- [ ] 10 — Finition et démo V2 (`full_demo_v2`, docs, `DONE_V2.flag`)

## Journal
- 2026-10-10 18:45 — Étape 0 : `amal/master` a4fa849 intégré. `floors.js` repris tel quel (étage 1 : Radiologie, Dialyse, Pharmacie, Équipements ; RDC / Étage 1 / Tout / Éclaté ; salle isolée ; visite à pied) ; `scene.js` fusionné à la main (1 conflit dans `animate()` : les deux lignes gardées) ; `avatars.js`, `patient-state.js` appliqués sans conflit ; changements de `server.py` portés dans `app/` (champs `risk_level`, `risk_score`, `behavior_indicators`, `recommendations`, événement `behavioral_risk`, remise à zéro par `recover`, propagation `room_state.behavior` → VisionAgent → RiskAgent) ; panneau capteurs branché sur `room_state.env`. 98 tests dashboard verts, captures `docs/screenshots/v2/00…05`.
