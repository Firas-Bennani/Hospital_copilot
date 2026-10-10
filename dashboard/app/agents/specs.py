"""
Spécifications des raisonnements LLM des agents (V2) : une seule source pour
- les workflows n8n (`n8n/build_workflows.py` génère un workflow par entrée) ;
- le repli local (`orchestration._run_local`) quand n8n est indisponible.

Chaque entrée : `agent` (agent Python propriétaire), `webhook` (chemin du webhook n8n), `title`, `system`
(consigne), `format` (forme JSON exacte attendue), `required` (clés obligatoires), `max_tokens`,
`mock(context)` (réponse déterministe de secours, construite à partir des seules valeurs du contexte).
"""

from __future__ import annotations

import json
from typing import Any, Optional

RULES = (
    "Tu es un assistant d'aide à la décision d'une clinique (Hospital Copilot). "
    "Règles : n'invente JAMAIS de valeur ; cite les valeurs fournies ; respecte strictement les allergies et les traitements en cours ; "
    "tu ne poses pas de diagnostic et tu ne prescris rien : tu expliques, synthétises et suggères, un soignant valide. "
    "La détection et la sévérité sont déjà fixées par des règles déterministes : ne les modifie pas. "
    "Réponds en français, UNIQUEMENT par un objet JSON valide, sans texte autour et sans balise Markdown."
)

SPECS: dict[str, dict[str, Any]] = {}


def spec(name: str, **kw: Any) -> None:
    kw.setdefault("webhook", name)
    kw.setdefault("max_tokens", 8000)  # le modèle consomme des tokens de réflexion avant de répondre
    kw.setdefault("required", [])
    SPECS[name] = kw


def build_prompt(workflow: str, context: dict[str, Any]) -> tuple[str, str]:
    s = SPECS[workflow]
    system = RULES + "\n" + s["system"]
    user = f"Contexte (JSON) :\n{json.dumps(context, ensure_ascii=False, indent=1, default=str)}\n\nFormat exact attendu :\n{s['format']}"
    return system, user


def validate(workflow: str, data: Optional[dict[str, Any]]) -> Optional[str]:
    """None si la réponse est exploitable, sinon le motif du rejet."""
    if not isinstance(data, dict):
        return "réponse absente ou JSON invalide"
    missing = [k for k in SPECS[workflow]["required"] if data.get(k) in (None, "", [])]
    return f"clé(s) manquante(s) : {', '.join(missing)}" if missing else None


def _v(ctx: dict[str, Any], *path: str, default: Any = None) -> Any:
    cur: Any = ctx
    for k in path:
        cur = cur.get(k) if isinstance(cur, dict) else None
        if cur is None:
            return default
    return cur


# ─── FeverAgent ───────────────────────────────────────────────────────────────
def _mock_fever(ctx: dict[str, Any]) -> dict[str, Any]:
    p = ctx.get("patient") or {}
    v = ctx.get("constantes") or {}
    labs = ctx.get("bilan_propose") or []
    if ctx.get("phase") == "resultats":
        res = ctx.get("resultats") or []
        abn = [r for r in res if r.get("anormal")]
        return {
            "summary": f"Résultats du bilan reçus pour {p.get('nom', 'le patient')} : {len(abn)} valeur(s) hors normes sur {len(res)}.",
            "interpretation": "; ".join(f"{r['examen']} {r['valeur']} {r.get('unite', '')} (normes {r.get('normes', 'n/a')})" for r in abn) or "Aucune valeur hors normes.",
            "labs": [], "watch": ["Recontrôler la température centrale après l'antipyrétique prescrit.", "Surveiller NEWS2 et qSOFA toutes les heures jusqu'à apyrexie."],
        }
    return {
        "summary": f"Fièvre vraie chez {p.get('nom', 'le patient')} ({p.get('age', '?')} ans) : température centrale {v.get('tempC', '?')} °C ({ctx.get('critere', '')}), "
                   f"qSOFA {ctx.get('qsofa', '?')}, NEWS2 {ctx.get('news2', '?')}. Antécédents : {p.get('antecedents') or 'non renseignés'}. Allergies : {p.get('allergies') or 'aucune connue'}.",
        "exam_focus": ["Rechercher un foyer infectieux (pulmonaire, urinaire, cutané, voie veineuse).", "Évaluer conscience, hydratation et signes de sepsis (qSOFA, NEWS2)."],
        "labs": [{"code": x["code"], "justification": x.get("motif") or "Examen proposé par la règle du parcours fièvre."} for x in labs],
        "watch": ["Température centrale et constantes toutes les heures.", "Vérifier les allergies avant tout traitement."],
    }


spec(
    "fever-pathway", agent="FeverAgent", title="Parcours fièvre : synthèse et justification du bilan",
    system=("Un patient hospitalisé présente une FIÈVRE VRAIE (température centrale, critère déterministe fourni). Le médecin de garde est demandé. "
            "Phase « bilan » : rédige une synthèse courte, les points à examiner en priorité, et justifie CHAQUE examen biologique proposé à partir du dossier "
            "(antécédents, dernières valeurs, traitements, allergies). Tu peux suggérer un examen supplémentaire uniquement s'il figure dans `catalogue`. "
            "Phase « resultats » : interprète prudemment les résultats fournis (valeurs et normes citées) et propose la surveillance."),
    format='{"summary": "2 à 3 phrases", "exam_focus": ["point d\'examen clinique"], "labs": [{"code": "CRP", "justification": "pourquoi, pour CE patient"}], "interpretation": "phase resultats uniquement", "watch": ["surveillance"]}',
    required=["summary"], mock=_mock_fever,
)
