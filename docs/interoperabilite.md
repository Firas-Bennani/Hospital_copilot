# Interopérabilité — API HL7 FHIR R4 (lecture seule)

Hospital Copilot expose les données cliniques d'un patient au format **HL7 FHIR R4 (4.0.1)**, en JSON (`application/fhir+json`), pour qu'un système d'information hospitalier (SIH), un dossier patient informatisé ou un entrepôt de données puisse les lire sans connaître le modèle interne de la plateforme.

- Code : `dashboard/app/fhir/mapping.py` (fonctions de correspondance pures, sans accès base), `dashboard/app/api/fhir.py` (routes, droits, traçabilité).
- Interface : bouton **« Exporter en FHIR »** dans la vue *Dossier médical* (`dashboard/static/js/v3/fhir-export.js`) → télécharge `PAT-xxxx-fhir.json`.
- Tests : `dashboard/tests/test_v3_fhir.py`.
- Interrupteur : variable d'environnement `FHIR_ENABLED` (activée par défaut ; `FHIR_ENABLED=0` → toutes les routes `/fhir/*` répondent 404 avec un `OperationOutcome`). Elle est lue à chaque requête.

## 1. Ce qui est exposé

| Requête | Réponse |
|---|---|
| `GET /fhir/metadata` | `CapabilityStatement` minimal (ressources, interactions, paramètres de recherche) |
| `GET /fhir/Patient/{id}` | `Patient` |
| `GET /fhir/Observation?patient={id}` | `Bundle` : constantes vitales + biologie (filtre optionnel `category=vital-signs` ou `category=laboratory`) |
| `GET /fhir/Condition?patient={id}` | `Bundle` : maladies chroniques, antécédents, motif de l'hospitalisation en cours |
| `GET /fhir/AllergyIntolerance?patient={id}` | `Bundle` : allergies |
| `GET /fhir/MedicationRequest?patient={id}` | `Bundle` : ordonnances de traitement hospitalières |
| `GET /fhir/Encounter?patient={id}` | `Bundle` : admissions |
| `GET /fhir/Patient/{id}/$everything` | `Bundle` de toutes les ressources ci-dessus que le rôle de l'appelant peut lire |

`{id}` et `patient=` acceptent indifféremment le pseudonyme (`PAT-0001`), la référence FHIR (`Patient/PAT-0001`) ou l'identifiant interne (`patient_01`). En sortie, seul le pseudonyme apparaît.

Les recherches renvoient un `Bundle` de type `searchset` avec `total`, `link[self]` et `entry[{fullUrl, resource, search.mode}]`. Chaque ressource porte `resourceType`, `id`, `meta.lastUpdated` et une référence `subject` (ou `patient`) de la forme `Patient/PAT-0001`.

Les erreurs sont des `OperationOutcome` :

| Code HTTP | `issue.code` | Cas |
|---|---|---|
| 400 | `required` | paramètre `patient` absent |
| 401 | `login` | appel non authentifié |
| 403 | `forbidden` | ressource non accessible au rôle |
| 404 | `not-found` | patient inconnu |
| 404 | `not-supported` | API désactivée (`FHIR_ENABLED=0`) |

## 2. Correspondance modèle → ressource FHIR

| Donnée de la plateforme | Ressource FHIR | Détail |
|---|---|---|
| `Patient` | `Patient` | `id` = `Patient.code` ; `identifier` = `{system: "urn:hackcure:pseudonym", value: code}` ; `gender` ; `name` et `birthDate` selon les droits (§ 4) |
| Constantes en direct (`room_state(room)["vitals"]`), à défaut dernière mesure `VitalReading` | `Observation` (`vital-signs`) | dernière valeur par constante ; `effectiveDateTime` = horodatage de l'appareil ; `device.display` = identifiant de l'appareil ; `encounter` = admission en cours |
| `LabResult` | `Observation` (`laboratory`) | code local (`urn:hackcure:lab`) + code LOINC quand il est connu ; `valueQuantity` ou `valueString` (résultat qualitatif) ; `referenceRange` ; `interpretation` N / A |
| `MedicalRecordEntry` de type `chronique` | `Condition` (`problem-list-item`) | `code.text`, `onsetDateTime` = date du diagnostic |
| `Patient.history` (texte libre) | `Condition` (`problem-list-item`) | un antécédent par segment (virgules et points-virgules hors parenthèses), sans doublon avec les maladies chroniques ; `code.text` seulement |
| `Admission.reason` (admission en cours) | `Condition` (`encounter-diagnosis`) | motif d'hospitalisation, `code.text` |
| `Patient.allergies` + `MedicalRecordEntry` de type `allergie` | `AllergyIntolerance` | `code.text`, `onsetDateTime` si connu |
| `TreatmentOrder` + `TreatmentOrderLine` (ordonnance de traitement hospitalière) | `MedicationRequest` | `status` draft / active / stopped ; `intent` = `order` ; `medicationCodeableConcept.text` (DCI, dosage, spécialité) ; `dosageInstruction` (texte, voie, horaires `timeOfDay`, durée, `asNeededBoolean`) ; `requester`, `reasonCode`, `groupIdentifier` = n° d'ordonnance ; alertes allergie / interaction en `note` |
| `Treatment` (traitement saisi à l'admission) | `MedicationRequest` | `status` active / completed ; posologie et voie en `dosageInstruction` |
| `Admission` | `Encounter` | `class` = `IMP` (hospitalisation) ; `status` in-progress / finished ; `period` ; `location` = chambre ; `reasonCode` et médecin adresseur |

## 3. Codes LOINC et unités UCUM

### Constantes vitales

| Constante (métrique interne) | LOINC | Libellé LOINC | Unité affichée | Code UCUM |
|---|---|---|---|---|
| Fréquence cardiaque (`hr`) | 8867-4 | Heart rate | /min | `/min` |
| SpO2 (`spo2`) | 59408-5 (+ 2708-6) | Oxygen saturation in Arterial blood by Pulse oximetry | % | `%` |
| Pression artérielle (panel) | 85354-9 | Blood pressure panel with all children optional | — | — |
| ↳ systolique (`sys`) | 8480-6 | Systolic blood pressure | mmHg | `mm[Hg]` |
| ↳ diastolique (`dia`) | 8462-4 | Diastolic blood pressure | mmHg | `mm[Hg]` |
| ↳ moyenne (`map`, si présente) | 8478-0 | Mean blood pressure | mmHg | `mm[Hg]` |
| Température corporelle (`tempC`) | 8310-5 | Body temperature | °C | `Cel` |
| Fréquence respiratoire (`rr`) | 9279-1 | Respiratory rate | /min | `/min` |
| Glycémie capillaire (`glucose`) | 41653-7 | Glucose [Mass/volume] in Capillary blood by Glucometer | g/L | `g/L` |

La glycémie capillaire utilise 41653-7 (lecteur de glycémie) et non 2339-0 (glucose sanguin, mg/dL) : la plateforme mesure au lecteur, en g/L. La pression artérielle est une seule Observation à composants (pas de `valueQuantity` au niveau du panel), comme dans le profil FHIR des signes vitaux.

### Biologie

Chaque résultat porte le code local du laboratoire (`urn:hackcure:lab`, ex. `CRP`). Un code LOINC est ajouté pour : HB 718-7, LEUCO 6690-2, PNN 751-8, PLAQ 777-3, CRP 1988-5, PCT 33959-8, LACT 2524-7, NA 2951-2, K 2823-3, CREAT 14682-9, UREE 22664-7, GLY 2345-7, HBA1C 4548-4, TROPO 67151-1, BNP 33762-6, ASAT 1920-8, ALAT 1742-6, INR 6301-6, ALB 1751-7, TSH 3016-3, PH 2744-1, PCO2 2019-8. Les autres examens (ex. hémocultures, ECBU, TP, LDL, cétonémie) ne portent que le code local.

Unités UCUM de la biologie : `mg/L`, `g/L`, `mmol/L`, `umol/L` (µmol/L), `ng/L`, `ng/mL`, `pg/mL`, `%`, `10*9/L` (G/L), `U/L` (UI/L), `m[IU]/L` (mUI/L), `mm[Hg]`. Une unité inconnue est exportée en clair (`unit`) sans `system` ni `code`.

Cette table de correspondance est écrite à la main et n'a pas été validée contre un serveur de terminologie : elle est à faire relire par un biologiste avant tout usage réel.

## 4. Pseudonymisation et droits

**Identifiant.** L'identifiant FHIR d'un patient est toujours son pseudonyme (`PAT-0001`). Ni l'identifiant interne ni la clé de base n'apparaissent dans les ressources.

**Identité.** Le nom et la date de naissance complète ne sont ajoutés que si l'appelant possède la permission `view_identity` (réceptionniste, infirmier, médecins, propriétaire, psychiatre). Sinon (pharmacien) :

- pas de `name` ;
- `birthDate` réduit à l'année (`"1958"`) ;
- `meta.security` contient l'étiquette `PSEUDED` (`http://terminology.hl7.org/CodeSystem/v3-ObservationValue`).

Le sexe (`gender`) est toujours présent.

**Droits par rôle** — les mêmes que le dossier médical (`dashboard/app/api/dossier.py`) :

| Rôle | Patient | Observation | Condition | AllergyIntolerance | MedicationRequest | Encounter |
|---|---|---|---|---|---|---|
| Médecins, propriétaire, psychiatre, infirmier | oui (identité) | oui | oui | oui | oui | oui |
| Pharmacien | oui (pseudonymisé) | 403 | 403 | oui | oui | 403 |
| Réceptionniste | oui (identité) | 403 | 403 | 403 | 403 | oui, sans motif ni médecin |
| Non authentifié | 401 | 401 | 401 | 401 | 401 | 401 |

`$everything` ne contient que les types autorisés pour le rôle (le pharmacien reçoit Patient + AllergyIntolerance + MedicationRequest). `GET /fhir/metadata` demande aussi une authentification.

**Traçabilité.** Chaque lecture écrit une ligne `AuditLog` : action `fhir_read`, entité `fhir:<Type>` (ou `fhir:Patient/$everything`), identifiant = pseudonyme, détails = portée, nombre de ressources renvoyées. Un refus (403) écrit une ligne `fhir_denied`.

## 5. Exemples

Authentification : le cookie de session de la plateforme, ou un jeton `Bearer` (celui renvoyé par `/api/auth/login`, ou le jeton de service `PLATFORM_SERVICE_TOKEN`). Les guillemets simples évitent que le shell interprète `$everything`.

```bash
# 1. Connexion (le jeton est renvoyé dans le champ "token")
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"medecin","password":"<mot de passe>"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 2. Capacités du serveur
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/fhir/metadata

# 3. Un patient, par son pseudonyme
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/fhir/Patient/PAT-0001

# 4. Dernières constantes vitales
curl -s -H "Authorization: Bearer $TOKEN" 'http://localhost:8000/fhir/Observation?patient=PAT-0001&category=vital-signs'

# 5. Allergies et prescriptions
curl -s -H "Authorization: Bearer $TOKEN" 'http://localhost:8000/fhir/AllergyIntolerance?patient=Patient/PAT-0002'
curl -s -H "Authorization: Bearer $TOKEN" 'http://localhost:8000/fhir/MedicationRequest?patient=PAT-0002'

# 6. Tout le dossier dans un fichier
curl -s -H "Authorization: Bearer $TOKEN" 'http://localhost:8000/fhir/Patient/PAT-0001/$everything' -o PAT-0001-fhir.json
```

Adapter l'hôte et le port à l'installation. Extrait d'une Observation :

```json
{
  "resourceType": "Observation",
  "id": "vital-PAT-0001-heart-rate",
  "meta": {"lastUpdated": "2026-10-11T08:30:00+00:00"},
  "status": "final",
  "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs", "display": "Vital Signs"}]}],
  "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}], "text": "Fréquence cardiaque"},
  "subject": {"reference": "Patient/PAT-0001"},
  "effectiveDateTime": "2026-10-11T08:30:00+00:00",
  "valueQuantity": {"value": 82, "unit": "/min", "system": "http://unitsofmeasure.org", "code": "/min"}
}
```

## 6. Comment un SIH consommerait l'API

1. **Découverte** : `GET /fhir/metadata` indique la version FHIR, les ressources et les paramètres de recherche disponibles.
2. **Rapprochement d'identité** : le SIH conserve la table de correspondance entre son identifiant permanent du patient (IPP) et le pseudonyme `PAT-xxxx`. L'API n'expose pas de recherche de patient par nom : le pseudonyme doit être connu.
3. **Synchronisation** : appel périodique de `GET /fhir/Patient/{id}/$everything` (ou des recherches par type) avec un compte de service ; les `id` des ressources sont stables d'un appel à l'autre, ce qui permet une mise à jour par remplacement côté SIH. Les Observations de constantes vitales représentent la *dernière* valeur connue (un `id` par constante), pas un historique.
4. **Export ponctuel** : le bouton « Exporter en FHIR » produit le même `Bundle` sous forme de fichier, importable dans un autre système ou transmissible avec le dossier lors d'un transfert.

## 7. Limites

- **Lecture seule** : pas de création, de modification ni de suppression (`POST` / `PUT` / `DELETE` ne sont pas implémentés).
- **Pas de SMART-on-FHIR** ni d'OAuth 2 : l'authentification est celle de la plateforme (cookie ou jeton JWT), les droits sont ceux du rôle.
- **Pas de serveur de terminologie** : pas de `$validate-code`, `$expand` ni `$translate` ; la correspondance LOINC est une table statique.
- **Pas de codes SNOMED CT / CIM-10** : antécédents, allergies, motifs d'admission et médicaments sont en texte libre dans la source, ils sont exportés en `code.text` (ou `medicationCodeableConcept.text`) sans code inventé. Les médicaments n'ont ni code ATC ni code CIP.
- **Recherche minimale** : seuls `patient` (alias `subject`) et, pour Observation, `category` sont pris en compte. Pas de `_count`, de pagination, de `_include`, de tri ni de filtre par date ou par code. Pas de lecture unitaire `GET /fhir/Observation/{id}` (seul `Patient` se lit par identifiant). La biologie est limitée aux 1 000 résultats les plus récents.
- **Constantes vitales** : dernière valeur seulement ; l'historique des mesures n'est pas exposé.
- **Conformité non certifiée** : les ressources suivent la structure FHIR R4 de base et n'ont pas été passées au validateur officiel HL7 ni vérifiées contre des profils nationaux.
- **Pseudonymisation, pas anonymisation** : l'année de naissance, le sexe et les données cliniques restent présents ; un export reste une donnée de santé à protéger.
