"""
MODULE 1 - Moteur ZFE (Geo)
===========================
Question posée : "Le camion est-il dans la Zone à Faibles Émissions (ZFE) ?"

Principe (2 étapes, de la plus rapide à la plus précise) :
  1. BOUNDING BOX  : on regarde si le point est dans le plus petit rectangle
                     qui entoure la ZFE. Si non -> HORS ZFE immédiatement.
  2. RAY CASTING   : sinon, on tire un rayon horizontal depuis le point et on
                     compte combien de côtés du polygone il traverse.
                     Nombre impair = DANS la zone / pair = HORS de la zone.

Tout fonctionne SANS RÉSEAU (le polygone est un simple fichier local).
"""

import json
import logging
import math
import os

# --------------------------------------------------------------------------
# Journal des alertes : affiché dans le terminal ET enregistré dans un fichier
# --------------------------------------------------------------------------
os.makedirs("output", exist_ok=True)
logger = logging.getLogger("zfe")
if not logger.handlers:                       # évite les doublons à l'affichage
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S")
    for handler in (logging.StreamHandler(), logging.FileHandler("output/zfe_alerts.log", encoding="utf-8")):
        handler.setFormatter(fmt)
        logger.addHandler(handler)


# --------------------------------------------------------------------------
# Chargement des fichiers (avec gestion des erreurs : le programme ne plante pas)
# --------------------------------------------------------------------------
def load_json(path):
    """Lit un fichier JSON. Lève une erreur claire et lisible si problème."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"Fichier introuvable : {path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Fichier JSON invalide ({path}) : {e}")


def load_polygon(path):
    """Retourne la liste des sommets du polygone ZFE (minimum 3 points)."""
    polygon = load_json(path)
    if not isinstance(polygon, list) or len(polygon) < 3:
        raise ValueError("Le polygone doit contenir au moins 3 points.")
    return polygon


# --------------------------------------------------------------------------
# Étape 1 : Bounding Box (le filtre rapide)
# --------------------------------------------------------------------------
def compute_bounding_box(polygon):
    """Calcule UNE FOIS le rectangle qui entoure le polygone."""
    lats = [p["lat"] for p in polygon]
    lons = [p["lon"] for p in polygon]
    return {"lat_min": min(lats), "lat_max": max(lats),
            "lon_min": min(lons), "lon_max": max(lons)}


def in_bounding_box(lat, lon, box):
    """Vrai si le point est dans le rectangle (4 comparaisons seulement)."""
    return box["lat_min"] <= lat <= box["lat_max"] and box["lon_min"] <= lon <= box["lon_max"]


# --------------------------------------------------------------------------
# Étape 2 : Ray Casting (le test précis)
# --------------------------------------------------------------------------
def ray_casting(lat, lon, polygon):
    """
    Tire un rayon vers l'Est depuis le point et compte les côtés traversés.
    Complexité O(N) avec N = nombre de sommets (une seule boucle, pas de O(N²)).
    """
    inside = False
    j = len(polygon) - 1                       # j = sommet précédent
    for i in range(len(polygon)):
        lat_i, lon_i = polygon[i]["lat"], polygon[i]["lon"]
        lat_j, lon_j = polygon[j]["lat"], polygon[j]["lon"]
        # Le côté [j -> i] est-il à cheval sur la latitude du point ?
        if (lat_i > lat) != (lat_j > lat):
            # Longitude où le côté croise la latitude du point
            lon_croisement = (lon_j - lon_i) * (lat - lat_i) / (lat_j - lat_i) + lon_i
            if lon < lon_croisement:           # le croisement est à l'Est -> le rayon le traverse
                inside = not inside            # on bascule dedans/dehors
        j = i
    return inside


def is_inside_zfe(lat, lon, polygon, box):
    """Combine les deux étapes : box d'abord (rapide), ray casting ensuite (précis)."""
    if not in_bounding_box(lat, lon, box):
        return False                           # éliminé sans aucun calcul lourd
    return ray_casting(lat, lon, polygon)


# --------------------------------------------------------------------------
# Pré-alerte "Bordure" : distance (en mètres) entre le point et le bord de la ZFE
# --------------------------------------------------------------------------
def distance_to_border_m(lat, lon, polygon):
    """Distance approximative au côté le plus proche (suffisant à l'échelle d'une ville)."""
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
    px, py = lon * m_per_deg_lon, lat * m_per_deg_lat
    best = float("inf")
    for i in range(len(polygon) - 1):
        ax, ay = polygon[i]["lon"] * m_per_deg_lon, polygon[i]["lat"] * m_per_deg_lat
        bx, by = polygon[i + 1]["lon"] * m_per_deg_lon, polygon[i + 1]["lat"] * m_per_deg_lat
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        t = 0 if length2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length2))
        best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


# --------------------------------------------------------------------------
# Analyse d'une trace GPS complète
# --------------------------------------------------------------------------
def valid_gps_point(point):
    """Vérifie qu'un point GPS est exploitable (nombres, latitude/longitude réalistes)."""
    try:
        lat, lon = float(point["lat"]), float(point["lon"])
    except (KeyError, TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def analyze_trace(trace, polygon, border_margin_m=500):
    """
    Parcourt la trace GPS point par point et renvoie une liste de résultats.

    Statuts possibles :
      HORS_ZFE  : le camion est dehors
      BORDURE   : dehors, mais à moins de `border_margin_m` mètres (pré-alerte)
      ALERTE    : le camion VIENT D'ENTRER dans la ZFE (alerte déclenchée une seule fois)
      DANS_ZFE  : le camion est toujours dans la ZFE (pas de nouvelle alerte = pas de surcharge)
      INVALIDE  : point GPS inutilisable (ignoré, le programme continue)
    """
    box = compute_bounding_box(polygon)
    results = []
    was_inside = False

    for point in trace:
        pid = point.get("id", "?") if isinstance(point, dict) else "?"
        ts = point.get("timestamp", "?") if isinstance(point, dict) else "?"

        if not isinstance(point, dict) or not valid_gps_point(point):
            logger.info(f"[WARN] Point {pid} ignoré (coordonnées invalides)")
            results.append({"id": pid, "timestamp": ts, "lat": None, "lon": None,
                            "status": "INVALIDE", "distance_m": None, "expected": None})
            continue

        lat, lon = float(point["lat"]), float(point["lon"])
        inside = is_inside_zfe(lat, lon, polygon, box)
        distance = distance_to_border_m(lat, lon, polygon)

        if inside and not was_inside:
            status = "ALERTE"
            logger.info(f"[ALERT ZFE] {ts} - Entrée en ZFE détectée (lat={lat}, lon={lon})")
        elif inside:
            status = "DANS_ZFE"
            logger.info(f"[INFO] {ts} - Camion toujours en ZFE")
        elif distance <= border_margin_m:
            status = "BORDURE"
            logger.info(f"[PRE-ALERTE] {ts} - À {distance:.0f} m de la ZFE")
        else:
            status = "HORS_ZFE"
            logger.info(f"[OK] {ts} - Hors ZFE")

        was_inside = inside
        results.append({"id": pid, "timestamp": ts, "lat": lat, "lon": lon, "status": status,
                        "distance_m": round(distance), "expected": point.get("expected")})
    return results


# --------------------------------------------------------------------------
# Lancement en terminal :  python zfe_engine.py
# --------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        poly = load_polygon("data/lyon_polygon.json")
        trace = load_json("data/truck_gps.json")
        analyze_trace(trace, poly)
    except ValueError as err:
        print(f"Erreur : {err}")
