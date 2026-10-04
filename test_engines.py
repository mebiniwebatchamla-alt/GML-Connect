"""
Tests automatiques simples. Lancement :  python test_engines.py
Si tout est correct, le programme affiche "Tous les tests sont OK".
"""
import zfe_engine as zfe
import safety_engine as safety

poly = zfe.load_polygon("data/lyon_polygon.json")
box = zfe.compute_bounding_box(poly)

# --- Module 1 : ZFE ---------------------------------------------------------
assert zfe.is_inside_zfe(45.7600, 4.8357, poly, box) is True      # centre de la ZFE
assert zfe.is_inside_zfe(45.8100, 4.7500, poly, box) is False     # loin, rejeté par la bounding box
assert zfe.is_inside_zfe(45.7850, 4.8050, poly, box) is False     # proche du bord mais dehors

trace = zfe.load_json("data/truck_gps.json")
statuses = [r["status"] for r in zfe.analyze_trace(trace, poly)]
assert statuses == ["HORS_ZFE", "HORS_ZFE", "BORDURE", "ALERTE", "DANS_ZFE"], statuses

bad = [{"id": 1, "lat": "x", "lon": 4.8}, {"id": 2, "lat": 99, "lon": 4.8}, "n'importe quoi"]
assert [r["status"] for r in zfe.analyze_trace(bad, poly)] == ["INVALIDE"] * 3   # pas de plantage

# --- Module 2 : Safety ------------------------------------------------------
res, _ = safety.analyze_file("data/accelerometer_data_sample.csv", "output/test_sample.json")
assert res["harsh_braking_count"] == 1 and res["events"][0]["peak_acc_y"] == -3.45

res, _ = safety.analyze_file("data/accelerometer_data_noisy.csv", "output/test_noisy.json")
assert res["harsh_braking_count"] == 3 and res["score"] == 70     # le freinage à -1.9 n'est PAS compté

res, _ = safety.analyze_file("data/accelerometer_data_corrupt.csv", "output/test_corrupt.json")
assert res["samples_rejected"] == 5 and res["harsh_braking_count"] == 3

try:
    safety.analyze_file("fichier_inexistant.csv")
    raise AssertionError("une erreur était attendue")
except ValueError:
    pass

print("Tous les tests sont OK")
