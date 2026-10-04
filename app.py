"""
GML Edge Telematics - Application de démonstration (POC)
========================================================
Interface Streamlit qui relie les 2 moteurs :
    Accueil  ->  Module 1 (ZFE)  ->  Module 2 (Safety)  ->  Synthèse

Lancement :  streamlit run app.py
"""

import json
import os
import time

import matplotlib.pyplot as plt
import streamlit as st

import safety_engine as safety
import zfe_engine as zfe

# --------------------------------------------------------------------------
# Configuration de la page
# --------------------------------------------------------------------------
st.set_page_config(page_title="GML Edge Telematics", page_icon="🚚", layout="wide")

PAGES = ["Accueil", "Module 1 - ZFE", "Module 2 - Safety", "Synthèse"]
ACCUEIL, MODULE1, MODULE2, SYNTHESE = PAGES

# Mémoire de l'application (conservée entre deux clics)
st.session_state.setdefault("page", ACCUEIL)
st.session_state.setdefault("zfe_results", None)
st.session_state.setdefault("safety_result", None)
st.session_state.setdefault("safety_samples", None)


def go_to(page):
    """Change de page (utilisé par les boutons de navigation)."""
    st.session_state.page = page


# --------------------------------------------------------------------------
# Barre latérale : navigation entre les modules
# --------------------------------------------------------------------------
st.sidebar.title("GML Edge Telematics")
st.sidebar.caption("Tablette durcie - Zebra ET40 (simulation)")
st.sidebar.radio("Navigation", PAGES, key="page")
st.sidebar.divider()
st.sidebar.markdown("**Avancement**")
st.sidebar.write("✅ Module 1 - ZFE" if st.session_state.zfe_results else "⬜ Module 1 - ZFE")
st.sidebar.write("✅ Module 2 - Safety" if st.session_state.safety_result else "⬜ Module 2 - Safety")
st.sidebar.divider()
st.sidebar.success("Mode hors-ligne : aucun appel réseau")

# Couleurs et messages selon le statut du camion
STATUS_STYLE = {
    "HORS_ZFE": ("#2e9e4f", "✅ Hors ZFE"),
    "BORDURE": ("#f0a500", "⚠️ Pré-alerte : approche de la ZFE"),
    "ALERTE": ("#d62828", "🚨 ALERTE ZFE : entrée en zone interdite"),
    "DANS_ZFE": ("#8d99ae", "ℹ️ Toujours en ZFE (alerte déjà émise)"),
    "INVALIDE": ("#6c757d", "❓ Point GPS invalide ignoré"),
}


# --------------------------------------------------------------------------
# Fonctions de dessin
# --------------------------------------------------------------------------
def draw_map(polygon, results):
    """Dessine la ZFE (polygone), sa bounding box et les points GPS déjà reçus."""
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.fill([p["lon"] for p in polygon], [p["lat"] for p in polygon],
            color="#d62828", alpha=0.15, label="ZFE Lyon")
    ax.plot([p["lon"] for p in polygon], [p["lat"] for p in polygon], color="#d62828")

    box = zfe.compute_bounding_box(polygon)
    ax.plot([box["lon_min"], box["lon_max"], box["lon_max"], box["lon_min"], box["lon_min"]],
            [box["lat_min"], box["lat_min"], box["lat_max"], box["lat_max"], box["lat_min"]],
            "--", color="gray", linewidth=1, label="Bounding box")

    for r in results:
        if r["lat"] is None:
            continue
        color = STATUS_STYLE[r["status"]][0]
        ax.scatter(r["lon"], r["lat"], color=color, s=90, zorder=3)
        ax.annotate(str(r["id"]), (r["lon"], r["lat"]), textcoords="offset points", xytext=(6, 6))

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(alpha=0.3)
    return fig


def draw_acceleration(samples, events, threshold):
    """Courbe de l'axe Y avec le seuil et les freinages violents repérés."""
    t0 = samples[0]["timestamp"]
    times = [s["timestamp"] - t0 for s in samples]
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(times, [s["acc_y"] for s in samples], color="#8d99ae", linewidth=0.8, label="Axe Y (brut)")
    ax.axhline(threshold, color="#d62828", linestyle="--", label=f"Seuil {threshold} m/s²")
    for i, e in enumerate(events):
        ax.scatter(e["timestamp"] - t0, e["peak_acc_y"], color="#d62828", s=70, zorder=3,
                   label="Freinage violent" if i == 0 else None)
    ax.set_xlabel("Temps (secondes)")
    ax.set_ylabel("Accélération (m/s²)")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)
    return fig


# ==========================================================================
# PAGE 0 : ACCUEIL
# ==========================================================================
if st.session_state.page == ACCUEIL:
    st.title("GML Edge Telematics")
    st.subheader("Preuve de concept de la « Boîte Noire Télématique »")
    st.write(
        "La V1 (Cloud) a échoué : sans réseau, la carte ZFE ne se charge pas (amende de 375 €) "
        "et l'assureur n'accepte pas un simple GPS. "
        "La V2 calcule **tout sur la tablette** (Edge Computing), même sans réseau."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h3 style='color: green;'> Module 1 - ZFE<p>", unsafe_allow_html=True)
        st.write("Détecte l'entrée du camion dans la Zone à Faibles Émissions, **sans réseau**.")
        st.caption("Technique : Bounding Box + Ray Casting")
    with col2:
        st.markdown("<h3 style='color: orange;'> Module 2 - Safety<p>", unsafe_allow_html=True)
        st.write("Repère les freinages violents dans les vibrations et calcule un **score de conduite**.")
        st.caption("Technique : filtrage + seuil sur l'accéléromètre")

    st.markdown("### Parcours de démonstration")
    st.markdown(
        "1. **Module 1** : lancer la simulation GPS et voir l'alerte se déclencher à l'entrée de la ZFE\n"
        "2. **Module 2** : analyser le fichier d'accéléromètre bruité et isoler les freinages violents\n"
        "3. **Synthèse** : consulter le bilan et le fichier `daily_score.json`"
    )
    st.button("Démarrer la démonstration →", type="primary", on_click=go_to, args=(MODULE1,))


# ==========================================================================
# PAGE 1 : MODULE 1 - ZFE
# ==========================================================================
elif st.session_state.page == MODULE1:
    st.title("📍 Module 1 - Moteur ZFE (Geo)")
    st.write("Le camion roule : à chaque point GPS, la tablette vérifie **localement** s'il est dans la ZFE.")

    left, right = st.columns([1, 1])
    with left:
        scenario = st.radio(
            "Trace GPS à simuler",
            ["Trace de l'examen (truck_gps.json)", "Trace avec points invalides (test de robustesse)"],
        )
        margin = st.slider("Distance de pré-alerte « Bordure » (mètres)", 0, 1000, 500, step=50)
        speed = st.slider("Vitesse de la simulation (secondes entre 2 points)", 0.2, 2.0, 1.0, step=0.2)
        start = st.button("▶ Lancer la simulation", type="primary")

    # Chargement des données (erreurs affichées proprement, sans plantage)
    try:
        polygon = zfe.load_polygon("data/lyon_polygon.json")
        trace = zfe.load_json("data/truck_gps.json")
    except ValueError as err:
        st.error(f"Impossible de charger les données : {err}")
        st.stop()

    if scenario.startswith("Trace avec"):
        trace = trace[:2] + [
            {"id": 3, "timestamp": "08:00:20", "lat": "ERREUR", "lon": 4.80},   # texte au lieu d'un nombre
            {"id": 4, "timestamp": "08:00:25", "lat": 95.0, "lon": 4.80},       # latitude impossible
        ] + trace[3:]

    with right:
        map_slot = st.empty()
        map_slot.pyplot(draw_map(polygon, st.session_state.zfe_results or []))

    status_slot = st.empty()

    if start:
        results = zfe.analyze_trace(trace, polygon, border_margin_m=margin)   # calcul local, instantané
        shown = []
        for r in results:                                                      # relecture en "temps réel"
            shown.append(r)
            color, message = STATUS_STYLE[r["status"]]
            with status_slot.container():
                text = f"**Point {r['id']} - {r['timestamp']}** : {message}"
                if r["status"] == "ALERTE":
                    st.error(text)
                elif r["status"] in ("BORDURE", "INVALIDE"):
                    st.warning(text)
                elif r["status"] == "DANS_ZFE":
                    st.info(text)
                else:
                    st.success(text)
            map_slot.pyplot(draw_map(polygon, shown))
            time.sleep(speed)
        st.session_state.zfe_results = results

    results = st.session_state.zfe_results
    if results:
        st.subheader("Résultats")
        st.dataframe(
            [{"Point": r["id"], "Heure": r["timestamp"], "Statut": r["status"],
              "Distance au bord (m)": r["distance_m"], "Attendu (énoncé)": r["expected"]} for r in results],
            width="stretch", hide_index=True,
        )
        st.caption(
            "ℹ️ Le point 3 est annoncé « IN (Bordure) » dans l'énoncé mais se situe géométriquement ≈ 450 m "
            "à l'extérieur du polygone : le moteur le classe donc en pré-alerte « Bordure »."
        )
        if os.path.exists("output/zfe_alerts.log"):
            with open("output/zfe_alerts.log", encoding="utf-8") as f:
                st.code("".join(f.readlines()[-8:]), language="text")
        st.button("Passer au Module 2 : Safety →", type="primary", on_click=go_to, args=(MODULE2,))


# ==========================================================================
# PAGE 2 : MODULE 2 - SAFETY
# ==========================================================================
elif st.session_state.page == MODULE2:
    st.title("⚡ Module 2 - Moteur Safety (Physics)")
    st.write("La tablette lit l'accéléromètre et cherche les **freinages violents** cachés dans le bruit.")

    sources = {
        "Fichier de l'énoncé (10 lignes)": "data/accelerometer_data_sample.csv",
        "Fichier bruité (60 s à 100 Hz, 3 freinages cachés)": "data/accelerometer_data_noisy.csv",
        "Fichier corrompu (test de robustesse)": "data/accelerometer_data_corrupt.csv",
        "Importer mon propre fichier CSV": None,
    }
    choice = st.radio("Données à analyser", list(sources.keys()))
    threshold = st.slider("Seuil de freinage violent (m/s²)", -6.0, -1.0, safety.HARSH_BRAKING_THRESHOLD, step=0.1)

    csv_path = sources[choice]
    if csv_path is None:
        uploaded = st.file_uploader("Fichier CSV (colonnes : timestamp, acc_x, acc_y, acc_z)", type="csv")
        if uploaded is not None:
            os.makedirs("output", exist_ok=True)
            csv_path = "output/uploaded.csv"
            with open(csv_path, "wb") as f:
                f.write(uploaded.getvalue())

    if st.button("🔍 Analyser les données", type="primary", disabled=csv_path is None):
        try:
            samples, rejected = safety.read_accelerometer_csv(csv_path)
            events = safety.detect_harsh_braking(samples, threshold)
            result = safety.build_daily_score(events, len(samples), rejected, csv_path)
            result["threshold_ms2"] = threshold
            safety.save_daily_score(result)
            st.session_state.safety_result = result
            st.session_state.safety_samples = samples
        except ValueError as err:                       # erreur prévue : message clair, pas de plantage
            st.session_state.safety_result = None
            st.error(f"Analyse impossible : {err}")

    result = st.session_state.safety_result
    if result:
        samples = st.session_state.safety_samples
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mesures analysées", f"{result['samples_analyzed']:,}".replace(",", " "))
        c2.metric("Mesures rejetées", result["samples_rejected"])
        c3.metric("Freinages violents", result["harsh_braking_count"])
        c4.metric("Score du jour", f"{result['score']}/100")
        st.info(f"Note : **{result['rating']}**")

        st.pyplot(draw_acceleration(samples, result["events"], result["threshold_ms2"]))

        if result["events"]:
            st.subheader("Événements détectés")
            for e in result["events"]:
                st.write(f"🔴 [HARSH BRAKING] {e['datetime_utc']} UTC - pic **{e['peak_acc_y']} m/s²** "
                         f"({e['samples']} mesure(s))")
        else:
            st.success("Aucun freinage violent : conduite prudente 👍")

        with st.expander("Voir le fichier daily_score.json"):
            st.json(result)
        st.download_button("⬇ Télécharger daily_score.json", json.dumps(result, indent=2, ensure_ascii=False),
                           file_name="daily_score.json", mime="application/json")

    nav1, nav2 = st.columns(2)
    nav1.button("← Retour au Module 1", on_click=go_to, args=(MODULE1,))
    if result:
        nav2.button("Voir la synthèse →", type="primary", on_click=go_to, args=(SYNTHESE,))


# ==========================================================================
# PAGE 3 : SYNTHÈSE
# ==========================================================================
else:
    st.title("📋 Synthèse de la démonstration")
    zfe_results = st.session_state.zfe_results
    safety_result = st.session_state.safety_result

    if not zfe_results or not safety_result:
        st.warning("Terminez d'abord les deux modules pour voir la synthèse.")
        if not zfe_results:
            st.button("Aller au Module 1", on_click=go_to, args=(MODULE1,))
        if not safety_result:
            st.button("Aller au Module 2", on_click=go_to, args=(MODULE2,))
    else:
        alerts = [r for r in zfe_results if r["status"] == "ALERTE"]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📍 Conformité ZFE")
            st.metric("Alertes d'entrée en ZFE", len(alerts))
            st.write("Détection réalisée **sans réseau**. Amende de 375 € évitée.")
        with col2:
            st.markdown("### ⚡ Assurance")
            st.metric("Score de conduite", f"{safety_result['score']}/100")
            st.write(f"{safety_result['harsh_braking_count']} freinage(s) violent(s) prouvé(s) par les données.")
        st.success("Les 2 missions du ComEx sont démontrées : conformité ZFE hors-ligne + preuve comportementale.")
        st.button("↺ Recommencer la démonstration", on_click=go_to, args=(ACCUEIL,))
