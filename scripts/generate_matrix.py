#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
generate_matrix.py
Générateur de Matrice de Séparation des Tâches (SoD)
Banque fictive "BFC"
Version : 1.0.0
Date : 2026-06-26
================================================================
Ce script lit les fichiers de gouvernance YAML et produit une
matrice de compatibilité entre rôles. Il est conçu pour être
compris par un consultant IAM ou un RSSI sans compétences
de développement avancées.

UTILISATION :
    python generate_matrix.py

PRÉREQUIS :
    - Python 3.8+
    - PyYAML (pip install pyyaml)
    - Les fichiers roles_definitions.yaml et sod_constraints.yaml
      doivent être dans le même dossier que ce script.

SORTIE :
    - sod_matrix.html  : matrice visuelle (ouvrir dans un navigateur)
    - sod_matrix.md    : matrice textuelle (intégrable dans un rapport)
    - sod_report.txt   : rapport de synthèse avec alertes
================================================================
"""

# --------------------------------------------------------------
# ÉTAPE 0 : Imports — on charge les bibliothèques nécessaires
# --------------------------------------------------------------
# yaml : permet de lire les fichiers .yaml (comme roles_definitions.yaml)
# os   : permet de manipuler les chemins de fichiers
# datetime : pour dater les rapports générés
# --------------------------------------------------------------
import yaml
import os
import sys
from datetime import datetime

# --------------------------------------------------------------
# ÉTAPE 1 : Configuration — chemins des fichiers source
# --------------------------------------------------------------
# On définit ici les noms des fichiers à lire.
# Si tu veux les renommer, change juste ces deux lignes.
# --------------------------------------------------------------
ROLES_FILE = "../policies/roles_definitions.yaml"
SOD_FILE = "../policies/sod_constraints.yaml"

# --------------------------------------------------------------
# ÉTAPE 2 : Fonction de chargement YAML
# --------------------------------------------------------------
# Cette fonction lit un fichier YAML et le transforme en
# structure Python (dictionnaires, listes) que le script
# peut manipuler.
#
# Paramètre : filepath (str) — chemin du fichier à lire
# Retour    : dict — contenu du fichier sous forme de données
# --------------------------------------------------------------
def load_yaml(filepath):
    """
    Charge un fichier YAML et retourne son contenu structuré.

    Explication pour le non-technique :
    → Le fichier YAML est un texte structuré. Cette fonction
      le "traduit" en données que Python peut comprendre
      (comme un traducteur qui passe du français à l'anglais).
    """
    # On vérifie que le fichier existe avant de l'ouvrir.
    # Cela évite une erreur si le fichier est manquant.
    if not os.path.exists(filepath):
        print(f"❌ ERREUR : Le fichier '{filepath}' est introuvable.")
        print(f"   Vérifie qu'il est bien dans le dossier : {os.getcwd()}")
        sys.exit(1)  # On arrête le script proprement

    # On ouvre le fichier en mode lecture ("r") avec encodage UTF-8
    # (pour bien gérer les accents français).
    with open(filepath, "r", encoding="utf-8") as f:
        # yaml.safe_load lit le fichier et le convertit en données Python.
        # "safe" signifie qu'il ne peut pas exécuter de code malveillant —
        # c'est une bonne pratique de sécurité.
        data = yaml.safe_load(f)

    return data


# --------------------------------------------------------------
# ÉTAPE 3 : Extraction des rôles
# --------------------------------------------------------------
# Cette fonction parcourt le fichier roles_definitions.yaml
# et extrait pour chaque rôle :
#   - son identifiant (id)
#   - son nom lisible (name)
#   - ses incompatibilités déclarées (sod_incompatible_with)
#
# Paramètre : data (dict) — contenu du fichier YAML
# Retour    : dict — {id_role: {name, incompatibles}}
# --------------------------------------------------------------
def extract_roles(data):
    """
    Extrait la liste des rôles et leurs incompatibilités.

    Explication pour le non-technique :
    → On parcourt le fichier YAML rôle par rôle. Pour chacun,
      on note son nom et la liste des rôles avec lesquels il
      est incompatible (SoD). Cela construit notre "carte"
      des incompatibilités.
    """
    roles = {}

    # On parcourt toutes les clés du fichier YAML.
    # Une clé comme "role_gcc" correspond à un rôle défini.
    for key, value in data.items():
        # On ignore les commentaires et les clés qui ne sont pas des rôles
        # (par exemple, les lignes de séparation comme "# NOTE SUR L'ABAC").
        if not key.startswith("role_"):
            continue

        # On récupère l'identifiant technique du rôle (ex: "ROLE_GCC_001")
        role_id = value.get("id", key)

        # On récupère le nom lisible (ex: "Gestionnaire de Comptes Clients")
        role_name = value.get("name", key)

        # On récupère la liste des rôles incompatibles.
        # Si aucun n'est défini, on met une liste vide (pas d'incompatibilité).
        incompatibles = value.get("sod_incompatible_with", [])

        # On stocke tout ça dans notre dictionnaire "roles"
        roles[role_id] = {
            "name": role_name,
            "incompatibles": incompatibles,
            "key": key  # on garde la clé YAML pour référence
        }

    return roles


# --------------------------------------------------------------
# ÉTAPE 4 : Extraction des règles SoD explicites
# --------------------------------------------------------------
# Cette fonction lit le fichier sod_constraints.yaml et extrait
# les règles de séparation définies par l'auditeur / le RSSI.
# Ces règles sont le "contrat" de SoD — elles complètent les
# incompatibilités déclarées dans roles_definitions.yaml.
#
# Paramètre : data (dict) — contenu du fichier sod_constraints.yaml
# Retour    : list — liste des règles SoD
# --------------------------------------------------------------
def extract_sod_rules(data):
    """
    Extrait les règles de Séparation des Tâches (SoD).

    Explication pour le non-technique :
    → Le fichier sod_constraints.yaml contient les règles MÉTIER
      de séparation. Cette fonction les lit et les structure
      pour qu'on puisse les croiser avec les rôles.
    """
    rules = []

    for key, value in data.items():
        # On ignore les clés qui ne sont pas des règles SoD
        if not key.startswith("sod_rule_"):
            continue

        rule = {
            "id": value.get("id", key),
            "name": value.get("name", ""),
            "description": value.get("description", ""),
            "severity": value.get("severity", "HIGH"),
            "roles": value.get("roles_incompatible", []),
            "justification": value.get("justification_allowed", False),
            "rationale": value.get("business_rationale", "")
        }
        rules.append(rule)

    return rules


# --------------------------------------------------------------
# ÉTAPE 5 : Construction de la matrice de compatibilité
# --------------------------------------------------------------
# Cette fonction construit une matrice N×N où N = nombre de rôles.
# Chaque cellule [i][j] indique si le rôle i est compatible
# avec le rôle j (✅) ou incompatible (❌).
#
# Paramètres :
#   - roles (dict) : rôles extraits
#   - sod_rules (list) : règles SoD explicites
# Retour : dict — matrice {role_id: {role_id: statut}}
# --------------------------------------------------------------
def build_matrix(roles, sod_rules):
    """
    Construit la matrice de compatibilité entre tous les rôles.

    Explication pour le non-technique :
    → On crée un tableau où chaque ligne et chaque colonne
      représente un rôle. Une case rouge (❌) signifie que les
      deux rôles ne peuvent pas être cumulés par la même
      personne. Une case verte (✅) signifie qu'ils peuvent
      l'être.
    """
    # On récupère la liste ordonnée des identifiants de rôles
    role_ids = sorted(roles.keys())
    n = len(role_ids)

    # On initialise la matrice : par défaut, tout est compatible (✅)
    # C'est le "principe de confiance" : on part du principe que
    # deux rôles peuvent être cumulés, sauf preuve du contraire.
    matrix = {}
    for r1 in role_ids:
        matrix[r1] = {}
        for r2 in role_ids:
            # Un rôle est toujours compatible avec lui-même
            if r1 == r2:
                matrix[r1][r2] = "SAME"
            else:
                matrix[r1][r2] = "COMPATIBLE"

    # ----------------------------------------------------------
    # ÉTAPE 5a : On marque les incompatibilités déclarées
    # dans roles_definitions.yaml
    # ----------------------------------------------------------
    for role_id, role_info in roles.items():
        for incompatible_id in role_info["incompatibles"]:
            # On marque les deux sens de l'incompatibilité
            # (si A est incompatible avec B, alors B est incompatible avec A)
            matrix[role_id][incompatible_id] = "INCOMPATIBLE"
            matrix[incompatible_id][role_id] = "INCOMPATIBLE"

    # ----------------------------------------------------------
    # ÉTAPE 5b : On marque les incompatibilités des règles SoD
    # explicites (sod_constraints.yaml)
    # ----------------------------------------------------------
    for rule in sod_rules:
        rule_roles = rule["roles"]
        # Pour chaque paire de rôles dans la règle, on marque ❌
        for i in range(len(rule_roles)):
            for j in range(i + 1, len(rule_roles)):
                r1 = rule_roles[i]
                r2 = rule_roles[j]
                matrix[r1][r2] = "INCOMPATIBLE"
                matrix[r2][r1] = "INCOMPATIBLE"

    return matrix, role_ids


# --------------------------------------------------------------
# ÉTAPE 6 : Génération du rapport HTML
# --------------------------------------------------------------
# Cette fonction produit un fichier HTML coloré que l'on peut
# ouvrir dans un navigateur. C'est le livrable visuel pour
# l'auditeur / le RSSI.
#
# Paramètres :
#   - matrix (dict) : matrice de compatibilité
#   - role_ids (list) : liste ordonnée des rôles
#   - roles (dict) : infos détaillées des rôles
#   - sod_rules (list) : règles SoD
# --------------------------------------------------------------
def generate_html(matrix, role_ids, roles, sod_rules):
    """
    Génère un fichier HTML avec la matrice SoD colorée.

    Explication pour le non-technique :
    → Cette fonction "écrit" un fichier web (HTML) qui contient
      un tableau coloré. Tu l'ouvres dans Chrome/Firefox/Edge
      et tu vois immédiatement les incompatibilités en rouge.
    """

    # On compte les violations pour le résumé
    violation_count = 0
    for r1 in role_ids:
        for r2 in role_ids:
            if matrix[r1][r2] == "INCOMPATIBLE":
                violation_count += 1
    # On divise par 2 car la matrice est symétrique (A↔B = B↔A)
    violation_count = violation_count // 2

    # On construit le contenu HTML ligne par ligne
    html_lines = []
    html_lines.append("<!DOCTYPE html>")
    html_lines.append('<html lang="fr">')
    html_lines.append("<head>")
    html_lines.append('  <meta charset="UTF-8">')
    html_lines.append('  <title>Matrice SoD — BFC</title>')
    html_lines.append("  <style>")
    html_lines.append("    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }")
    html_lines.append("    h1 { color: #1a3a5c; }")
    html_lines.append("    h2 { color: #2c5282; font-size: 1.1em; margin-top: 30px; }")
    html_lines.append("    table { border-collapse: collapse; margin-top: 20px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }")
    html_lines.append("    th, td { border: 1px solid #ddd; padding: 12px; text-align: center; font-size: 0.9em; }")
    html_lines.append("    th { background: #1a3a5c; color: white; }")
    html_lines.append("    .compatible { background: #c6f6d5; color: #22543d; }")  # vert clair
    html_lines.append("    .incompatible { background: #fed7d7; color: #742a2a; font-weight: bold; }")  # rouge clair
    html_lines.append("    .same { background: #e2e8f0; color: #4a5568; }")  # gris
    html_lines.append("    .legend { margin-top: 20px; padding: 15px; background: white; border-radius: 8px; }")
    html_lines.append("    .legend span { display: inline-block; width: 20px; height: 20px; margin-right: 8px; vertical-align: middle; border: 1px solid #ccc; }")
    html_lines.append("    .summary { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }")
    html_lines.append("    .rule-box { background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #1a3a5c; border-radius: 4px; }")
    html_lines.append("    .critical { border-left-color: #e53e3e; }")
    html_lines.append("  </style>")
    html_lines.append("</head>")
    html_lines.append("<body>")

    # En-tête
    html_lines.append(f'  <h1>🛡️ Matrice de Séparation des Tâches (SoD)</h1>')
    html_lines.append(f'  <p><strong>Banque :</strong> BFC (fictive) | <strong>Généré le :</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>')
    html_lines.append(f'  <p><strong>Source :</strong> roles_definitions.yaml + sod_constraints.yaml</p>')

    # Résumé
    html_lines.append('  <div class="summary">')
    html_lines.append(f'    <h2>📊 Résumé</h2>')
    html_lines.append(f'    <p><strong>Nombre de rôles :</strong> {len(role_ids)}</p>')
    html_lines.append(f'    <p><strong>Règles SoD actives :</strong> {len(sod_rules)}</p>')
    html_lines.append(f'    <p><strong>Paires incompatibles détectées :</strong> {violation_count}</p>')
    html_lines.append(f'    <p><em>Ce document est généré automatiquement à partir des fichiers de configuration. Il est toujours à jour.</em></p>')
    html_lines.append('  </div>')

    # Légende
    html_lines.append('  <div class="legend">')
    html_lines.append('    <h2>🎨 Légende</h2>')
    html_lines.append('    <p><span class="compatible"></span> ✅ Compatible — ces deux rôles peuvent être cumulés</p>')
    html_lines.append('    <p><span class="incompatible"></span> ❌ INCOMPATIBLE — ces deux rôles NE PEUVENT PAS être cumulés (SoD)</p>')
    html_lines.append('    <p><span class="same"></span> ➖ Même rôle — la diagonale (pas de cumul avec soi-même)</p>')
    html_lines.append('  </div>')

    # Tableau de la matrice
    html_lines.append('  <h2>🔲 Matrice de Compatibilité</h2>')
    html_lines.append('  <table>')

    # Ligne d'en-tête (noms des rôles en colonnes)
    html_lines.append('    <tr>')
    html_lines.append('      <th>Rôle ↓ / Rôle →</th>')
    for r in role_ids:
        # On affiche l'ID court + le nom complet en tooltip
        short_name = r.replace("ROLE_", "")
        html_lines.append(f'      <th title="{roles[r]["name"]}">{short_name}</th>')
    html_lines.append('    </tr>')

    # Lignes de la matrice
    for r1 in role_ids:
        html_lines.append('    <tr>')
        short_name = r1.replace("ROLE_", "")
        html_lines.append(f'      <th title="{roles[r1]["name"]}">{short_name}</th>')
        for r2 in role_ids:
            status = matrix[r1][r2]
            if status == "SAME":
                html_lines.append('      <td class="same">—</td>')
            elif status == "COMPATIBLE":
                html_lines.append('      <td class="compatible">✅</td>')
            else:
                html_lines.append('      <td class="incompatible">❌</td>')
        html_lines.append('    </tr>')

    html_lines.append('  </table>')

    # Détail des règles SoD
    html_lines.append('  <h2>📋 Détail des Règles SoD</h2>')
    for rule in sod_rules:
        severity_class = "critical" if rule["severity"] == "CRITICAL" else ""
        html_lines.append(f'  <div class="rule-box {severity_class}">')
        html_lines.append(f'    <strong>{rule["id"]} — {rule["name"]}</strong>')
        html_lines.append(f'    <p><strong>Sévérité :</strong> {rule["severity"]}</p>')
        html_lines.append(f'    <p><strong>Rôles concernés :</strong> {", ".join(rule["roles"])}</p>')
        html_lines.append(f'    <p><strong>Justification autorisée :</strong> {"Oui" if rule["justification"] else "Non — règle absolue"}</p>')
        html_lines.append(f'    <p><em>{rule["rationale"].replace(chr(10), " ")}</em></p>')
        html_lines.append('  </div>')

    # Pied de page
    html_lines.append('  <hr>')
    html_lines.append(f'  <p><em>Document généré automatiquement par generate_matrix.py v1.0.0 — {datetime.now().strftime("%d/%m/%Y %H:%M")}</em></p>')
    html_lines.append('  <p><em>Ce document est la preuve de conformité. Il est reproductible à tout instant T.</em></p>')
    html_lines.append("</body>")
    html_lines.append("</html>")

    # On écrit le fichier
    output_path = "sod_matrix.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    print(f"✅ Fichier HTML généré : {output_path}")
    return output_path


# --------------------------------------------------------------
# ÉTAPE 7 : Génération du rapport Markdown
# --------------------------------------------------------------
# Même contenu que le HTML, mais en texte brut (Markdown).
# Intégrable directement dans un rapport d'audit Word/PDF.
# --------------------------------------------------------------
def generate_markdown(matrix, role_ids, roles, sod_rules):
    """
    Génère un fichier Markdown avec la matrice SoD.

    Explication pour le non-technique :
    → Le Markdown est un format texte simple qui s'ouvre partout
      (Word, Notepad, GitHub). C'est le format "universel".
    """

    violation_count = 0
    for r1 in role_ids:
        for r2 in role_ids:
            if matrix[r1][r2] == "INCOMPATIBLE":
                violation_count += 1
    violation_count = violation_count // 2

    md_lines = []
    md_lines.append("# 🛡️ Matrice de Séparation des Tâches (SoD)")
    md_lines.append("")
    md_lines.append(f"**Banque :** BFC (fictive)  ")
    md_lines.append(f"**Généré le :** {datetime.now().strftime('%d/%m/%Y %H:%M')}  ")
    md_lines.append(f"**Source :** `roles_definitions.yaml` + `sod_constraints.yaml`  ")
    md_lines.append("")
    md_lines.append("## 📊 Résumé")
    md_lines.append("")
    md_lines.append(f"- **Nombre de rôles :** {len(role_ids)}")
    md_lines.append(f"- **Règles SoD actives :** {len(sod_rules)}")
    md_lines.append(f"- **Paires incompatibles détectées :** {violation_count}")
    md_lines.append("")
    md_lines.append("> *Ce document est généré automatiquement à partir des fichiers de configuration. Il est toujours à jour.*")
    md_lines.append("")
    md_lines.append("## 🎨 Légende")
    md_lines.append("")
    md_lines.append("| Symbole | Signification |")
    md_lines.append("|---------|---------------|")
    md_lines.append("| ✅ | Compatible — ces deux rôles peuvent être cumulés |")
    md_lines.append("| ❌ | **INCOMPATIBLE** — ces deux rôles NE PEUVENT PAS être cumulés (SoD) |")
    md_lines.append("| — | Même rôle — la diagonale |")
    md_lines.append("")
    md_lines.append("## 🔲 Matrice de Compatibilité")
    md_lines.append("")

    # En-tête du tableau Markdown
    header = "| Rôle ↓ \\ Rôle → |"
    separator = "|---|---|"
    for r in role_ids:
        short = r.replace("ROLE_", "")
        header += f" {short} |"
        separator += "---|"
    md_lines.append(header)
    md_lines.append(separator)

    # Lignes
    for r1 in role_ids:
        short = r1.replace("ROLE_", "")
        line = f"| **{short}** |"
        for r2 in role_ids:
            status = matrix[r1][r2]
            if status == "SAME":
                line += " — |"
            elif status == "COMPATIBLE":
                line += " ✅ |"
            else:
                line += " **❌** |"
        md_lines.append(line)

    md_lines.append("")
    md_lines.append("## 📋 Détail des Règles SoD")
    md_lines.append("")

    for rule in sod_rules:
        md_lines.append(f"### {rule['id']} — {rule['name']}")
        md_lines.append("")
        md_lines.append(f"- **Sévérité :** `{rule['severity']}`")
        md_lines.append(f"- **Rôles concernés :** {', '.join(rule['roles'])}")
        md_lines.append(f"- **Justification autorisée :** {'Oui' if rule['justification'] else 'Non — règle absolue'}")
        md_lines.append("")
        md_lines.append(f"> {rule['rationale'].replace(chr(10), ' ')}")
        md_lines.append("")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"*Document généré automatiquement par `generate_matrix.py` v1.0.0 — {datetime.now().strftime('%d/%m/%Y %H:%M')}*")
    md_lines.append("")
    md_lines.append("*Ce document est la preuve de conformité. Il est reproductible à tout instant T.*")

    output_path = "sod_matrix.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"✅ Fichier Markdown généré : {output_path}")
    return output_path


# --------------------------------------------------------------
# ÉTAPE 8 : Génération du rapport texte de synthèse
# --------------------------------------------------------------
# Ce fichier est un résumé brut pour un auditeur qui veut
# juste les chiffres clés, sans le tableau complet.
# --------------------------------------------------------------
def generate_text_report(matrix, role_ids, roles, sod_rules):
    """
    Génère un rapport texte de synthèse.

    Explication pour le non-technique :
    → C'est le "résumé exécutif" : juste les chiffres et les
      alertes. Un RSSI peut le lire en 30 secondes.
    """

    lines = []
    lines.append("=" * 60)
    lines.append("RAPPORT DE SYNTHÈSE — SÉPARATION DES TÂCHES (SoD)")
    lines.append("Banque BFC (fictive)")
    lines.append(f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"NOMBRE DE RÔLES DÉFINIS : {len(role_ids)}")
    for r in role_ids:
        lines.append(f"  • {r} : {roles[r]['name']}")
    lines.append("")
    lines.append(f"RÈGLES SoD ACTIVES : {len(sod_rules)}")
    for rule in sod_rules:
        lines.append(f"  • {rule['id']} : {rule['name']} [{rule['severity']}]")
    lines.append("")

    # Comptage des violations
    violation_count = 0
    violations = []
    for r1 in role_ids:
        for r2 in role_ids:
            if r1 < r2 and matrix[r1][r2] == "INCOMPATIBLE":
                violation_count += 1
                violations.append((r1, r2))

    lines.append(f"PAIRES INCOMPATIBLES DÉTECTÉES : {violation_count}")
    if violations:
        lines.append("Liste des incompatibilités :")
        for v1, v2 in violations:
            lines.append(f"  ❌ {v1}  ↔  {v2}")
    else:
        lines.append("  Aucune incompatibilité détectée.")
    lines.append("")
    lines.append("=" * 60)
    lines.append("STATUT : Ce rapport est généré automatiquement.")
    lines.append("Il est reproductible à tout instant T.")
    lines.append("=" * 60)

    output_path = "sod_report.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Fichier texte généré : {output_path}")
    return output_path


# ================================================================
# POINT D'ENTRÉE DU SCRIPT (main)
# ================================================================
# C'est ici que tout commence quand on lance le script.
# On appelle chaque fonction dans l'ordre logique.
# ================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("GÉNÉRATEUR DE MATRICE SoD — BFC")
    print(f"Lancement : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    print("")

    # Étape 1 : on charge les fichiers YAML
    print("📂 Chargement des fichiers de configuration...")
    roles_data = load_yaml(ROLES_FILE)
    sod_data = load_yaml(SOD_FILE)
    print("✅ Fichiers chargés avec succès.")
    print("")

    # Étape 2 : on extrait les données
    print("🔍 Extraction des rôles et des règles SoD...")
    roles = extract_roles(roles_data)
    sod_rules = extract_sod_rules(sod_data)
    print(f"✅ {len(roles)} rôles extraits.")
    print(f"✅ {len(sod_rules)} règles SoD extraites.")
    print("")

    # Étape 3 : on construit la matrice
    print("🔲 Construction de la matrice de compatibilité...")
    matrix, role_ids = build_matrix(roles, sod_rules)
    print("✅ Matrice construite.")
    print("")

    # Étape 4 : on génère les trois rapports
    print("📝 Génération des rapports...")
    generate_html(matrix, role_ids, roles, sod_rules)
    generate_markdown(matrix, role_ids, roles, sod_rules)
    generate_text_report(matrix, role_ids, roles, sod_rules)
    print("")

    print("=" * 60)
    print("✅ GÉNÉRATION TERMINÉE")
    print("=" * 60)
    print("")
    print("Fichiers produits :")
    print("  • sod_matrix.html   → Ouvrir dans un navigateur (visuel)")
    print("  • sod_matrix.md     → Intégrer dans un rapport Word/PDF")
    print("  • sod_report.txt    → Résumé exécutif pour le RSSI")
    print("")
    print("Prochaine étape : ouvrir sod_matrix.html dans Chrome/Firefox")
    print("pour visualiser la matrice de compatibilité.")
