# PROGRESS V3 — conformité au cahier des charges HackCure

Branche `feat/v2`. Point de retour : tag `v2-pre-conformite` (et `v2-stable`). Tests sans crédit d'API : `LLM_PROVIDER=mock`, `N8N_ENABLED=false`.
Relire ce fichier au début de chaque session ; reprendre à la première étape non cochée. Pas de nouvelle étape après 06h00.

- [ ] 1 — Docker : environnement conteneurisé autonome
- [ ] 2 — Pseudonymisation (Privacy by Design)
- [ ] 3 — Chiffrement en transit (TLS 1.3) et au repos (AES-256-GCM), non-répudiation
- [ ] 4 — Interopérabilité HL7 FHIR R4
- [ ] 5 — Intégrité des trames IoT (séquence, horodatage, HMAC-SHA256)
- [ ] 6 — SADM : confiance, explication, humain dans la boucle, 3 étapes maximum
- [ ] 7 — Documents pour le jury
- [ ] 8 — Vérification finale

Organisation (demande de 02h05) : étapes 4, 5 et 7 confiées à des sous-agents en parallèle (arbres de travail isolés), intégrées une par une ;
étapes 1, 2, 6 puis 3 par l'agent principal.

## Journal
- 2026-10-11 02:40 — Étape 1 : `Dockerfile` (Python 3.11 slim, utilisateur non-root, HEALTHCHECK `/health` par `dashboard/healthcheck.py`), `docker-compose.yml` (plateforme, Mosquitto, profils `n8n` et `mssql`, volumes, `.env` de l'hôte, redémarrage automatique), `scripts/run-docker.ps1` / `.sh`, section README. **Non exécuté** : le démon Docker de cette machine ne répond pas (erreur 500 du moteur) ; validé par `docker compose config` et par des tests de structure. Voir `BLOCKERS.md`.
