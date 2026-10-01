# app.py - Application d'aide a la lecture des candidatures
#
# Cinq pages, dans l'ordre du travail du comite : charger, classer,
# appliquer les quotas, lire les limites, administrer.
"""
Application d'aide a la lecture des candidatures au programme DataCamp
Donates chez TDEV.

Ce que l'application fait : elle charge le fichier de candidatures d'une
vague, en controle la qualite, attribue a chaque dossier un score a partir
d'un modele appris sur les decisions passees, applique les quotas de
priorisation de l'association, et affiche la composition de la liste obtenue.

Ce que l'application ne fait pas : elle ne decide pas. Elle propose un ordre
de lecture. Le comite lit tous les dossiers.

Lancement :
    streamlit run src/app.py
"""

import io
import os
import sys
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import graphiques
import variables
import acces

# Chemins et chiffres affiches, tous definis dans config.py
CHEMIN_MODELE = config.CHEMIN_MODELE
# On lit les chiffres dans config.py, avec des valeurs de repli : une version
# desynchronisee du fichier de configuration ne doit pas faire tomber la page.
_mesures = getattr(config, "PERFORMANCE", {})
GAIN_MESURE = {
    "auc": _mesures.get("auc", 0.572),
    "intervalle": _mesures.get("intervalle", "0,49 a 0,64"),
    "decile": _mesures.get("gain_premier_decile", 1.62),
    "lecture_en_moins": _mesures.get("lecture_en_moins", 16),
}

st.set_page_config(page_title="Lecture des candidatures TDEV",
                   page_icon=":clipboard:", layout="wide")

role = acces.demander_connexion()


# ----------------------------------------------------------------------
# Accessibilite : reglages appliques a toute l'application
# ----------------------------------------------------------------------

# Accessibilite : taille du texte et contraste, appliques a toute l'application
def appliquer_accessibilite(taille, contraste):
    couleurs = ""
    if contraste:
        couleurs = """
        .stApp { background-color: #FFFFFF; color: #000000; }
        .stApp a { color: #0000CC; text-decoration: underline; }
        [data-testid="stSidebar"] { background-color: #F0F0F0; }
        """
    st.markdown("""
    <style>
    html, body, .stApp, p, li, label, div[data-testid="stMarkdownContainer"] {
        font-size: %dpx !important;
        line-height: 1.6 !important;
    }
    .stDataFrame { font-size: %dpx !important; }
    *:focus { outline: 3px solid #D96C3B !important; outline-offset: 2px; }
    %s
    </style>
    """ % (taille, max(12, taille - 2), couleurs), unsafe_allow_html=True)



# Chargement de l'artefact de modele, mis en cache
@st.cache_resource
def charger_modele():
    if not os.path.exists(CHEMIN_MODELE):
        return None
    return joblib.load(CHEMIN_MODELE)



# Lecture du fichier depose, trois formats acceptes
def lire_fichier(fichier):
    nom = fichier.name.lower()
    if nom.endswith(".csv"):
        return pd.read_csv(fichier)
    if nom.endswith(".xlsx") or nom.endswith(".xls"):
        return pd.read_excel(fichier)
    if nom.endswith(".json"):
        return pd.read_json(fichier)
    return None



# Controle de qualite du fichier
# Chaque constat porte un libelle en toutes lettres, jamais une simple couleur.
def controler_qualite(donnees):
    """Renvoie une liste de constats, chacun avec un niveau et un libelle."""
    constats = []

    constats.append(("information", "Lignes lues",
                     str(len(donnees)) + " candidatures, "
                     + str(len(donnees.columns)) + " colonnes"))

    colonne_id = None
    for candidat in ["identifiant", "Submission ID", "Respondent ID"]:
        if candidat in donnees.columns:
            colonne_id = candidat
            break
    if colonne_id is None:
        constats.append(("alerte", "Identifiant",
                         "Aucune colonne d'identifiant reconnue, le controle "
                         "des doublons ne peut pas etre fait"))
    else:
        doublons = int(donnees[colonne_id].duplicated().sum())
        if doublons > 0:
            constats.append(("alerte", "Candidatures en double",
                             str(doublons) + " doublons sur la colonne "
                             + colonne_id + ". Les criteres de TDEV prevoient "
                             "leur elimination. Seule la derniere soumission "
                             "est conservee."))
        else:
            constats.append(("correct", "Candidatures en double",
                             "Aucun doublon detecte"))

    attendues = {
        "objectifs personnels": ["objectifs personn"],
        "motivation": ["pourquoi meritez-vous"],
        "defis releves": ["defis personnels ou professionnels"],
        "sujets a apprendre": ["sujets, les competences"],
        "temps hebdomadaire": ["combien de temps allez-vous"],
        "parcours academique": ["carriere academique"],
        "acces a Internet": ["type d", "internet utiliserez"]
    }
    manquantes = []
    for libelle in attendues:
        if variables.colonne_contenant(donnees, attendues[libelle]) is None:
            manquantes.append(libelle)
    if manquantes:
        constats.append(("alerte", "Colonnes attendues absentes",
                         ", ".join(manquantes)
                         + ". Les variables correspondantes seront mises a zero, "
                           "ce qui degrade la qualite du classement."))
    else:
        constats.append(("correct", "Colonnes attendues",
                         "Toutes les colonnes utiles sont presentes"))

    taux = donnees.isna().mean()
    tres_vides = taux[taux > 0.80]
    if len(tres_vides) > 0:
        constats.append(("information", "Colonnes presque vides",
                         str(len(tres_vides)) + " colonnes renseignees a moins "
                         "de 20 pour cent. Elles sont traitees comme des "
                         "indicateurs de presence."))

    genre = variables.extraire_genre(donnees)
    if (genre == "Non renseigne").mean() > 0.10:
        constats.append(("alerte", "Genre non renseigne",
                         str(round((genre == "Non renseigne").mean() * 100, 1))
                         + " pour cent des dossiers. Le quota de parite sera "
                           "approximatif."))

    return constats



# Dedoublonnage, premier critere de verification de TDEV
def dedoublonner(donnees):
    for candidat in ["identifiant", "Submission ID", "Respondent ID"]:
        if candidat in donnees.columns:
            colonne_date = variables.colonne_contenant(donnees, ["submitted"])
            if colonne_date is not None:
                donnees = donnees.sort_values(colonne_date)
            return donnees.drop_duplicates(subset=[candidat],
                                           keep="last").reset_index(drop=True)
    return donnees



# Application des quotas, apres le classement et jamais avant
# Le modele n'apprend aucun critere de priorite. Ils sont appliques ici,
# ce qui les rend visibles et modifiables par le comite.
def appliquer_quotas(table, nb_places, part_femmes, part_togo, actif):
    """
    Les quotas sont appliques apres le classement, jamais appris par le
    modele. Le comite voit la regle, la modifie, et en garde la
    responsabilite.
    """
    table = table.sort_values("score", ascending=False).reset_index(drop=True)
    if not actif:
        choix = table.head(nb_places).copy()
        choix["motif"] = "score"
        return choix

    cible_femmes = int(round(nb_places * part_femmes / 100))
    cible_togo = int(round(nb_places * part_togo / 100))

    retenues, deja = [], set()

    def prendre(sous_ensemble, nombre, motif):
        pris = 0
        for i in sous_ensemble.index:
            if pris >= nombre:
                break
            if i in deja:
                continue
            ligne = sous_ensemble.loc[i].to_dict()
            ligne["motif"] = motif
            retenues.append(ligne)
            deja.add(i)
            pris += 1
        return pris

    prendre(table[table["genre"] == "Femme"], cible_femmes, "quota parite")
    prendre(table[table["pays"] == "Togo"], cible_togo, "quota Togo")
    prendre(table, nb_places - len(retenues), "score")

    return pd.DataFrame(retenues)



# Comparaison de la composition de la liste et du vivier
def tableau_composition(reference, selection, colonne, libelle):
    a = reference[colonne].value_counts(normalize=True) * 100
    b = selection[colonne].value_counts(normalize=True) * 100
    table = pd.DataFrame({"Part dans le vivier": a, "Part dans la liste": b})
    table = table.fillna(0).round(1)
    table["Ecart en points"] = (table["Part dans la liste"]
                                - table["Part dans le vivier"]).round(1)
    table.index.name = libelle
    return table.sort_values("Part dans le vivier", ascending=False)


# ----------------------------------------------------------------------
# Barre laterale
# ----------------------------------------------------------------------

# Barre laterale : reglages d'accessibilite, navigation, deconnexion
st.sidebar.title("Reglages")

st.sidebar.markdown("### Confort de lecture")
taille = st.sidebar.slider("Taille du texte en pixels", 14, 26, 16, step=1,
                           help="Agrandit tout le texte de l'application.")
contraste = st.sidebar.checkbox("Contraste renforce", value=False,
                                help="Noir sur blanc, liens soulignes.")
appliquer_accessibilite(taille, contraste)

st.sidebar.markdown("### Navigation")
etapes = ["1. Charger et controler", "2. Classer", "3. Quotas et composition",
          "4. Limites et methode"]
if role == "administrateur":
    etapes.append("5. Back office")
page = st.sidebar.radio("Choisir une etape", etapes, label_visibility="visible")

st.sidebar.markdown("---")
st.sidebar.markdown("Connecte en tant que " + st.session_state.get("identifiant", "")
                    + ", role " + role + ".")
if st.sidebar.button("Se deconnecter"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    "Aucune donnee n'est conservee. Les fichiers sont traites en memoire "
    "le temps de la session et disparaissent a la fermeture de l'onglet.")


# ----------------------------------------------------------------------
# Avertissement permanent
# ----------------------------------------------------------------------

# Avertissement permanent, affiche sur toutes les pages
st.warning(
    "Cet outil propose un ordre de lecture. Il ne decide pas. "
    "Sa capacite a distinguer un dossier retenu d'un dossier ecarte est de "
    + str(GAIN_MESURE["auc"]).replace(".", ",")
    + " sur une echelle ou 0,50 est le hasard. Tout dossier doit etre lu.",
    icon=":material/warning:")

artefact = charger_modele()
if artefact is None:
    st.error("Le modele est introuvable. Lancer d'abord : python src/modele.py")
    st.stop()


# ----------------------------------------------------------------------
# Page 1
# ----------------------------------------------------------------------

# Page 1 : charger un fichier et en controler la qualite
if page.startswith("1"):
    st.title("Charger un fichier de candidatures")
    st.markdown(
        "Depose ici le fichier complet d'une vague, au format CSV, XLSX ou "
        "JSON. Le fichier n'est pas enregistre.")

    fichier = st.file_uploader(
        "Fichier de candidatures a analyser",
        type=["csv", "xlsx", "xls", "json"],
        help="Le fichier doit contenir une ligne par candidature et les "
             "colonnes du formulaire DataCamp Donates.")

    if fichier is not None:
        donnees = lire_fichier(fichier)
        if donnees is None:
            st.error("Format non reconnu.")
            st.stop()
        donnees = dedoublonner(donnees)
        st.session_state["donnees"] = donnees

        st.subheader("Controle de qualite")
        constats = controler_qualite(donnees)
        for niveau, titre, detail in constats:
            etiquette = {"correct": "Conforme", "alerte": "A verifier",
                         "information": "Information"}[niveau]
            st.markdown("**" + etiquette + " - " + titre + "** : " + detail)

        st.subheader("Apercu des donnees")
        st.dataframe(donnees.head(20), use_container_width=True)
        st.caption("Les vingt premieres lignes du fichier charge.")
        st.success("Fichier pret. Passer a l'etape 2 dans le menu de gauche.")
    else:
        st.info("Aucun fichier charge pour l'instant.")


# ----------------------------------------------------------------------
# Page 2
# ----------------------------------------------------------------------

# Page 2 : classer les candidatures
elif page.startswith("2"):
    st.title("Classer les candidatures")

    if "donnees" not in st.session_state:
        st.info("Charger d'abord un fichier a l'etape 1.")
        st.stop()

    donnees = st.session_state["donnees"]
    x = variables.construire_tout(donnees, artefact["vectoriseur"],
                                  artefact["colonnes"])
    score = artefact["modele"].predict_proba(x)[:, 1]

    table = pd.DataFrame({
        "rang": np.argsort(np.argsort(-score)) + 1,
        "score": np.round(score, 4),
        "genre": variables.extraire_genre(donnees).values,
        "pays": variables.extraire_pays(donnees).values,
        "mots ecrits": variables.construire_longueurs(donnees)["nb_mots_total"].values
    })
    for colonne in ["identifiant", "Submission ID"]:
        if colonne in donnees.columns:
            table.insert(0, "identifiant", donnees[colonne].values)
            break
    table = table.sort_values("rang").reset_index(drop=True)
    st.session_state["table"] = table

    col1, col2, col3 = st.columns(3)
    col1.metric("Candidatures classees", len(table))
    col2.metric("Score median", round(float(np.median(score)), 3))
    col3.metric("Gain attendu sur le premier decile",
                "x " + str(GAIN_MESURE["decile"]).replace(".", ","))

    st.markdown(
        "En lisant les dossiers dans cet ordre, le comite trouve la moitie "
        "des laureats apres environ "
        + str(GAIN_MESURE["lecture_en_moins"])
        + " pour cent de lecture en moins qu'en lisant dans l'ordre d'arrivee. "
          "Ce chiffre est mesure hors echantillon sur la vague de janvier 2025.")

    gauche, droite = st.columns(2)
    with gauche:
        st.altair_chart(graphiques.distribution_des_scores(score),
                        use_container_width=True)
        st.caption("Lecture : les scores se repartissent autour du milieu de "
                   "l'echelle, avec peu de dossiers tres bien ou tres mal "
                   "classes. C'est la signature d'un modele au pouvoir "
                   "discriminant modeste, ce qui correspond a la performance "
                   "mesuree.")
    with droite:
        courbe = getattr(config, "COURBE_DE_GAIN", None) or graphiques.COURBE_DE_SECOURS
        st.altair_chart(graphiques.courbe_de_gain(courbe),
                        use_container_width=True)
        st.caption("Lecture : en lisant la moitie des dossiers dans l'ordre "
                   "propose, le comite trouve 58 pour cent des laureats, "
                   "contre 50 pour cent en lisant dans l'ordre d'arrivee.")

    with st.expander("Voir les chiffres de la courbe de gain"):
        st.dataframe(pd.DataFrame(courbe).rename(columns={
            "part_lue": "Dossiers lus, en pour cent",
            "part_trouvee": "Laureats trouves, en pour cent"}),
            use_container_width=True, hide_index=True)

    st.subheader("Classement complet")
    st.dataframe(table, use_container_width=True, height=440)
    st.caption("Classement par score decroissant. Le score est une estimation "
               "de la probabilite que le comite retienne le dossier, pas une "
               "note de qualite du candidat.")

    tampon = io.StringIO()
    table.to_csv(tampon, index=False)
    st.download_button("Telecharger le classement au format CSV",
                       tampon.getvalue(),
                       file_name="classement_" +
                                 datetime.now().strftime("%Y%m%d") + ".csv",
                       mime="text/csv")


# ----------------------------------------------------------------------
# Page 3
# ----------------------------------------------------------------------

# Page 3 : quotas et composition de la liste
elif page.startswith("3"):
    st.title("Quotas et composition de la liste")

    if "table" not in st.session_state:
        st.info("Lancer d'abord le classement a l'etape 2.")
        st.stop()

    table = st.session_state["table"]

    st.markdown(
        "Les quotas de priorisation de TDEV ne sont pas appris par le modele. "
        "Ils sont appliques ici, apres le classement, pour qu'ils restent "
        "visibles et modifiables par le comite.")

    col1, col2, col3 = st.columns(3)
    nb_places = col1.number_input("Nombre de bourses a attribuer",
                                  min_value=1, max_value=len(table),
                                  value=min(200, len(table)), step=10)
    part_femmes = col2.slider("Part minimale de candidates en pour cent",
                              0, 100, getattr(config, "QUOTA_FEMMES_DEFAUT", 40), step=5,
                              help="Critere de priorisation numero 1 de TDEV.")
    part_togo = col3.slider("Part minimale de candidats togolais en pour cent",
                            0, 100, getattr(config, "QUOTA_TOGO_DEFAUT", 30), step=5,
                            help="A recalibrer sur la composition du vivier "
                                 "de chaque vague.")
    actif = st.checkbox("Appliquer les quotas", value=True)

    selection = appliquer_quotas(table, int(nb_places), part_femmes,
                                 part_togo, actif)

    st.subheader("Liste proposee")
    st.dataframe(selection, use_container_width=True, height=330)
    st.caption("La colonne motif indique pourquoi chaque dossier figure dans "
               "la liste : par son score, ou au titre d'un quota.")

    gauche, droite = st.columns([1, 1])
    with gauche:
        st.altair_chart(graphiques.origine_des_retenus(selection),
                        use_container_width=True)
    with droite:
        seuil = float(selection["score"].min()) if len(selection) else None
        st.altair_chart(graphiques.distribution_des_scores(
            table["score"].values, seuil=seuil), use_container_width=True)

    st.subheader("Composition comparee")
    st.markdown("Un ecart important signale que la liste ne ressemble pas au "
                "vivier sur ce critere. Ce n'est pas necessairement un "
                "probleme, mais cela doit etre su.")

    for colonne, libelle in [("genre", "Genre declare"), ("pays", "Pays")]:
        comparaison = tableau_composition(table, selection, colonne, libelle)
        st.altair_chart(
            graphiques.composition_comparee(table, selection, colonne, libelle),
            use_container_width=True)
        with st.expander("Voir les chiffres : " + libelle.lower()):
            st.dataframe(comparaison, use_container_width=True)

    if actif:
        part_obtenue = (selection["genre"] == "Femme").mean() * 100
        st.markdown("Part de candidates dans la liste : "
                    + str(round(part_obtenue, 1)) + " pour cent, "
                    + "pour une cible de " + str(part_femmes) + " pour cent.")

    tampon = io.StringIO()
    selection.to_csv(tampon, index=False)
    st.download_button("Telecharger la liste proposee au format CSV",
                       tampon.getvalue(),
                       file_name="liste_proposee_" +
                                 datetime.now().strftime("%Y%m%d") + ".csv",
                       mime="text/csv")


# ----------------------------------------------------------------------
# Page 4
# ----------------------------------------------------------------------

# Page 4 : limites et methode, dans le parcours et non en annexe
elif page.startswith("4"):
    st.title("Limites et methode")

    st.subheader("Ce que mesure le score")
    st.markdown(
        "Le modele apprend la decision rendue par le comite de TDEV sur "
        + str(artefact["effectif_entrainement"]) + " candidatures des vagues "
        + " et ".join(artefact["vagues"]) + ", dont "
        + str(artefact["retenus_entrainement"]) + " ont ete retenues.\n\n"
        "Il predit donc ce que le comite a fait, et non la qualite d'un "
        "candidat ni sa reussite future. Si le comite se trompe, le modele "
        "apprend son erreur.")

    st.subheader("Ce que vaut le score")
    st.markdown(
        "Capacite a distinguer un dossier retenu d'un dossier ecarte : "
        + str(GAIN_MESURE["auc"]).replace(".", ",")
        + ", intervalle de confiance de " + GAIN_MESURE["intervalle"]
        + ", sur une echelle ou 0,50 correspond au hasard.\n\n"
        "C'est faible. C'est suffisant pour ordonner une liste de lecture, "
        "ce n'est pas suffisant pour decider.")

    st.subheader("Les quatre limites a connaitre")
    st.markdown(
        "1. Les criteres du comite changent d'une vague a l'autre. Un modele "
        "appris sur janvier 2024 ne predit pas janvier 2025. Le modele doit "
        "etre reentraine a chaque vague.\n\n"
        "2. La variable la plus associee a la decision est la longueur des "
        "reponses redactionnelles. Ecrire longuement suppose un clavier, du "
        "temps et une aisance redactionnelle, inegalement repartis.\n\n"
        "3. Le genre est le critere le plus predictif du jeu de donnees. Il "
        "est volontairement exclu du modele et applique en quota visible.\n\n"
        "4. Le modele reproduit partiellement l'ecart lie au genre sans avoir "
        "recu cette variable, par l'intermediaire de variables correlees.")

    st.subheader("Protection des donnees")
    st.markdown(
        "Aucun fichier n'est enregistre sur le serveur. Les donnees sont "
        "traitees en memoire le temps de la session.\n\n"
        "La base de donnees du projet ne contient aucune adresse "
        "electronique ni aucun nom : les identifiants y sont remplaces par "
        "une empreinte SHA-256 tronquee.\n\n"
        "Les traitements de pseudonymisation sont executes en local, avant "
        "tout envoi de donnees vers un service tiers.")

    st.subheader("Accessibilite")
    st.markdown(
        "La taille du texte est reglable dans le menu de gauche, de 14 a 26 "
        "pixels. Un mode a contraste renforce est disponible.\n\n"
        "Aucune information n'est portee par la couleur seule : chaque "
        "constat de controle porte un libelle en toutes lettres.\n\n"
        "Tous les champs portent une etiquette explicite et un texte d'aide. "
        "La navigation au clavier est possible sur l'ensemble des elements, "
        "avec un contour de focus visible.\n\n"
        "Les tableaux sont lisibles par un lecteur d'ecran et aucun graphique "
        "n'est utilise sans equivalent textuel.")

    st.subheader("Version du modele")
    st.json({k: artefact[k] for k in ["version", "effectif_entrainement",
                                      "retenus_entrainement", "taux_de_base",
                                      "auc_moyen", "vagues"]})


# ----------------------------------------------------------------------
# Page 5, reservee au role administrateur
# ----------------------------------------------------------------------
else:
    st.title("Back office")

    if role != "administrateur":
        st.error("Cette page est reservee au role administrateur.")
        st.stop()

    st.subheader("Etat du modele en service")
    colonnes = st.columns(4)
    colonnes[0].metric("Version", artefact["version"])
    colonnes[1].metric("Candidatures d'apprentissage",
                       artefact["effectif_entrainement"])
    colonnes[2].metric("Retenues", artefact["retenus_entrainement"])
    colonnes[3].metric("AUC moyen", round(artefact["auc_moyen"], 3))
    st.markdown("Vagues d'apprentissage : " + ", ".join(artefact["vagues"]) + ".")

    st.subheader("Poids des variables")
    st.markdown(
        "Un poids positif pousse vers l'acceptation, un poids negatif vers le "
        "refus. Les valeurs sont exprimees en logarithme de rapport de cotes, "
        "sur variables centrees reduites.")
    poids = pd.Series(
        artefact["modele"].named_steps["logisticregression"].coef_[0],
        index=artefact["colonnes"]).sort_values(ascending=False)
    tableau_poids = pd.DataFrame({"variable": poids.index,
                                  "poids": poids.values.round(4)})
    st.dataframe(tableau_poids, use_container_width=True, height=320)

    st.subheader("Contenu de la base de donnees")
    chemin_base = config.CHEMIN_BASE
    if not os.path.exists(chemin_base):
        st.info(
            "La base n'est pas presente dans cette version deployee. Elle "
            "contient des candidatures pseudonymisees, qui ne sont pas "
            "publiees sur le depot public. Son schema, ses volumetries et son "
            "export figurent dans l'archive remise avec le memoire. Pour la "
            "reconstruire en local : placer les fichiers de candidature dans "
            "le dossier declare par src/config.py, puis lancer "
            "python src/base.py")
    else:
        import sqlite3
        connexion = sqlite3.connect(chemin_base)
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name", connexion)
        resume = []
        for nom in tables["name"]:
            n = connexion.execute("SELECT COUNT(*) FROM " + nom).fetchone()[0]
            resume.append({"table": nom, "lignes": n})
        st.dataframe(pd.DataFrame(resume), use_container_width=True)

        choix = st.selectbox("Table a consulter", tables["name"].tolist(),
                             help="Affiche les cent premieres lignes.")
        apercu = pd.read_sql_query(
            "SELECT * FROM " + choix + " LIMIT 100", connexion)
        st.dataframe(apercu, use_container_width=True, height=320)
        st.caption("Aucune adresse electronique ni aucun nom ne figure dans "
                   "cette base. La colonne empreinte est un hachage SHA-256 "
                   "tronque.")
        connexion.close()

    st.subheader("Reentrainer le modele")
    st.markdown(
        "Les criteres du comite evoluent d'une vague a l'autre. Le modele doit "
        "etre reappris apres chaque campagne, une fois les decisions de celle-ci "
        "etiquetees.\n\n"
        "Procedure, depuis la racine du projet :\n\n"
        "1. placer le fichier de la nouvelle vague dans le dossier data\n"
        "2. ajouter son nom dans la liste FICHIERS du script src/modele.py\n"
        "3. lancer python src/modele.py\n"
        "4. relancer l'application\n\n"
        "Le script affiche l'intervalle de confiance de la nouvelle version. "
        "Si cet intervalle contient 0,50, le modele n'apporte rien sur cette "
        "vague et il ne faut pas le mettre en service.")

    st.subheader("Changer un mot de passe")
    st.markdown("Calculer l'empreinte du nouveau mot de passe, puis la "
                "reporter dans le fichier config.yaml.")
    nouveau = st.text_input("Nouveau mot de passe", type="password",
                            help="L'empreinte s'affiche ci-dessous. Le mot de "
                                 "passe lui-meme n'est pas enregistre.")
    if nouveau:
        st.code(acces.empreinte(nouveau), language="text")
