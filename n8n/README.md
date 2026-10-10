# n8n — orchestration de la réponse aux risques

**Principe.** La plateforme **détecte** (règles déterministes, NEWS2, chute = critical, alarme locale du Pi).
n8n **orchestre la réponse** : plan d'action rédigé par Claude, alerte Telegram, attente d'acquittement, escalade,
re-vérification après le passage de l'infirmier, rapport de garde, alertes pharmacie.
Si n8n est arrêté, la plateforme continue seule avec ses agents Python (repli automatique, affiché dans l'interface).

```
plateforme ──POST /webhook/<nom> + X-Hospital-Secret──▶ n8n ──x-api-key──▶ api.anthropic.com
     ▲                                                   │──────────────▶ Telegram
     └──────── Authorization: Bearer <jeton de service> ─┘  (plan, escalade, résolution, journal)
```

## 1. Démarrage

```powershell
npx n8n                      # interface sur http://localhost:5678 (ou : docker run -it --rm -p 5678:5678 n8nio/n8n)
```
Créer le compte propriétaire à la première ouverture, puis **Settings → n8n API → Create an API key**.

Variables dans `.env` (jamais commité ; modèle dans `.env.example`) :

| Variable | Rôle |
|---|---|
| `N8N_ENABLED=true` | active l'envoi des événements vers n8n |
| `N8N_BASE_URL=http://localhost:5678` | adresse de n8n |
| `N8N_WEBHOOK_SECRET` | secret partagé : la plateforme l'envoie dans `X-Hospital-Secret`, les webhooks n8n le vérifient |
| `PLATFORM_URL=http://localhost:8000` | adresse de la plateforme vue depuis n8n |
| `PLATFORM_SERVICE_TOKEN` | jeton de service : n8n appelle l'API de la plateforme avec le rôle `owner` |
| `N8N_API_KEY` | clé de l'API publique de n8n, utilisée seulement par le script d'import |
| `ANTHROPIC_API_KEY`, `LLM_MODEL` | clé et modèle utilisés par les nœuds HTTP Anthropic |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | bot et conversation destinataires |

## 2. Import (credentials + workflows + activation)

```powershell
.\n8n\import.ps1                 # Windows   (.\n8n\import.ps1 -Check pour vérifier l'état)
```
```bash
./n8n/import.sh                  # Linux / macOS   (./n8n/import.sh --check)
```
Le script (`n8n/setup_n8n.py`, API publique de n8n) est **rejouable** : il crée ou met à jour les 4 credentials à partir
de `.env`, importe les 4 workflows (mise à jour si le nom existe déjà) et les **active**. Il ne touche à aucun autre
workflow de l'instance.

| Credential n8n | Type | Contenu |
|---|---|---|
| Hospital Copilot — Anthropic (x-api-key) | Header Auth | `x-api-key: ANTHROPIC_API_KEY` |
| Hospital Copilot — Telegram | Telegram API | `TELEGRAM_BOT_TOKEN` |
| Hospital Copilot — Plateforme (jeton de service) | Header Auth | `Authorization: Bearer PLATFORM_SERVICE_TOKEN` |
| Hospital Copilot — Webhook (X-Hospital-Secret) | Header Auth | `X-Hospital-Secret: N8N_WEBHOOK_SECRET` |

Les fichiers `n8n/workflows/*.json` ne contiennent **aucun secret** : les credentials y sont désignés par leur nom et
par un jeton (`__CRED_ANTHROPIC__`…), remplacé par l'identifiant réel à l'import. Trois valeurs de configuration non
secrètes sont aussi posées à l'import (`__PLATFORM_URL__`, `__TELEGRAM_CHAT_ID__`, `__LLM_MODEL__`) : elles ne servent
que lorsque le déclencheur est un Cron ; pour un webhook, l'événement de la plateforme fournit ces valeurs.

Si la plateforme n'écoute pas sur le port de `PLATFORM_URL` : `.\n8n\import.ps1 -PlatformUrl http://localhost:8010`.

**Sans clé d'API** (`.\n8n\import.ps1 -Cli` ou `./n8n/import.sh --cli`) : exécute
`npx n8n import:workflow --separate --input=n8n/workflows`. Il faut alors créer les 4 credentials du tableau à la main,
les sélectionner dans les nœuds de chaque workflow (webhooks, HTTP Request, Telegram, Wait), puis activer les workflows.

## 3. Les 4 workflows

| Workflow | Déclencheur | Enchaînement |
|---|---|---|
| **risk-triage** | webhook `risk-created` | Code (prompt : patient, allergies, traitements, constantes, vision) → **HTTP Anthropic** → Code (validation JSON, plan de 3 à 6 étapes, sinon plan de secours) → `POST /api/risks/{id}/plan` → **Telegram infirmier** → **Wait** (reprise par le webhook `risk-ack` ; délai critical 2 min, high 10 min, medium 30 min) → acquitté : fin ; sinon `POST /api/risks/{id}/escalate` → **Telegram médecin de garde** |
| **risk-verify** | webhook `staff-left` | **Wait 2 min** → `GET /api/rooms/{room}/state` → Code (prompt) → **HTTP Anthropic** (résolu ? justification) → Code (validation + garde-fou) → `POST /api/risks/{id}/resolve` ou `/persistent` → **Telegram** de confirmation ou d'alerte |
| **shift-report** | Cron 07:45 et 19:45 + webhook `shift-report` (bouton « Générer ») | `GET /api/events?since=` (risques, événements, humeurs) → **HTTP Anthropic** (rapport structuré par chambre) → Code (validation, mise en forme) → `POST /api/shift-reports` → **Telegram** avec le lien d'impression |
| **pharmacy-alerts** | Cron quotidien 08:00 + webhook `pharmacy-alerts` (bouton de la vue Pharmacie) | `GET /api/pharmacy/alerts?days=30` (stock sous le seuil, péremption < 30 j) → **Telegram pharmacien** |

Chaque étape clé appelle `POST /api/agents/log` : les exécutions apparaissent en direct dans le panneau **Agents** de
la plateforme (cartes `n8n:<workflow>`, étape, durée, identifiant de la réponse Anthropic).

Points de conception :
- **Acquittement dans la plateforme** : le bouton « Je prends en charge » du Centre de commande appelle l'URL de reprise
  du nœud Wait (`…/webhook-waiting/<exécution>/risk-ack`, protégée par `X-Hospital-Secret`). Pas de bouton Telegram
  (il faudrait une URL publique HTTPS). L'entrée du personnel dans la chambre lève aussi l'attente.
- **Garde-fous** : la sévérité reste celle de la plateforme ; `risk-verify` ne clôture jamais un risque si le contrôle
  déterministe de la plateforme (`auto_check`) échoue ; une escalade demandée sur un risque déjà pris en charge est ignorée.
- **Réponse de secours** : si l'appel Anthropic échoue ou renvoie un JSON invalide, le workflow continue avec un plan
  prédéfini (ou le seul contrôle déterministe) et l'indique : mention « réponse de secours (LLM indisponible) » dans la
  plateforme et dans le journal.
- **Délais de démo** : n8n reçoit les délais de la plateforme (`ESCALATION_*_S`, `FOLLOWUP_RECHECK_S`), ce qui permet
  de les raccourcir pour une démonstration. Un nœud Wait de n8n se déclenche avec une précision de quelques secondes.
- n8n (Node) résout `localhost` en IPv6 : les workflows appellent la plateforme sur `127.0.0.1`.

## 4. Repli si n8n est indisponible

La plateforme sonde `GET {N8N_BASE_URL}/healthz` toutes les 20 s et tente chaque webhook 3 fois. En cas d'échec, ou si
`N8N_ENABLED=false` : le RiskAgent rédige le plan lui-même (API Anthropic directe), envoie Telegram, et le
FollowUpAgent gère l'escalade et la re-vérification. L'interface l'affiche : badge « n8n hors ligne · repli local » dans
la barre du haut, étiquette « agents locaux » sur le risque, cartes n8n grisées dans le panneau Agents.

## 5. Vérifier

```powershell
.\n8n\import.ps1 -Check                          # les 4 workflows doivent être ACTIFS
curl http://localhost:8000/health                # "n8n": "online", "llm": "ok"
curl -H "X-N8N-API-KEY: <clé>" "http://localhost:5678/api/v1/executions?limit=10"
```
Dans n8n : onglet **Executions** de chaque workflow (chaque nœud montre ses entrées et sorties, dont la réponse de Claude).
