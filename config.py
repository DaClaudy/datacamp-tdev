# config.py - Constantes et chemins du projet
#
# Tout ce qui depend de l'endroit ou sont rangees les donnees est ici.
# Si tes fichiers de candidature changent de dossier, c'est le seul fichier
# a modifier.

import os


# Racine du projet
# Ce fichier est dans src/, la racine est donc le dossier parent.
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Dossiers ou chercher les fichiers de candidature
# Les chemins sont essayes dans l'ordre, le premier qui existe est retenu.
# Ajoute ici tes propres dossiers si tes donnees sont ailleurs.
DOSSIERS_DONNEES = [
    os.path.join(RACINE, "data"),
    os.path.join(RACINE, "donnees"),
    os.path.join(RACINE, "data_brutes"),
    os.path.join(RACINE, "..", "data"),
    os.path.join(RACINE, "..", "donnees"),
]


# Fichiers utilises pour l'entrainement
# Ce sont les deux vagues qui partagent le questionnaire DataCamp Donates.
FICHIERS_ENTRAINEMENT = [
    "anonymise_vague_janv24.csv",
    "anonymise_vague_janv25.csv",
]


# Autres dossiers du projet
DOSSIER_MODELE = os.path.join(RACINE, "modele")
DOSSIER_SQL = os.path.join(RACINE, "sql")
DOSSIER_SORTIES = os.path.join(RACINE, "sorties")


# Fichiers produits
CHEMIN_MODELE = os.path.join(DOSSIER_MODELE, "modele_selection.joblib")
CHEMIN_COEFFICIENTS = os.path.join(DOSSIER_MODELE, "coefficients.csv")
CHEMIN_RESUME = os.path.join(DOSSIER_MODELE, "resume.json")
CHEMIN_BASE = os.path.join(DOSSIER_SQL, "datacamp.db")
CHEMIN_DUMP = os.path.join(DOSSIER_SQL, "datacamp_dump.sql")


# Colonnes attendues dans les fichiers de candidature
COLONNE_CIBLE = "cible_selectionne"
COLONNE_IDENTIFIANT = "identifiant"


# Parametres du modele
GRAINE = 42                 # pour que deux executions donnent le meme resultat
PART_TEST = 0.30            # decoupage 70 / 30 exige par le guide
REGULARISATION = 0.5        # parametre C de la regression logistique
NB_TERMES_TFIDF = 40        # nombre de mots retenus dans les champs libres
FREQUENCE_MIN_TFIDF = 15    # un mot doit apparaitre dans au moins 15 dossiers


# Quotas de priorisation appliques apres le classement
# Ils ne sont jamais appris par le modele. Le comite les voit et les modifie.
QUOTA_FEMMES_DEFAUT = 40    # en pourcentage
QUOTA_TOGO_DEFAUT = 30      # en pourcentage, a recalibrer a chaque vague


# Performance mesuree en condition reelle d'emploi
# Vague de janvier 2025 seule, modele sans indicateur de vague.
# Ces chiffres sont affiches dans l'application, ils doivent rester a jour.
PERFORMANCE = {
    "auc": 0.572,
    "intervalle": "0,49 a 0,64",
    "gain_premier_decile": 1.62,
    "lecture_en_moins": 16,
}


def dossier_donnees():
    """Retourne le premier dossier de donnees qui existe."""
    for chemin in DOSSIERS_DONNEES:
        if os.path.isdir(chemin):
            return os.path.normpath(chemin)
    return os.path.normpath(DOSSIERS_DONNEES[0])


def chemin_fichier(nom):
    """Cherche un fichier de donnees dans tous les dossiers connus."""
    for dossier in DOSSIERS_DONNEES:
        chemin = os.path.join(dossier, nom)
        if os.path.exists(chemin):
            return os.path.normpath(chemin)
    return None


def fichiers_entrainement():
    """Retourne les chemins des fichiers d'entrainement trouves."""
    trouves = []
    manquants = []
    for nom in FICHIERS_ENTRAINEMENT:
        chemin = chemin_fichier(nom)
        if chemin is None:
            manquants.append(nom)
        else:
            trouves.append(chemin)
    return trouves, manquants


def verifier_donnees():
    """Affiche un diagnostic et arrete le script si des fichiers manquent."""
    trouves, manquants = fichiers_entrainement()
    if manquants:
        print("Fichiers de donnees introuvables :")
        for nom in manquants:
            print("   ", nom)
        print("\nDossiers explores :")
        for dossier in DOSSIERS_DONNEES:
            marque = "existe" if os.path.isdir(dossier) else "absent"
            print("   ", os.path.normpath(dossier), "(" + marque + ")")
        print("\nAjoute le bon dossier dans DOSSIERS_DONNEES, fichier src/config.py")
        raise SystemExit()
    return trouves
