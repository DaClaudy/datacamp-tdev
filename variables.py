# variables.py - Construction des variables a partir d'un fichier de candidatures
"""
Construction des variables a partir d'un fichier de candidatures brut.

Ce module est partage entre l'entrainement du modele et l'application. C'est
volontaire : si l'application construisait ses variables autrement que le
script d'entrainement, le modele recevrait des colonnes qui ne correspondent
pas a ce qu'il a appris, et les scores seraient faux sans qu'aucune erreur ne
soit levee. Un seul endroit, une seule definition.

Le genre n'est jamais construit comme variable explicative. Il est renvoye a
part, pour l'audit d'equite et pour l'application des quotas.
"""

import re
import unicodedata

import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer


# Mots vides francais
# Sans cette liste, les termes les plus influents du modele sont des
# articles et des pronoms, ce qui n'apprend rien.
MOTS_VIDES = """au aux avec ce ces dans de des du elle en et eux il je la le
leur lui ma mais me meme mes moi mon ne nos notre nous on ou par pas pour qu
que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous c d j l
a m n s t y ete etee etees etes etant suis es est sommes etes sont serai seras
sera serons serez seront avoir avais avait avions aviez avaient eu ai as avons
avez ont plus tres bien aussi cette comme donc alors car tout tous toute toutes
afin ainsi deja encore faire fait meme non oui si sans sous entre apres avant
cela celui ceux chaque leurs autre autres etre""".split()


# Pays retenus comme variables, les autres sont regroupes
PAYS_PRINCIPAUX = ["Togo", "Benin", "Cote d Ivoire", "Senegal", "Maroc",
                   "Burkina Faso", "Cameroun", "Congo"]


# Correspondance ville vers pays
# Le champ de residence est en saisie libre : un candidat togolais peut
# ecrire Lome, Lome Togo, ou Togo. Sans cette table, il compte pour trois.
VILLES_VERS_PAYS = {
    "lome": "Togo", "kara": "Togo", "sokode": "Togo", "atakpame": "Togo",
    "kpalime": "Togo", "tsevie": "Togo", "aneho": "Togo", "dapaong": "Togo",
    "cotonou": "Benin", "porto novo": "Benin", "parakou": "Benin",
    "abomey": "Benin", "bohicon": "Benin", "natitingou": "Benin",
    "abidjan": "Cote d Ivoire", "yamoussoukro": "Cote d Ivoire",
    "bouake": "Cote d Ivoire", "daloa": "Cote d Ivoire",
    "dakar": "Senegal", "thies": "Senegal", "saint louis": "Senegal",
    "casablanca": "Maroc", "rabat": "Maroc", "marrakech": "Maroc",
    "fes": "Maroc", "agadir": "Maroc", "tanger": "Maroc",
    "ouagadougou": "Burkina Faso", "bobo dioulasso": "Burkina Faso",
    "douala": "Cameroun", "yaounde": "Cameroun", "bafoussam": "Cameroun",
    "brazzaville": "Congo", "pointe noire": "Congo",
    "kinshasa": "RDC", "lubumbashi": "RDC", "goma": "RDC", "bukavu": "RDC",
    "ndjamena": "Tchad", "niamey": "Niger", "bamako": "Mali",
    "conakry": "Guinee", "libreville": "Gabon", "paris": "France",
    "lyon": "France", "marseille": "France", "montreal": "Canada"
}


# Echelles de conversion des reponses ordinales en nombres
ECHELLE_ACADEMIQUE = {
    "premiere annee de licence": 1, "deuxieme annee de licence": 2,
    "troisieme annee de licence": 3, "quatrieme annee de licence": 4,
    "etudiant diplome": 5, "ancien eleve/non inscrit": 0
}

ECHELLE_TEMPS = {"<1 heure/semaine": 1, "1-2 heures/semaine": 2,
                 "3-5 heures/semaine": 3, ">5 heures/semaine": 4}

ECHELLE_TEMOIGNAGE = {"non": 0, "peut-etre": 1, "oui": 2}


# Niveau d'etudes des parents, du plus eleve au plus bas
NIVEAUX_PARENTS = [(["doctorat"], 6), (["ma, ms"], 5), (["licence (ba"], 4),
                   (["d'associe"], 3), (["enseignement secondaire"], 2),
                   (["aucun de ces diplomes"], 1)]


# Les quatre questions redactionnelles du formulaire
CHAMPS_LIBRES = {
    "sujets": ["sujets, les competences"],
    "objectifs": ["objectifs personn"],
    "merite": ["pourquoi meritez-vous"],
    "defis": ["defis personnels ou professionnels"]
}



# Fonctions utilitaires
def sans_accent(texte):
    forme = unicodedata.normalize("NFKD", str(texte))
    return "".join(c for c in forme if not unicodedata.combining(c))


def cle(texte):
    return re.sub(r"[^a-z0-9]+", "_", sans_accent(texte).lower()).strip("_")


def colonne_contenant(donnees, morceaux):
    """Retrouve une colonne par des fragments de son libelle."""
    for nom in donnees.columns:
        reference = sans_accent(nom).lower()
        if all(sans_accent(m).lower() in reference for m in morceaux):
            return nom
    return None


def binaire(serie):
    return serie.astype(str).str.lower().isin(["true", "1", "oui", "1.0"]).astype(int)



# Nettoyage du champ de residence
def deduire_pays(valeur):
    """Les candidats saisissent librement leur residence. On ramene au pays."""
    if valeur is None or (isinstance(valeur, float) and np.isnan(valeur)):
        return "Inconnu"
    texte = sans_accent(valeur).lower().strip()
    for morceau in re.split(r"[,/;|-]", texte):
        morceau = morceau.strip()
        if morceau in VILLES_VERS_PAYS:
            return VILLES_VERS_PAYS[morceau]
    for ville in VILLES_VERS_PAYS:
        if ville in texte:
            return VILLES_VERS_PAYS[ville]
    for pays in PAYS_PRINCIPAUX + ["RDC", "France", "Tchad", "Niger", "Mali"]:
        if sans_accent(pays).lower() in texte:
            return pays
    return "Autre"



# Le genre est renvoye a part, jamais comme variable du modele
# Il sert a l'audit d'equite et a l'application des quotas.
def extraire_genre(donnees):
    """Renvoye a part, jamais comme variable du modele."""
    nom = colonne_contenant(donnees, ["options vous decrit le mieux"])
    if nom is None:
        return pd.Series("Non renseigne", index=donnees.index)
    return donnees[nom].fillna("Non renseigne")


def extraire_pays(donnees):
    if "pays" in donnees.columns:
        return donnees["pays"].fillna("Inconnu")
    nom = colonne_contenant(donnees, ["ville"])
    if nom is None:
        nom = colonne_contenant(donnees, ["residence"])
    if nom is None:
        return pd.Series("Inconnu", index=donnees.index)
    return donnees[nom].map(deduire_pays)



# Famille 1 : les variables structurelles, 41 au total
def construire_structurelles(donnees):
    x = pd.DataFrame(index=donnees.index)

    if "age" in donnees.columns:
        age = pd.to_numeric(donnees["age"], errors="coerce")
    else:
        nom = colonne_contenant(donnees, ["date de naissance"])
        if nom is not None:
            naissance = pd.to_datetime(donnees[nom], errors="coerce")
            age = (pd.Timestamp("today") - naissance).dt.days / 365.25
        else:
            age = pd.Series(np.nan, index=donnees.index)
    mediane = age.median()
    x["age"] = age.fillna(mediane if not pd.isna(mediane) else 23.0)

    situations = {
        "sans_emploi": ["cases qui s", "(sans emploi)"],
        "sous_emploi": ["cases qui s", "sous-employe"],
        "sous_seuil_pauvrete": ["cases qui s", "seuil de pauvrete"],
        "refugie": ["cases qui s", "refugie"],
        "handicap_ou_defavorise": ["cases qui s", "handicapee"],
        "etudiant_16_26": ["cases qui s", "16 a 26"],
        "donnees_env_sante": ["cases qui s", "environnement et la sante"],
        "aucune_categorie": ["cases qui s", "aucune de ces categories"]
    }
    noms = []
    for c in situations:
        nom = colonne_contenant(donnees, situations[c])
        x["sit_" + c] = binaire(donnees[nom]) if nom else 0
        noms.append("sit_" + c)
    x["sit_nombre"] = x[noms].sum(axis=1)

    nom = colonne_contenant(donnees, ["telecharger ici tout document"])
    x["doc_justificatif"] = donnees[nom].notna().astype(int) if nom else 0

    nom = colonne_contenant(donnees, ["type d", "internet utiliserez"])
    internet = donnees[nom].fillna("Non renseigne") if nom else pd.Series(
        "Non renseigne", index=donnees.index)
    for valeur in ["Mon propre Internet", "Wi-Fi public/ecole", "Donnees mobiles",
                   "Internet d'un ami", "Je ne suis pas sur"]:
        x["net_" + cle(valeur)[:22]] = (
            internet.map(sans_accent) == sans_accent(valeur)).astype(int)

    appareils = {
        "ordi_propre": ["allez-vous utiliser datacamp", "(mon propre ordinateur)"],
        "ordi_partage": ["allez-vous utiliser datacamp", "emprunte/partage"],
        "mobile": ["allez-vous utiliser datacamp", "appareil mobile ios"],
        "appareil_autre": ["allez-vous utiliser datacamp", "? (autre)"]
    }
    noms = []
    for c in appareils:
        nom = colonne_contenant(donnees, appareils[c])
        x["app_" + c] = binaire(donnees[nom]) if nom else 0
        noms.append("app_" + c)
    x["app_nombre"] = x[noms].sum(axis=1)

    nom = colonne_contenant(donnees, ["deja suivi un cours ou une piste"])
    x["deja_datacamp"] = donnees[nom].notna().astype(int) if nom else 0
    nom = colonne_contenant(donnees, ["titre du poste"])
    x["a_un_poste"] = donnees[nom].notna().astype(int) if nom else 0
    nom = colonne_contenant(donnees, ["employeur (si vous"])
    x["a_un_employeur"] = donnees[nom].notna().astype(int) if nom else 0

    nom = colonne_contenant(donnees, ["carriere academique"])
    if nom is not None:
        niveau = donnees[nom].fillna("").map(
            lambda v: ECHELLE_ACADEMIQUE.get(sans_accent(v).lower().strip(), np.nan))
        x["avancement_academique"] = niveau.fillna(3)
    else:
        x["avancement_academique"] = 3

    nom = colonne_contenant(donnees, ["types d", "aide financiere dont vous"])
    aide = donnees[nom].fillna("") if nom else pd.Series("", index=donnees.index)
    x["aide_aucune"] = aide.map(lambda v: 1 if "aucun" in sans_accent(v).lower() else 0)
    x["aide_nombre"] = aide.map(
        lambda v: 0 if ("aucun" in sans_accent(v).lower() or v == "")
        else len(str(v).split(",")))
    nom = colonne_contenant(donnees, ["plus d", "informations sur votre aide"])
    x["aide_commentaire"] = donnees[nom].notna().astype(int) if nom else 0

    parents = pd.Series(0, index=donnees.index)
    for motifs, valeur in NIVEAUX_PARENTS:
        nom = colonne_contenant(donnees, ["niveau d", "vos parents"] + motifs[:1])
        if nom is not None:
            parents = np.maximum(parents, binaire(donnees[nom]) * valeur)
    x["parents_niveau"] = parents

    nom = colonne_contenant(donnees, ["echelle de 1 a 5"])
    if nom is not None:
        niveau = pd.to_numeric(donnees[nom], errors="coerce")
        x["niveau_datascience"] = niveau.fillna(niveau.median() if niveau.notna().any() else 2)
    else:
        x["niveau_datascience"] = 2

    nom = colonne_contenant(donnees, ["combien de temps allez-vous"])
    if nom is not None:
        temps = donnees[nom].fillna("").map(
            lambda v: ECHELLE_TEMPS.get(str(v).strip(), np.nan))
        x["temps_hebdo"] = temps.fillna(3)
    else:
        x["temps_hebdo"] = 3

    nom = colonne_contenant(donnees, ["temoignage de 3 a 5 phrases"])
    if nom is not None:
        t = donnees[nom].fillna("").map(
            lambda v: ECHELLE_TEMOIGNAGE.get(sans_accent(v).lower().strip(), np.nan))
        x["temoignage"] = t.fillna(1)
    else:
        x["temoignage"] = 1

    pays = extraire_pays(donnees)
    for p in PAYS_PRINCIPAUX:
        x["pays_" + cle(p)] = (pays == p).astype(int)
    x["pays_autre"] = (~pays.isin(PAYS_PRINCIPAUX)).astype(int)

    return x



# Famille 2 : les longueurs des champs redactionnels, 13 au total
def construire_longueurs(donnees):
    x = pd.DataFrame(index=donnees.index)
    total = []
    for c in CHAMPS_LIBRES:
        nom = colonne_contenant(donnees, CHAMPS_LIBRES[c])
        contenu = donnees[nom].fillna("").astype(str) if nom else pd.Series(
            "", index=donnees.index)
        x["nb_car_" + c] = contenu.str.len()
        x["nb_mots_" + c] = contenu.str.split().map(len)
        x["vide_" + c] = (contenu.str.strip() == "").astype(int)
        total.append("nb_mots_" + c)
    x["nb_mots_total"] = x[total].sum(axis=1)
    return x



# Famille 3 : les variables lexicales TF-IDF, 40 au total
def corpus_textes(donnees):
    morceaux = []
    for c in CHAMPS_LIBRES:
        nom = colonne_contenant(donnees, CHAMPS_LIBRES[c])
        contenu = donnees[nom].fillna("").astype(str) if nom else pd.Series(
            "", index=donnees.index)
        morceaux.append(contenu)
    assemble = morceaux[0]
    for m in morceaux[1:]:
        assemble = assemble + " " + m
    return assemble.map(lambda t: sans_accent(t).lower())


def ajuster_tfidf(donnees, nb_termes=40, min_df=15):
    vectoriseur = TfidfVectorizer(max_features=nb_termes, min_df=min_df,
                                  stop_words=MOTS_VIDES, ngram_range=(1, 1))
    vectoriseur.fit(corpus_textes(donnees))
    return vectoriseur


def appliquer_tfidf(donnees, vectoriseur):
    matrice = vectoriseur.transform(corpus_textes(donnees))
    return pd.DataFrame(matrice.toarray(),
                        columns=["txt_" + m for m in vectoriseur.get_feature_names_out()],
                        index=donnees.index)



# Assemblage des trois familles
# L'alignement sur les colonnes attendues est indispensable : si le modele
# recoit des colonnes dans un autre ordre, les scores sont faux sans erreur.
def construire_tout(donnees, vectoriseur, colonnes_attendues=None):
    """Assemble les trois familles et aligne sur les colonnes du modele."""
    x = pd.concat([construire_structurelles(donnees),
                   construire_longueurs(donnees),
                   appliquer_tfidf(donnees, vectoriseur)], axis=1)
    if colonnes_attendues is not None:
        for c in colonnes_attendues:
            if c not in x.columns:
                x[c] = 0
        x = x[list(colonnes_attendues)]
    return x
