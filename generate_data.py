"""
Génère des fichiers de test réalistes pour la démonstration :
  - data/accelerometer_data_noisy.csv   : 60 s à 100 Hz, bruit de vibrations + 3 freinages violents cachés
  - data/accelerometer_data_corrupt.csv : même chose + lignes abîmées (pour prouver que le code ne plante pas)

Utilisation :  python generate_data.py
"""
import csv
import random

random.seed(42)                      # même résultat à chaque exécution (démo reproductible)
START = 1678880000.0
HZ = 100
DURATION_S = 60

# (seconde de début, durée en secondes, décélération en m/s²)
BRAKINGS = [(12.0, 0.30, -3.8), (31.5, 0.20, -4.6), (48.2, 0.40, -3.1)]
HARD_BUT_LEGAL = (20.0, 0.50, -1.9)  # freinage ferme mais sous le seuil : ne doit PAS être détecté


def make_rows():
    rows = []
    for i in range(DURATION_S * HZ):
        t = i / HZ
        ax = random.gauss(0.1, 0.12)
        ay = random.gauss(0.0, 0.35)      # vibrations de la route
        az = random.gauss(9.81, 0.10)
        for start, dur, acc in BRAKINGS + [HARD_BUT_LEGAL]:
            if start <= t < start + dur:
                ay = acc + random.gauss(0, 0.2)
        rows.append([f"{START + t:.2f}", f"{ax:.2f}", f"{ay:.2f}", f"{az:.2f}"])
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "acc_x", "acc_y", "acc_z"])
        w.writerows(rows)


if __name__ == "__main__":
    rows = make_rows()
    write_csv("data/accelerometer_data_noisy.csv", rows)

    bad = [r[:] for r in rows]
    bad[100] = ["1678880001.00", "", "0.02", "9.80"]          # cellule vide
    bad[250] = ["1678880002.50", "abc", "0.10", "9.81"]       # texte au lieu d'un nombre
    bad[400] = ["1678880004.00", "0.1"]                       # ligne tronquée
    bad[800] = ["1678880008.00", "0.1", "999.0", "9.8"]       # valeur aberrante du capteur
    bad[1200] = ["1678880012.00", "0.1", "nan", "9.8"]        # valeur NaN
    write_csv("data/accelerometer_data_corrupt.csv", bad)
    print("Fichiers générés dans data/ (noisy + corrupt).")
