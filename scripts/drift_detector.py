#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
drift_detector.py
Module de Détection de Dérive (Drift Detection)
Banque fictive "BFC"
Version : 1.0.0
Date : 2026-06-26
================================================================
Ce script compare l'état DEFINI de la gouvernance (fichiers
YAML) avec l'état REEL des systèmes cibles (simule ici par
un fichier JSON). Il detecte les ecarts et genere des alertes.

LE PROBLEME RESOLU :
Dans une banque, un administrateur peut modifier directement
un droit dans Active Directory sans passer par le pipeline
GitOps. Cette modification "sauvage" cree un ecart entre :
- Ce qui est ECRIT dans les fichiers YAML (la politique)
- Ce qui est ACTIF dans les systemes (la realite)

Ce script detecte cet ecart et le signale.

UTILISATION :
    python drift_detector.py

PREREQUIS :
    - Python 3.8+
    - PyYAML
    - Le fichier roles_definitions.yaml (etat defini)
    - Le fichier real_state_simulation.json (etat reel simule)

SORTIE :
    - drift_report.html : rapport visuel des ecarts
    - drift_report.md   : rapport texte des ecarts
================================================================
"""

import yaml
import json
import os
import sys
from datetime import datetime

# --------------------------------------------------------------
# ETAPE 0 : Configuration
# --------------------------------------------------------------
DEFINED_STATE_FILE = "../policies/roles_definitions.yaml"
REAL_STATE_FILE = "../reports/real_state_simulation.json"

# --------------------------------------------------------------
# ETAPE 1 : Chargement de l'état DEFINI (YAML)
# --------------------------------------------------------------
def load_defined_state(filepath):
    """
    Charge l'état defini dans les fichiers de gouvernance.

    Explication pour le non-technique :
    C'est la "photo" de ce qui DEVRAIT etre vrai selon
    la politique de la banque. C'est notre reference.
    """
    if not os.path.exists(filepath):
        print("ERREUR : Fichier '" + filepath + "' introuvable.")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    defined = {}
    for key, value in data.items():
        if not key.startswith("role_"):
            continue
        role_id = value.get("id", key)
        permissions = value.get("permissions", [])
        perm_set = set()
        for p in permissions:
            perm_set.add((p.get("action"), p.get("resource"), p.get("scope")))
        defined[role_id] = perm_set

    return defined


# --------------------------------------------------------------
# ETAPE 2 : Chargement de l'état REEL (simulation)
# --------------------------------------------------------------
def load_real_state(filepath):
    """
    Charge l'état reel des systemes cibles.

    Explication pour le non-technique :
    Dans une vraie banque, ce fichier serait remplace par
    des appels API vers Active Directory, les bases de
    donnees, et le cloud prive. Ici, on simule avec un
    fichier JSON pour demontrer le mecanisme.
    """
    if not os.path.exists(filepath):
        print("ERREUR : Fichier '" + filepath + "' introuvable.")
        print("   Creation d'un fichier de simulation par defaut...")
        create_default_simulation(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    real = {}
    for role_id, perms in data.items():
        perm_set = set()
        for p in perms:
            perm_set.add((p.get("action"), p.get("resource"), p.get("scope")))
        real[role_id] = perm_set

    return real


def create_default_simulation(filepath):
    """
    Cree un fichier de simulation par defaut avec une DERIVE
    intentionnelle pour demontrer la detection.

    Explication pour le non-technique :
    Ce fichier simule l'état reel des systemes. J'ai volontairement
    ajoute une erreur pour montrer comment le script la detecte :
    le role GCC a une permission supplementaire "virement:valider"
    qui n'existe pas dans le YAML. C'est une derive.
    """
    simulation = {
        "ROLE_GCC_001": [
            {"action": "compte:consulter", "resource": "compte_client", "scope": "own_branch"},
            {"action": "compte:modifier", "resource": "compte_client", "scope": "own_branch"},
            {"action": "compte:ouvrir", "resource": "compte_client", "scope": "own_branch"},
            {"action": "virement:valider", "resource": "operation_financiere", "scope": "own_branch"}
        ],
        "ROLE_VFM_001": [
            {"action": "virement:valider", "resource": "operation_financiere", "scope": "own_branch"},
            {"action": "virement:rejeter", "resource": "operation_financiere", "scope": "own_branch"},
            {"action": "virement:consulter", "resource": "operation_financiere", "scope": "own_branch"}
        ],
        "ROLE_AUD_001": [
            {"action": "audit:consulter", "resource": "logs_acces", "scope": "all_branches"},
            {"action": "audit:consulter", "resource": "matrice_roles", "scope": "all_branches"},
            {"action": "audit:generer_rapport", "resource": "rapport_conformite", "scope": "all_branches"}
        ],
        "ROLE_ADM_001": [
            {"action": "iam:administrer", "resource": "roles_definitions", "scope": "all_branches"},
            {"action": "iam:administrer", "resource": "abac_attributes", "scope": "all_branches"},
            {"action": "iam:administrer", "resource": "sod_constraints", "scope": "all_branches"},
            {"action": "audit:consulter", "resource": "logs_acces", "scope": "all_branches"}
        ]
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(simulation, f, indent=2, ensure_ascii=False)

    print("Fichier de simulation cree : " + filepath)
    print("   ATTENTION : Ce fichier contient une DERIVE intentionnelle pour la demonstration.")
    print("      Le role GCC a une permission 'virement:valider' non autorisee.")


# --------------------------------------------------------------
# ETAPE 3 : Comparaison des etats
# --------------------------------------------------------------
def detect_drift(defined, real):
    """
    Compare l'état defini avec l'état reel et identifie les ecarts.

    Explication pour le non-technique :
    On compare les deux listes de permissions pour chaque role.
      Si une permission existe dans le reel mais pas dans le defini,
      c'est une DERIVE (quelqu'un a ajoute un droit en dehors du
      processus). Si une permission existe dans le defini mais pas
      dans le reel, c'est un MANQUE (un droit n'a pas ete applique).

    Les deux cas sont des problemes de conformite.
    """
    drifts = []

    all_roles = set(defined.keys()) | set(real.keys())

    for role_id in sorted(all_roles):
        defined_perms = defined.get(role_id, set())
        real_perms = real.get(role_id, set())

        extra = real_perms - defined_perms
        missing = defined_perms - real_perms

        if extra or missing:
            drifts.append({
                "role": role_id,
                "extra": list(extra),
                "missing": list(missing),
                "severity": "CRITICAL" if extra else "HIGH"
            })

    return drifts


# --------------------------------------------------------------
# ETAPE 4 : Generation du rapport HTML
# --------------------------------------------------------------
def generate_html_report(drifts):
    """
    Genere un rapport HTML des ecarts detectes.
    """
    html_lines = []
    html_lines.append("<!DOCTYPE html>")
    html_lines.append('<html lang="fr">')
    html_lines.append("<head>")
    html_lines.append('  <meta charset="UTF-8">')
    html_lines.append('  <title>Rapport de Derive - BFC</title>')
    html_lines.append("  <style>")
    html_lines.append("    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }")
    html_lines.append("    h1 { color: #c62828; }")
    html_lines.append("    .summary { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }")
    html_lines.append("    .drift-box { background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #c62828; border-radius: 4px; }")
    html_lines.append("    .critical { border-left-color: #c62828; }")
    html_lines.append("    .high { border-left-color: #f57c00; }")
    html_lines.append("    .ok { background: #c6f6d5; padding: 20px; border-radius: 8px; }")
    html_lines.append("    code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: monospace; }")
    html_lines.append("  </style>")
    html_lines.append("</head>")
    html_lines.append("<body>")

    html_lines.append('  <h1>Rapport de Detection de Derive (Drift)</h1>')
    html_lines.append('  <p><strong>Banque :</strong> BFC (fictive) | <strong>Genere le :</strong> &apos; + datetime.now().strftime("%d/%m/%Y %H:%M") + &apos;</p>')
    html_lines.append('  <p><strong>Source definie :</strong> &apos; + DEFINED_STATE_FILE + &apos; | <strong>Source reelle :</strong> &apos; + REAL_STATE_FILE + &apos;</p>')

    html_lines.append('  <div class="summary">')
    html_lines.append('    <h2>Resume</h2>')
    html_lines.append('    <p><strong>Derives detectees :</strong> &apos; + str(len(drifts)) + &apos;</p>')
    if drifts:
        critical = sum(1 for d in drifts if d["severity"] == "CRITICAL")
        html_lines.append('    <p><strong>Derives CRITIQUES :</strong> &apos; + str(critical) + &apos; ALERTE</p>')
        html_lines.append('    <p><em>Une derive CRITIQUE signifie qu&apos;une permission non autorisee est active dans les systemes. Action immediate requise.</em></p>')
    else:
        html_lines.append('    <p>Aucune derive detectee. L&apos;etat reel correspond a l&apos;etat defini.</p>')
    html_lines.append('  </div>')

    if drifts:
        html_lines.append('  <h2>Detail des Derives</h2>')
        for drift in drifts:
            severity_class = "critical" if drift["severity"] == "CRITICAL" else "high"
            html_lines.append('  <div class="drift-box &apos; + severity_class + &apos;">')
            html_lines.append('    <strong>&apos; + drift["role"] + &apos; - Severite : &apos; + drift["severity"] + &apos;</strong>')

            if drift["extra"]:
                html_lines.append('    <p>Permissions en trop (derive positive) :</p>')
                html_lines.append('    <p>Ces permissions existent dans le systeme reel mais PAS dans la politique definie. Elles ont probablement ete ajoutees manuellement.</p>')
                html_lines.append('    <ul>')
                for perm in drift["extra"]:
                    html_lines.append('      <li><code>&apos; + perm[0] + &apos;</code> sur <code>&apos; + perm[1] + &apos;</code> (scope: <code>&apos; + perm[2] + &apos;</code>)</li>')
                html_lines.append('    </ul>')

            if drift["missing"]:
                html_lines.append('    <p>Permissions manquantes (derive negative) :</p>')
                html_lines.append('    <p>Ces permissions sont definies dans la politique mais ABSENTES du systeme reel. Elles n&apos;ont pas ete appliquees.</p>')
                html_lines.append('    <ul>')
                for perm in drift["missing"]:
                    html_lines.append('      <li><code>&apos; + perm[0] + &apos;</code> sur <code>&apos; + perm[1] + &apos;</code> (scope: <code>&apos; + perm[2] + &apos;</code>)</li>')
                html_lines.append('    </ul>')

            html_lines.append('  </div>')
    else:
        html_lines.append('  <div class="ok">')
        html_lines.append('    <h2>Etat conforme</h2>')
        html_lines.append('    <p>Aucun ecart detecte entre la politique definie et la realite des systemes.</p>')
        html_lines.append('  </div>')

    html_lines.append('  <hr>')
    html_lines.append('  <p><em>Rapport genere par drift_detector.py v1.0.0 - &apos; + datetime.now().strftime("%d/%m/%Y %H:%M") + &apos;</em></p>')
    html_lines.append('  <p><em>Ce rapport doit etre examine par le RSSI ou le Responsable Conformite en cas de derive CRITIQUE.</em></p>')
    html_lines.append("</body>")
    html_lines.append("</html>")

    with open("drift_report.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    print("Fichier HTML genere : drift_report.html")


# --------------------------------------------------------------
# ETAPE 5 : Generation du rapport Markdown
# --------------------------------------------------------------
def generate_md_report(drifts):
    """
    Genere un rapport Markdown des ecarts detectes.
    """
    lines = []
    lines.append("# Rapport de Detection de Derive (Drift)")
    lines.append("")
    lines.append("**Banque :** BFC (fictive)  ")
    lines.append("**Genere le :** " + datetime.now().strftime('%d/%m/%Y %H:%M') + "  ")
    lines.append("**Source definie :** `" + DEFINED_STATE_FILE + "` | **Source reelle :** `" + REAL_STATE_FILE + "`  ")
    lines.append("")
    lines.append("## Resume")
    lines.append("")
    lines.append("- **Derives detectees :** " + str(len(drifts)))
    if drifts:
        critical = sum(1 for d in drifts if d["severity"] == "CRITICAL")
        lines.append("- **Derives CRITIQUES :** " + str(critical) + " ALERTE")
        lines.append("")
        lines.append("> *Une derive CRITIQUE signifie qu'une permission non autorisee est active dans les systemes. Action immediate requise.*")
    else:
        lines.append("- Aucune derive detectee.")
    lines.append("")

    if drifts:
        lines.append("## Detail des Derives")
        lines.append("")
        for drift in drifts:
            lines.append("### " + drift['role'] + " - Severite : `" + drift['severity'] + "`")
            lines.append("")
            if drift["extra"]:
                lines.append("**Permissions en trop (derive positive) :**")
                lines.append("*Ces permissions existent dans le systeme reel mais PAS dans la politique definie.*")
                lines.append("")
                for perm in drift["extra"]:
                    lines.append("- `" + perm[0] + "` sur `" + perm[1] + "` (scope: `" + perm[2] + "`)")
                lines.append("")
            if drift["missing"]:
                lines.append("**Permissions manquantes (derive negative) :**")
                lines.append("*Ces permissions sont definies dans la politique mais ABSENTES du systeme reel.*")
                lines.append("")
                for perm in drift["missing"]:
                    lines.append("- `" + perm[0] + "` sur `" + perm[1] + "` (scope: `" + perm[2] + "`)")
                lines.append("")
    else:
        lines.append("## Etat conforme")
        lines.append("")
        lines.append("Aucun ecart detecte entre la politique definie et la realite des systemes.")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Rapport genere par drift_detector.py v1.0.0 - " + datetime.now().strftime('%d/%m/%Y %H:%M') + "*")
    lines.append("")
    lines.append("*Ce rapport doit etre examine par le RSSI ou le Responsable Conformite en cas de derive CRITIQUE.*")

    with open("drift_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Rapport Markdown genere : drift_report.md")


# ================================================================
# POINT D'ENTREE
# ================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("DETECTEUR DE DERIVE (DRIFT DETECTION) - BFC")
    print("Lancement : " + datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    print("=" * 60)
    print("")

    print("Chargement de l'etat DEFINI (YAML)...")
    defined = load_defined_state(DEFINED_STATE_FILE)
    print(str(len(defined)) + " roles charges depuis la politique.")
    print("")

    print("Chargement de l'etat REEL (systemes cibles)...")
    real = load_real_state(REAL_STATE_FILE)
    print(str(len(real)) + " roles charges depuis les systemes.")
    print("")

    print("Detection des ecarts...")
    drifts = detect_drift(defined, real)
    print("Analyse terminee. " + str(len(drifts)) + " derive(s) detectee(s).")
    print("")

    print("Generation des rapports...")
    generate_html_report(drifts)
    generate_md_report(drifts)
    print("")

    print("=" * 60)
    print("DETECTION TERMINEE")
    print("=" * 60)
    print("")
    print("Fichiers produits :")
    print("  - drift_report.html -> Ouvrir dans un navigateur")
    print("  - drift_report.md   -> Integrer dans un rapport")
    print("")

    if drifts:
        print("ALERTE : Des derives ont ete detectees.")
        print("   Consultez les rapports et prenez les mesures correctives.")
        print("   En production, cette alerte serait envoyee au RSSI par email/SIEM.")
    else:
        print("Aucune derive. L'etat reel correspond a la politique.")
