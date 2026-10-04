"""
MODULE 2 - Moteur Safety (Physics)
==================================
Question posée : "Le chauffeur a-t-il freiné brutalement ?"

Principe :
  1. LECTURE      : on lit le fichier CSV de l'accéléromètre (ligne par ligne).
  2. FILTRAGE     : on écarte les lignes inutilisables ou aberrantes (capteur défaillant).
  3. SEUIL        : sur l'axe Y (avant/arrière), une valeur < -2.5 m/s² = freinage violent.
  4. REGROUPEMENT : plusieurs mesures consécutives sous le seuil = UN SEUL événement
                    (à 100 mesures/seconde, un freinage dure plusieurs mesures).
  5. SCORE        : 100 points - 10 points par freinage violent (minimum 0).
  6. EXPORT       : résultat enregistré dans daily_score.json.
"""

import csv
import json
import os
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# Paramètres (faciles à modifier)
# --------------------------------------------------------------------------
HARSH_BRAKING_THRESHOLD = -2.5   # m/s² : en dessous = freinage violent
SENSOR_MAX_ABS = 50.0            # m/s² : au-delà, la mesure est jugée aberrante (bruit capteur)
PENALTY_PER_EVENT = 10           # points retirés au score par freinage violent
REQUIRED_COLUMNS = ["timestamp", "acc_x", "acc_y", "acc_z"]


# --------------------------------------------------------------------------
# 1 + 2. Lecture et filtrage du CSV
# --------------------------------------------------------------------------
def read_accelerometer_csv(path):
    """
    Lit le CSV et renvoie (mesures_valides, nb_lignes_rejetées).
    Ne plante JAMAIS à cause d'une ligne abîmée : elle est simplement comptée comme rejetée.
    """
    try:
        file = open(path, newline="", encoding="utf-8")
    except FileNotFoundError:
        raise ValueError(f"Fichier introuvable : {path}")

    samples, rejected = [], 0
    with file:
        reader = csv.DictReader(file)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Colonnes manquantes dans le CSV : {', '.join(missing)}")

        for row in reader:
            try:
                sample = {
                    "timestamp": float(row["timestamp"]),
                    "acc_x": float(row["acc_x"]),
                    "acc_y": float(row["acc_y"]),
                    "acc_z": float(row["acc_z"]),
                }
            except (TypeError, ValueError):          # cellule vide, texte, ligne tronquée...
                rejected += 1
                continue
            # float("nan") et valeurs démesurées = capteur défaillant
            if any(v != v or abs(v) > SENSOR_MAX_ABS for k, v in sample.items() if k != "timestamp"):
                rejected += 1
                continue
            samples.append(sample)

    if not samples:
        raise ValueError("Aucune mesure exploitable dans le fichier.")
    return samples, rejected


# --------------------------------------------------------------------------
# 3 + 4. Détection des freinages violents
# --------------------------------------------------------------------------
def detect_harsh_braking(samples, threshold=HARSH_BRAKING_THRESHOLD):
    """
    Parcourt les mesures UNE seule fois (complexité O(N)).
    Renvoie la liste des événements : début, durée, pic de décélération.
    """
    events = []
    current = None                                   # événement en cours (ou None)

    for s in samples:
        if s["acc_y"] < threshold:
            if current is None:                      # début d'un nouveau freinage
                current = {"timestamp": s["timestamp"], "peak_acc_y": s["acc_y"], "samples": 1}
            else:                                    # freinage qui continue
                current["samples"] += 1
                current["peak_acc_y"] = min(current["peak_acc_y"], s["acc_y"])
        elif current is not None:                    # fin du freinage -> on le range
            events.append(current)
            current = None
    if current is not None:
        events.append(current)

    for e in events:                                 # mise en forme lisible
        e["datetime_utc"] = datetime.fromtimestamp(e["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        e["peak_acc_y"] = round(e["peak_acc_y"], 2)
    return events


# --------------------------------------------------------------------------
# 5. Score de conduite
# --------------------------------------------------------------------------
def compute_score(event_count):
    """100 points, moins 10 par freinage violent (jamais en dessous de 0)."""
    return max(0, 100 - PENALTY_PER_EVENT * event_count)


def rating_from_score(score):
    """Traduit le score en note lisible (utile pour l'assureur et le chauffeur)."""
    if score >= 90:
        return "A - Conduite très prudente"
    if score >= 70:
        return "B - Conduite correcte"
    if score >= 50:
        return "C - À améliorer"
    return "D - Conduite à risque"


# --------------------------------------------------------------------------
# 6. Export JSON
# --------------------------------------------------------------------------
def build_daily_score(events, samples_ok, samples_rejected, source_file, truck_id="GML-001"):
    """Construit le contenu du fichier daily_score.json (format défini pour le projet)."""
    score = compute_score(len(events))
    return {
        "truck_id": truck_id,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "source_file": os.path.basename(source_file),
        "threshold_ms2": HARSH_BRAKING_THRESHOLD,
        "samples_analyzed": samples_ok,
        "samples_rejected": samples_rejected,
        "harsh_braking_count": len(events),
        "score": score,
        "rating": rating_from_score(score),
        "events": events,
    }


def save_daily_score(daily_score, path="output/daily_score.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(daily_score, f, indent=2, ensure_ascii=False)
    return path


def analyze_file(csv_path, output_path="output/daily_score.json", truck_id="GML-001"):
    """Enchaîne tout : lecture -> détection -> score -> export. Renvoie le résultat."""
    samples, rejected = read_accelerometer_csv(csv_path)
    events = detect_harsh_braking(samples)
    result = build_daily_score(events, len(samples), rejected, csv_path, truck_id)
    save_daily_score(result, output_path)
    return result, samples


# --------------------------------------------------------------------------
# Lancement en terminal :  python safety_engine.py
# --------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        res, _ = analyze_file("data/accelerometer_data_noisy.csv")
        print(f"{res['harsh_braking_count']} freinage(s) violent(s) détecté(s) - score {res['score']}/100")
        for e in res["events"]:
            print(f"  [HARSH BRAKING] {e['datetime_utc']} - pic {e['peak_acc_y']} m/s²")
        print("Résultat enregistré dans output/daily_score.json")
    except ValueError as err:
        print(f"Erreur : {err}")
