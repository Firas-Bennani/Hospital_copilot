# DECISIONS — choix pris en autonomie

| Heure (2026-10-10) | Décision | Raison |
|---|---|---|
| 05:42 | Docker Desktop n'est pas démarré sur la machine : le développement et la démo utilisent le repli HTTP `POST /api/ingest`. `docker-compose.yml` (Mosquitto) est fourni et le client MQTT s'active automatiquement si un broker répond. | Règle « repli HTTP » du prompt ; la démo doit marcher sans broker. |
| 05:43 | Reconstruction de `computer_vision/src/datasets/harmonize.py` (fonctions `polygon_to_bbox`, `harmonize_label_line`) et ajout de `!computer_vision/src/datasets/` dans `.gitignore`. | Le `.gitignore` d'origine ignore `datasets/`, ce qui a exclu ce module du dépôt source : 4 tests existants échouaient à l'import. Les données `computer_vision/data/**` ne sont pas touchées. |
| 05:45 | Le simulateur est aussi **embarqué** dans le serveur (tâche asyncio, `EMBEDDED_SIM=1` par défaut) en plus du processus autonome `simulator/sim.py`. | Le bouton « Lancer la démo » doit fonctionner avec un seul processus, sans Pi, sans broker, sans clé LLM. |
| 05:45 | Venv créé avec le Python 3.13 d'Anaconda (seul interpréteur disponible ; pas de 3.11). | Compatibilité vérifiée avec FastAPI 0.143 / SQLModel 0.0.48. |
| 06:20 | Mots de passe hachés avec `bcrypt` directement (passlib reste installé mais inutilisé). | passlib 1.7 + bcrypt ≥ 4.1 émettent des erreurs d'incompatibilité ; moins de risque. |
| 06:25 | Tous les `datetime` stockés sont **timezone-aware (UTC)** (`models.utcnow()`). | SQLModel 0.0.48 refuse les datetimes naïfs. |
| 06:30 | Les patients gardent `display_name` = « Patient A..D » (étiquette 3D et `name` legacy) en plus d'un nom/prénom fictifs. | Le prompt impose les mêmes noms que `server.py` pour la non-régression ; la fiche patient affiche le nom complet. |
| 06:32 | Textes de `index.html` traduits en français (libellés uniquement, ids/classes inchangés). Les chaînes JS internes de `dashboard-ui.js` restent en anglais pour ne pas toucher au code existant. | Règle « textes en français » vs règle « ne pas réécrire l'existant ». |
| 06:35 | `GET /` redirige vers `/login` (302) si pas de cookie valide ; les endpoints legacy de démo restent ouverts. | Pas de « flash » du tableau de bord avant redirection ; compatible avec le prompt. |
