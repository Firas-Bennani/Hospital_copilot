# AMAL_SYNC — suivi de l'intégration du dépôt d'Amal

Dépôt source : `https://github.com/amalmch/hackcure_project` (branche `master`, remote git `amal`).
Notre dépôt a été créé à partir de son commit `7c4322d` (historiques sans lien commun).

| Date | Base | Dernier commit intégré | Commits repris |
|---|---|---|---|
| 2026-10-10 18:45 | `7c4322d` | **`a4fa849`** | `a4fa849` « Update 3D hospital dashboard and multi-floor navigation » |

**Dernier commit d'Amal intégré : `a4fa849`** — c'est la base de la prochaine synchronisation.

## Procédure (re-jouable)

```bash
git remote add amal https://github.com/amalmch/hackcure_project.git   # si absent
git fetch amal master
BASE=a4fa849                                   # dernier commit intégré (ligne ci-dessus)
git log --oneline $BASE..amal/master           # ce qu'il y a de nouveau ; rien ⇒ terminé
# 1) fichiers JS : application à trois voies, conflits résolus à la main en gardant les deux apports
git diff $BASE amal/master -- dashboard/static/js > /tmp/amal.patch && git apply -3 /tmp/amal.patch
# 2) fichiers que nous avons restructurés : lire le diff et le porter à la main
git diff $BASE amal/master -- dashboard/server.py dashboard/static/index.html dashboard/static/css
# 3) le reste (hors données) : git diff $BASE amal/master --stat -- . ':(exclude)computer_vision/data'
```
Puis : `node --check` sur chaque JS, `pytest`, captures `scripts/shots_v2.py` (RDC, Étage 1, éclaté, salle isolée, visite à pied), mise à jour du tableau ci-dessus.

## Où vont ses changements chez nous

| Fichier d'Amal | Chez nous |
|---|---|
| `dashboard/static/js/floors.js` | repris **tel quel** ; chargé après `app.js` ; initialisé par `scene.js` (`HospitalFloors.init`) |
| `scene.js`, `avatars.js`, `patient-state.js` | fusion à trois voies avec nos ajouts (liseré de risque, poses, moniteurs) |
| `dashboard/server.py` | porté dans `dashboard/app/state.py` (`process_event`) et `dashboard/app/api/demo.py` (`DemoEvent`, `/api/demo/trigger`, `/api/yolo/event`) |
| `index.html` (panneau capteurs) | `#sensor-panel` + `static/js/sensor-panel.js`, alimenté par `room_state.env` |

## Écarts volontaires
- `/api/yolo/event` garde `source="yolo"` (Amal : `ai_pipeline`) : notre ingestion et nos tests distinguent `yolo` / `simulation`.
- Le message WebSocket `behavior` n'est émis que pour `behavioral_risk` ; les autres événements gardent exactement les messages d'origine (non-régression).
- Le panneau « Étages & salles » de `floors.js` est remonté au-dessus du bandeau KPI et masqué quand une vue HTML est ouverte (règles dans `platform.css`, `floors.js` non modifié).
