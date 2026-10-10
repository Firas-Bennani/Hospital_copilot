# PROGRESS V2 — Hospital Copilot

Branche de travail : `feat/v2` (créée depuis `feat/platform`, qui reste la version de démo sûre).
Reprendre à la première étape non cochée. Ordre de priorité : 0 → 1 → 6 → 3 → 2 → 4 → 7 → 8 → 5, étape 9 au fil de l'eau, puis 10.

- [x] 0 — Intégrer les derniers travaux d'Amal (re-jouable, voir `AMAL_SYNC.md`)
- [x] 1 — Corrections : environnement (commande → 3D) et résolution de tous les scénarios
- [ ] 2 — Bouton « Dossier médical » (5 à 15 ans d'historique)
- [ ] 3 — Fièvre vraie ≠ simple hausse de température (FeverAgent, `fever-pathway`)
- [ ] 4 — Diagnostics live, ordonnance de traitement, plan d'administration, rappels
- [ ] 5 — Ambulance en temps réel (GPS) + chambre réservée
- [x] 6 — SpO2 de premier plan (oxymètre, règles, `desaturation_103`)
- [ ] 7 — Psychologie : rôle `psychiatrist`, questionnaires, PsychAgent
- [ ] 8 — PredictionAgent (bouton « Prédictions »)
- [ ] 9 — Tous les agents dans n8n (au fil de l'eau)
- [ ] 10 — Finition et démo V2 (`full_demo_v2`, docs, `DONE_V2.flag`)

## Journal
- 2026-10-10 18:45 — Étape 0 : `amal/master` a4fa849 intégré. `floors.js` repris tel quel (étage 1 : Radiologie, Dialyse, Pharmacie, Équipements ; RDC / Étage 1 / Tout / Éclaté ; salle isolée ; visite à pied) ; `scene.js` fusionné à la main (1 conflit dans `animate()` : les deux lignes gardées) ; `avatars.js`, `patient-state.js` appliqués sans conflit ; changements de `server.py` portés dans `app/` (champs `risk_level`, `risk_score`, `behavior_indicators`, `recommendations`, événement `behavioral_risk`, remise à zéro par `recover`, propagation `room_state.behavior` → VisionAgent → RiskAgent) ; panneau capteurs branché sur `room_state.env`. 98 tests dashboard verts, captures `docs/screenshots/v2/00…05`.
- 2026-10-10 19:15 — Étape 1 : (a) fenêtre réellement animée dans les 4 chambres (deux battants, vitre fixe masquée à l'ouverture, châssis ajouté en 103/104, courant d'air), radiateur / clim / veilleuse inchangés et vérifiés ; chaque commande (humain, agent, n8n) est tracée dans le journal des agents. (b) Un risque clinique ne se lève plus jamais seul : la normalisation d'un signal est notée, le risque attend la boucle soignant ; seuls les risques d'ambiance se clôturent automatiquement. (c) 11 scénarios `*_resolves.yaml` (chute, lever, fièvre, sepsis / NEWS2, perfusion, constantes, désaturation, douleur / appel, transfusion, comportement) lancés automatiquement par « Je prends en charge » en simulation, avatar du bon rôle (infirmier, médecin de garde en blouse blanche), présence ≥ 45 s, rien de simulé si un edge réel parle. (d) Correctif d'un verrou SQLite (transaction ouverte pendant un `await` dans la déduplication du RiskAgent). 13 tests de résolution ; 156 tests verts. Captures `10…13`.
- 2026-10-10 19:30 — Étape 6 : `clinical/spo2.py` (standard : < 94 attention, < 90 élevé, < 88 ou chute de 4 points/min critique ; BPCO, cible 88–92 % : < 88 / < 85 / < 83), NEWS2 échelle 2 pour les patients BPCO, VitalsAgent gradué (aggravation transmise sans délai, sévérité relevée sans doublon), revérification sur la cible du patient. Oxymètre de pouls déjà présent dans les 4 chambres (vérifié par test) ; SpO2 ajoutée au bandeau KPI (« SpO2 la plus basse ») et à la liste des patients, déjà présente sur la page Machines (valeur + courbe), le moniteur 3D et son étiquette. Scénario `desaturation_103` + `desaturation_resolves`. 7 tests ; captures `20…23`.
