# BLOCKERS — points bloquants et solutions de repli

| Heure (2026-10-10) | Blocage | Repli appliqué |
|---|---|---|
| 05:42 | Démon Docker indisponible (Docker Desktop arrêté) → pas de Mosquitto local. | Repli HTTP `POST /api/ingest` + simulateur embarqué ; MQTT reste optionnel. |
