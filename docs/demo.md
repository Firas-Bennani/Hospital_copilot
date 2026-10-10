# Script de démonstration — 3 minutes

Préparation (avant le jury) : `scripts\run-demo.ps1 -Reset` (ou `./scripts/run-demo.sh --reset`), ouvrir <http://localhost:8000>,
se connecter en **infirmier** (`infirmier` / `hackcure2026`) dans un onglet, et en **médecin de garde** (`medecin_garde`) dans un second onglet
(ou un second écran). Onglet **Agents** visible à droite. Variables conseillées : `FOLLOWUP_RECHECK_S=30` (réglé par le script).

| Temps | Action | Ce que le jury voit |
|---|---|---|
| 0:00 | Présenter le jumeau 3D : 4 chambres, accueil, extérieur. Cliquer **101** pour zoomer. | Avatar dans le lit, moniteur animé avec les **vraies constantes** du simulateur (FC, SpO2, PA, T°), étiquettes potence et moniteur, bandeau KPI. |
| 0:20 | **Lancer la démo → full_demo** (chambre 101). | Toast « scénario lancé », étapes affichées au fil de l'eau. |
| 0:30 | Le patient se redresse puis **se lève** (nuit). | Avatar assis puis **debout** à côté du lit ; VisionAgent → RiskAgent : risque **« Lever non accompagné »** (moyen/élevé), notification cloche, chambre **orange**. Veilleuse allumée (règle locale sur le Pi réel). |
| 0:50 | Il marche vers la porte puis **chute**. | Avatar **au sol** (pose existante), expression douleur, chambre **violette** pulsée, bannière critique. Panneau Agents : **VisionAgent → RiskAgent** (critical + plan d'action 3–6 étapes en < 2 s) → **notifications** infirmier + médecin de garde (in-app ; Telegram si configuré). Alarme locale `safety/alarm` si edge réel. |
| 1:10 | Ouvrir **Centre de commande** (infirmier). Montrer l'explication IA qui cite les constantes, les allergies (AINS, aspirine), les traitements. | Plan d'action avec cases à cocher ; équipements de la chambre. |
| 1:25 | À 1:00 du scénario, **l'infirmier entre** dans la chambre. | Avatar **infirmier** en tenue teal près du lit ; FollowUpAgent : risques → **en cours**, `StaffVisit` enregistré ; KPI « personnel en chambre ». |
| 1:35 | Cocher 2 étapes du plan (horodatées), le patient est réinstallé (scénario), **l'infirmier sort**. | FollowUpAgent : « re-vérification dans 30 s ». |
| 2:10 | Attendre la re-vérification. | Risques **résolus + vérifiés** (posture lit, expression apaisée), chambre redevient **verte**, notification « Résolu », journal des agents complet (📥 → 🧠 → ✅). |
| 2:20 | Bonus : à 2:10 du scénario, la **caméra thermique** monte (chaufferette). | Halo orange/rouge sur la tête de l'avatar, moniteur 39 °C, VitalsAgent → risque **« Fièvre »** avec plan (contrôle thermomètre, NEWS2, prévenir le médecin si ≥ 39 °C). |
| 2:35 | **Rapport de garde → Générer** (12 h) puis **Imprimer / PDF**. | Rapport par chambre : événements, risques, actions cochées, état, **humeur** observée ; page d'impression A4. |
| 2:50 | Onglet médecin : **Ordonnance** → ajouter *Clamoxyl* pour la chambre 102. | **Alerte allergie (pénicilline)** immédiate ; signature refusée tant que la ligne existe ; impression. |
| 3:00 | Conclusion : rôles (pharmacien = pharmacie seulement), mode Real pour un vrai Pi (`edge/main.py`), MQTT optionnel. | — |

## Variantes rapides
- `fall_demo` (chambre 104, 40 s) puis `nurse_resolves` (45 s) : même boucle en chambre 104, plus courte.
- `sepsis_trend` (chambre 102, 2 min) : dérive progressive → NEWS2 ≥ 5 → risque « Score NEWS2 élevé » / « Tendance sepsis ».
- `iv_empty` (chambre 103) : perfusion < 50 ml puis occlusion → alertes équipement, étiquette rouge sur la potence.
- `fever_101` : fièvre seule en 101.
- `stop` : remet toutes les chambres au calme.
- Boutons de démo existants (Chute / Douleur / Chute + douleur / Récupération / Séquence auto / Reset) : toujours fonctionnels (état 3D legacy).

## Avec le vrai Raspberry Pi
`python edge/main.py` sur le Pi (voir `MORNING_REPORT.md`) : la chambre 101 passe en vision réelle (`source: edge-yolo|edge-pose`),
le simulateur embarqué coupe automatiquement sa vision virtuelle pour la 101 et ne garde que les appareils.
