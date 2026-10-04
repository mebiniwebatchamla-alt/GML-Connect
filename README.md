<<<<<<< HEAD
# GML-Connect
=======
# GML Edge Telematics - POC « Boîte Noire Télématique »

Preuve de concept (POC) réalisée pour **GreenMove Logistics** dans le cadre de l'examen
*« Piloter une démarche d'innovation digitale centrée sur l'utilisateur »* (Dossier 4).

> **Contexte** : la V1 (Cloud) a échoué (carte ZFE non chargée sans 4G → amende de 375 € ; assureur non convaincu par un GPS passif).
> La V2 déplace l'intelligence **sur la tablette** (Edge Computing) : tout fonctionne **sans réseau**.

Le POC contient **2 moteurs autonomes** reliés par **une application de démonstration** :

| Module | Rôle | Technique |
|---|---|---|
| **Module 1 - ZFE (Geo)** | Détecter l'entrée du camion dans la Zone à Faibles Émissions | Bounding Box + Ray Casting |
| **Module 2 - Safety (Physics)** | Détecter les freinages violents et calculer un score de conduite | Filtrage + seuil sur l'accéléromètre |

---

## 1. Installation (5 minutes)

**Prérequis** : Python 3.9 ou plus récent ([python.org](https://www.python.org/downloads/)).

```bash
# 1. Récupérer le projet
git clone <URL_DE_VOTRE_DEPOT_GIT>
cd gml-edge-poc

# 2. (Recommandé) Créer un environnement isolé
python -m venv .venv
source .venv/bin/activate        # Mac / Linux
.venv\Scripts\activate           # Windows

# 3. Installer les 2 bibliothèques nécessaires
pip install -r requirements.txt

# 4. (Une seule fois) Générer les jeux de données de test
python generate_data.py
```

> Les fichiers de `data/` sont déjà fournis : l'étape 4 est facultative, elle régénère simplement les fichiers de test.

---

## 2. Procédure de test en local

### A. Lancer l'application complète (recommandé pour la démo)

```bash
streamlit run app.py
```
Le navigateur s'ouvre sur `http://localhost:8501`.

### B. Lancer les moteurs seuls dans le terminal (sans interface)

```bash
python zfe_engine.py        # Module 1 : affiche les logs [ALERT ZFE]
python safety_engine.py     # Module 2 : détecte les freinages et écrit output/daily_score.json
```

### C. Lancer les tests automatiques

```bash
python test_engines.py
```
Résultat attendu : `Tous les tests sont OK`

---

## 3. Structure du projet

```
gml-edge-poc/
├── app.py                  # Interface Streamlit (navigation Accueil → Module 1 → Module 2 → Synthèse)
├── zfe_engine.py           # Module 1 : Ray Casting + Bounding Box
├── safety_engine.py        # Module 2 : lecture CSV, filtrage, seuil, score, export JSON
├── generate_data.py        # Génère les fichiers de test (bruit + freinages cachés + lignes corrompues)
├── test_engines.py         # Tests automatiques
├── requirements.txt        # Dépendances (streamlit, matplotlib)
├── data/
│   ├── lyon_polygon.json               # Polygone ZFE (Annexe 3)
│   ├── truck_gps.json                  # Trace GPS du camion (Annexe 3)
│   ├── accelerometer_data_sample.csv   # Extrait de l'énoncé (10 lignes)
│   ├── accelerometer_data_noisy.csv    # 60 s à 100 Hz, 3 freinages violents cachés
│   └── accelerometer_data_corrupt.csv  # Mêmes données + lignes abîmées (test de robustesse)
└── output/                 # Créé automatiquement : daily_score.json et zfe_alerts.log
```

**Pourquoi Streamlit ?** C'est l'interface la plus simple pour un POC : pas de code graphique complexe,
rendu moderne, navigation et boutons en quelques lignes. Les moteurs (`zfe_engine.py`, `safety_engine.py`)
restent **indépendants de l'interface** : ils pourraient être réutilisés tels quels dans l'application Android de la tablette.

---

## 4. Parcours UX de la démonstration

Le parcours suit le déroulé d'une journée de conduite : **« Où suis-je ? » → « Comment ai-je conduit ? » → « Bilan »**.

| Étape | Écran | Action de l'utilisateur | Réaction du système | Intention UX |
|---|---|---|---|---|
| **0** | Accueil | Lit le contexte et clique sur **« Démarrer la démonstration »** | Affiche le problème (V1) et la solution (V2), les 2 modules, le parcours en 3 étapes | Comprendre en 10 secondes pourquoi l'outil existe |
| **1** | Module 1 | Choisit la trace GPS, règle la pré-alerte « Bordure », clique sur **« Lancer la simulation »** | Les points GPS arrivent un par un sur la carte. Couleurs : 🟢 hors ZFE · 🟠 pré-alerte · 🔴 **ALERTE ZFE** à l'entrée · ⚪ toujours dedans | Un seul code couleur, lisible d'un coup d'œil |
| **1b** | Module 1 | Option « Trace avec points invalides » | Les points invalides sont signalés et **ignorés** : le programme ne plante pas | Prouver la robustesse |
| **2** | Module 1 | Consulte le tableau et le journal `[ALERT ZFE]`, puis clique sur **« Passer au Module 2 → »** | Tableau récapitulatif + journal des alertes | Transition guidée, sans menu à chercher |
| **3** | Module 2 | Choisit le fichier (énoncé / bruité / corrompu / le sien), règle le seuil, clique sur **« Analyser »** | Courbe de l'accéléromètre avec le seuil et les freinages repérés en rouge, indicateurs (mesures, rejets, freinages, score) | Rendre visible « l'aiguille dans la botte de foin » |
| **4** | Module 2 | Ouvre `daily_score.json` ou le télécharge | Fichier de preuve prêt à envoyer à l'assureur | Répondre à la demande d'AssurezMoi |
| **5** | Synthèse | Clique sur **« Voir la synthèse → »** | Bilan des 2 missions : conformité ZFE hors-ligne + score de conduite | Conclure sur la valeur business |

La **barre latérale** montre à tout moment l'avancement (⬜ → ✅) et permet de revenir en arrière.

### Choix de conception pour limiter la charge mentale (lien avec le Dossier 2)
- **Une alerte, pas dix** : l'alerte ZFE ne se déclenche qu'**à l'entrée** de la zone ; ensuite le statut passe en info (évite la fatigue d'alerte).
- **Pré-alerte « Bordure »** : prévenir avant l'entrée laisse le temps de réagir.
- **Code couleur unique** (vert / orange / rouge) accompagné d'un texte et d'un pictogramme (jamais la couleur seule).
- **Messages d'erreur en français clair**, jamais de message technique.

---

## 5. Comment fonctionnent les algorithmes

### Module 1 - ZFE (`zfe_engine.py`)

**Objectif** : savoir si un point GPS est dans le polygone, très vite et sans réseau.

1. **Bounding Box (filtre rapide)** : on calcule *une seule fois* le plus petit rectangle qui entoure la ZFE
   (lat min/max, lon min/max). Si le point est hors du rectangle, il est forcément hors ZFE : réponse en **4 comparaisons**.
2. **Ray Casting (test précis)** : on trace un rayon horizontal depuis le point et on compte les côtés du polygone qu'il traverse.
   **Impair = dedans**, **pair = dehors**.
3. **Complexité** : une seule boucle sur les sommets → **O(N)** (aucune double boucle → pas de O(N²), conformément à l'Annexe 2).
4. **Mémoire** : le polygone est une liste de 6 points → quelques octets, très loin des 150 Mo disponibles sur la ET40.

**Pistes de réflexion écartées** : appeler une API cartographique (impossible sans réseau), charger une librairie géospatiale lourde
(trop de mémoire pour la tablette), tester le point contre chaque côté avec une double boucle (O(N²)).

### Module 2 - Safety (`safety_engine.py`)

**Objectif** : retrouver les freinages violents cachés dans le bruit des vibrations.

1. **Lecture** ligne par ligne (pas de chargement complet en mémoire).
2. **Filtrage** : les lignes vides, tronquées, non numériques, `NaN` ou aberrantes (> 50 m/s²) sont **rejetées et comptées**, sans interrompre l'analyse.
3. **Seuil** : sur l'axe Y (longitudinal), une valeur **< -2,5 m/s²** est un freinage violent.
4. **Regroupement** : à 100 mesures par seconde, un freinage dure plusieurs mesures → elles sont regroupées en **un seul événement**.
5. **Score** : 100 points − 10 par freinage violent (minimum 0), traduit en note A/B/C/D.
6. **Export** : `output/daily_score.json`.

> Le fichier bruité contient aussi un freinage ferme à -1,9 m/s² : il est **volontairement non détecté** (sous le seuil) pour montrer que l'algorithme ne produit pas de faux positifs.

**Format de `daily_score.json`** (format défini pour le projet) :
```json
{
  "truck_id": "GML-001",
  "generated_at_utc": "2026-10-04 14:00:00",
  "source_file": "accelerometer_data_noisy.csv",
  "threshold_ms2": -2.5,
  "samples_analyzed": 6000,
  "samples_rejected": 0,
  "harsh_braking_count": 3,
  "score": 70,
  "rating": "B - Conduite correcte",
  "events": [
    { "timestamp": 1678880012.0, "datetime_utc": "2023-03-15 11:33:32", "peak_acc_y": -4.3, "samples": 31 }
  ]
}
```

---

## 6. Points d'attention sur l'énoncé (à connaître avant la démo)

1. **Point GPS n°3** : l'énoncé l'annonce `IN (Bordure)`, mais ses coordonnées (45.7850 ; 4.8050) sont **géométriquement à l'extérieur** du polygone
   (≈ 450 m du bord). Le moteur le classe donc en **pré-alerte « BORDURE »** et déclenche l'alerte ZFE au point 4. Le résultat est cohérent avec la géométrie réelle.
2. **Unité du seuil** : la consigne parle de « 2.5G » alors que l'Annexe 3 précise **2,5 m/s²** (2,5 G = 24,5 m/s², soit une collision). Le POC suit l'Annexe 3.
3. **Score de conduite** : la formule (−10 points par freinage) est une **hypothèse de travail**, modifiable dans `safety_engine.py` (`PENALTY_PER_EVENT`).

---

## 7. Limites du POC et suites

- Les données sont **simulées** (fichiers) ; en production, elles viendraient des capteurs de la tablette (API Android).
- L'application tourne sur ordinateur ; la version industrielle serait une application Android native réutilisant la même logique.
- Prochaines étapes : base locale (SQLite) et agrégation des données avant envoi 4G, gestion de compte, interface HUD embarquée.

---

## 8. Script de démonstration vidéo (7-8 min)

1. **(1 min)** Accueil : rappeler la V1 en échec et le pivot Edge.
2. **(3 min)** Module 1 : lancer la simulation, montrer l'**alerte rouge à l'entrée**, la pré-alerte orange, puis le test « points invalides ».
3. **(3 min)** Module 2 : analyser le fichier **bruité**, montrer la courbe et les 3 freinages isolés, puis le fichier **corrompu** (5 lignes rejetées, aucun plantage), puis `daily_score.json`.
4. **(1 min)** Terminal : `python test_engines.py` → « Tous les tests sont OK ».
>>>>>>> 9bcd07a (fichier readme ajouté avec les détails: de l'installation à l'utilisation de l'app)
