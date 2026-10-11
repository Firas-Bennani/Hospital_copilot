"""
Interopérabilité HL7 FHIR R4 (V3, étape 4) : fonctions de correspondance PURES (aucun accès base, aucun accès réseau)
entre le modèle de la plateforme et les ressources FHIR. Le routeur `app/api/fhir.py` lit les données et applique les droits.
"""

from .mapping import (  # noqa: F401
    FHIR_MEDIA_TYPE,
    LAB_LOINC,
    PSEUDONYM_SYSTEM,
    VITALS,
    allergy_resources,
    bundle,
    capability_statement,
    condition_resources,
    encounter_resource,
    iso,
    lab_observation,
    medication_request_from_line,
    medication_request_from_treatment,
    operation_outcome,
    patient_resource,
    split_history,
    vital_observations,
)
