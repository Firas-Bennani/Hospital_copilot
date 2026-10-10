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


# ─── ReportAgent : synthèse du dossier médical ───────────────────────────────
def _mock_record_summary(ctx: dict[str, Any]) -> dict[str, Any]:
    p = ctx.get("patient") or {}
    chron = [f"{c['label']} (depuis {c['since']})" for c in ctx.get("maladies_chroniques") or []]
    return {
        "summary": f"{p.get('nom', 'Patient')}, {p.get('age', '?')} ans : {len(chron)} maladie(s) chronique(s) suivie(s), {len(ctx.get('allergies') or [])} allergie(s) documentée(s), "
                   f"{ctx.get('documents_au_dossier', '?')} documents au dossier." + (f" Hospitalisation en cours : {ctx['hospitalisation_en_cours']}." if ctx.get("hospitalisation_en_cours") else ""),
        "allergies": [f"{a['allergen']}" + (f" (documentée en {a['since']})" if a.get("since") else "") for a in ctx.get("allergies") or []] or ["Aucune allergie connue"],
        "chronic": chron or ["Aucune maladie chronique enregistrée"],
        "history": [f"{h['label']} ({h['year']})" for h in ctx.get("antecedents") or []] or ["Aucun antécédent chirurgical ou d'hospitalisation enregistré"],
        "active_treatments": [f"{t['dci']} {t.get('posology', '')}".strip() for t in (ctx.get("traitements_au_long_cours") or [])] + [f"{t['dci']} {t.get('posology', '')} ({t.get('route', '')}, hospitalier)".strip() for t in (ctx.get("traitements_hospitaliers_en_cours") or [])],
        "attention": [f"{v['examen']} {v['valeur']} {v['unite']} le {v['date']} (hors normes)" for v in (ctx.get("dernieres_valeurs_biologiques") or {}).values() if v.get("anormal")][:5]
                     + ([f"Risque de chute {p['risque_de_chute']}"] if p.get("risque_de_chute") in ("high", "medium") else []),
    }


spec(
    "record-summary", agent="ReportAgent", title="Synthèse du dossier médical",
    system=("Tu synthétises le dossier médical d'un patient pour l'équipe soignante, à partir des seuls éléments fournis (extraits déterministes du dossier). "
            "Sois factuel et concis : chaque point cite une date ou une valeur du dossier. Les points d'attention sont ce qu'un soignant doit savoir AVANT d'agir "
            "(allergies, interactions à surveiller, valeurs biologiques hors normes récentes, risque de chute, fragilités)."),
    format='{"summary": "3 à 5 phrases", "allergies": ["..."], "chronic": ["maladie (depuis AAAA)"], "history": ["antécédent (AAAA)"], "active_treatments": ["médicament posologie"], "attention": ["point d\'attention"]}',
    required=["summary"], mock=_mock_record_summary,
)


# ─── DiagnosticsAgent ─────────────────────────────────────────────────────────
def _mock_diagnostics(ctx: dict[str, Any]) -> dict[str, Any]:
    hyps = ctx.get("hypotheses") or []
    lead = hyps[0] if hyps else None
    p = ctx.get("patient") or {}
    if not lead:
        return {"summary": "Aucune hypothèse au-dessus du seuil : surveillance habituelle.", "next_steps": []}
    return {"summary": f"{p.get('nom', 'Patient')} : l'hypothèse la plus étayée est « {lead['label']} » (probabilité {lead['probability']}) — éléments : {'; '.join(lead['pros'][:4])}."
                       + (f" À nuancer : {'; '.join(lead['cons'])}." if lead.get("cons") else ""),
            "next_steps": lead.get("exams", [])[:3]}


spec(
    "diagnostics-live", agent="DiagnosticsAgent", title="Synthèse des hypothèses diagnostiques",
    system=("Tu reçois les hypothèses diagnostiques d'un patient hospitalisé, calculées par des règles déterministes (éléments pour, contre, examens utiles). "
            "Rédige pour le médecin et l'infirmier une synthèse de 3 phrases au plus, puis au plus 4 prochaines étapes concrètes (examens ou surveillances déjà listés). "
            "N'ajoute aucune hypothèse, ne change aucune probabilité, ne conclus pas à un diagnostic."),
    format='{"summary": "3 phrases au plus", "next_steps": ["étape concrète"]}', required=["summary"], mock=_mock_diagnostics,
)


# ─── MedicationAgent ──────────────────────────────────────────────────────────
def _mock_medication(ctx: dict[str, Any]) -> dict[str, Any]:
    if ctx.get("alerte_allergie"):
        return {"vigilance": f"{ctx['alerte_allergie']} — ne pas administrer sans avis médical."}
    if ctx.get("allergies") and ctx["allergies"] != "aucune connue":
        return {"vigilance": f"Allergies connues : {ctx['allergies']}. Vérifier l'identité du patient et le médicament avant l'administration."}
    return {"vigilance": "Vérifier l'identité du patient, la dose et la voie avant l'administration."}


spec(
    "medication-reminders", agent="MedicationAgent", title="Rappel de prise de médicament",
    system=("Un rappel de prise de médicament va être envoyé à l'équipe soignante (le texte du rappel est déjà rédigé par la plateforme). "
            "Ajoute UN point de vigilance utile et court pour cette prise et ce patient : allergie, condition de prise, surveillance après administration. "
            "Si une alerte d'allergie est fournie, c'est le point de vigilance. N'invente ni dose ni horaire."),
    format='{"vigilance": "une phrase"}', required=["vigilance"], max_tokens=4000, mock=_mock_medication,
)


# ─── InterventionAgent ────────────────────────────────────────────────────────
def _mock_intervention(ctx: dict[str, Any]) -> dict[str, Any]:
    r = ctx.get("risque") or {}
    done = [s["etape"] for s in ctx.get("plan_d_action") or [] if s.get("faite")]
    visits = ctx.get("visites") or []
    return {
        "summary": f"{r.get('titre', 'Intervention')} — détecté à {r.get('detecte_a')}, résolu et vérifié à {r.get('resolu_a')}.",
        "context": f"{r.get('titre')} (sévérité {r.get('severite')}) détecté à {r.get('detecte_a')} par {r.get('source')}." + (f" Escaladé à {r['escalade_a']}." if r.get("escalade_a") else ""),
        "intervention": ([f"Prise en charge à {r['pris_en_charge_a']}."] if r.get("pris_en_charge_a") else []) + [f"Visite du personnel de {v['debut']} à {v['fin'] or '—'} ({v['personnes']} personnes)." for v in visits]
                        + ([f"Étapes du plan réalisées : {'; '.join(done)}."] if done else ["Aucune étape du plan n'a été cochée dans la plateforme."]),
        "outcome": f"Revérification : {r.get('verification') or 'critère satisfait'}. Risque clos à {r.get('resolu_a')}.",
        "follow_up": ["Surveillance habituelle des constantes.", "Compléter ce compte rendu si nécessaire avant signature."],
    }


spec(
    "intervention-report", agent="InterventionAgent", title="Brouillon de compte rendu d'intervention",
    system=("Rédige le BROUILLON du compte rendu d'une intervention soignante, uniquement à partir du journal fourni (heures, détection, plan d'action, visites, revérification). "
            "Style factuel et chronologique, avec les heures. Si une information n'est pas dans le journal, écris « non renseigné » : le soignant complétera avant de signer."),
    format='{"summary": "une phrase", "context": "ce qui a été détecté, quand", "intervention": ["action horodatée"], "outcome": "résultat de la revérification", "follow_up": ["suite à donner"]}',
    required=["summary", "intervention"], mock=_mock_intervention,
)
