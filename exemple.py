# exemple.py - Fabrique un fichier de candidatures fictif
#
# Le depot public ne contient aucune donnee reelle. Ce script produit un
# fichier de demonstration qui respecte exactement la structure du
# questionnaire DataCamp Donates, avec des reponses inventees, afin que
# l'application puisse etre essayee sans exposer personne.
#
#     python src/exemple.py

import os
import random
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

GRAINE = 7
NB_LIGNES = 60


# Vocabulaire utilise pour fabriquer les reponses redactionnelles
DEBUTS = ["Je souhaite", "Mon objectif est de", "J'aimerais", "Je veux"]
VERBES = ["apprendre", "maitriser", "approfondir", "decouvrir", "consolider"]
SUJETS = ["Python", "SQL", "la visualisation de donnees", "l'apprentissage automatique",
          "Power BI", "les statistiques", "l'analyse de donnees", "les bases de donnees"]
SUITES = ["pour changer de metier", "afin de trouver un emploi dans la donnee",
          "pour aider mon organisation a mieux decider",
          "parce que mon pays manque de competences techniques",
          "pour accompagner les petites entreprises de ma ville",
          "afin de poursuivre mes etudes dans ce domaine"]
DEFIS = ["J'ai finance mes etudes en travaillant le soir",
         "J'ai appris a programmer seul, sans ordinateur personnel",
         "J'ai repris mes etudes apres deux ans d'interruption",
         "Je partage une connexion avec cinq personnes",
         "J'ai monte un petit club informatique dans mon quartier",
         "J'ai du quitter ma region pour continuer a etudier"]

PAYS = ["Togo", "Benin", "Cote d Ivoire", "Senegal", "Maroc", "Burkina Faso",
        "Cameroun", "Congo", "RDC", "Tchad"]


def phrase(aleatoire, nb_morceaux):
    """Assemble une reponse redactionnelle de longueur variable."""
    morceaux = []
    for _ in range(nb_morceaux):
        morceaux.append(aleatoire.choice(DEBUTS) + " " + aleatoire.choice(VERBES)
                        + " " + aleatoire.choice(SUJETS) + " "
                        + aleatoire.choice(SUITES) + ".")
    return " ".join(morceaux)


def fabriquer():
    aleatoire = random.Random(GRAINE)
    lignes = []

    for i in range(NB_LIGNES):
        # longueur de reponse variable, c'est la variable la plus discriminante
        ampleur = aleatoire.choice([1, 1, 2, 2, 2, 3, 4])
        sans_emploi = aleatoire.random() < 0.40
        etudiant = aleatoire.random() < 0.65

        lignes.append({
            "Submission ID": "DEMO" + str(1000 + i),
            "Respondent ID": "R" + str(2000 + i),
            "Submitted at": "2026-01-" + str(aleatoire.randint(10, 28)).zfill(2),
            "Laquelle de ces options vous décrit le mieux ?":
                aleatoire.choice(["Homme", "Homme", "Homme", "Femme"]),
            " Comment décririez-vous votre situation actuelle ? Veuillez cocher "
            "TOUTES les cases qui s'appliquent. (Sans emploi)": sans_emploi,
            " Comment décririez-vous votre situation actuelle ? Veuillez cocher "
            "TOUTES les cases qui s'appliquent. (Sous-employé (salaire trop bas, "
            "pas assez d'heures, etc.))": aleatoire.random() < 0.25,
            " Comment décririez-vous votre situation actuelle ? Veuillez cocher "
            "TOUTES les cases qui s'appliquent. (Vivant sous le seuil de pauvreté "
            "national)": aleatoire.random() < 0.20,
            " Comment décririez-vous votre situation actuelle ? Veuillez cocher "
            "TOUTES les cases qui s'appliquent. (Réfugié de guerre et/ou de "
            "catastrophe environnementale)": aleatoire.random() < 0.03,
            " Comment décririez-vous votre situation actuelle ? Veuillez cocher "
            "TOUTES les cases qui s'appliquent. (Personne handicapée ou membre "
            "d'une communauté historiquement défavorisée)": aleatoire.random() < 0.08,
            " Comment décririez-vous votre situation actuelle ? Veuillez cocher "
            "TOUTES les cases qui s'appliquent. (Étudiant âgé de 16 à 26 ans)": etudiant,
            " Comment décririez-vous votre situation actuelle ? Veuillez cocher "
            "TOUTES les cases qui s'appliquent. (Professionnel travaillant avec "
            "des données sur l'environnement et la santé)": aleatoire.random() < 0.05,
            " Comment décririez-vous votre situation actuelle ? Veuillez cocher "
            "TOUTES les cases qui s'appliquent. (Aucune de ces catégories)":
                aleatoire.random() < 0.10,
            "Quel type d'Internet utiliserez-vous pour accéder à DataCamp ?":
                aleatoire.choice(["Mon propre Internet", "Mon propre Internet",
                                  "Wi-Fi public/école", "Données mobiles",
                                  "Internet d'un ami"]),
            "Sur quel(s) appareil(s) allez-vous utiliser DataCamp ? "
            "(Mon propre ordinateur)": aleatoire.random() < 0.75,
            "Sur quel(s) appareil(s) allez-vous utiliser DataCamp ? "
            "(Un ordinateur emprunté/partagé)": aleatoire.random() < 0.15,
            "Sur quel(s) appareil(s) allez-vous utiliser DataCamp ? "
            "(Mon propre appareil mobile iOS/Android)": aleatoire.random() < 0.35,
            "Sur quel(s) appareil(s) allez-vous utiliser DataCamp ? (Autre)":
                aleatoire.random() < 0.02,
            "Avez-vous déjà suivi un cours ou une piste sur DataCamp ? Si oui, "
            "veuillez télécharger votre certificat.":
                "certificat_demo.pdf" if aleatoire.random() < 0.05 else None,
            "Vous pouvez télécharger ici tout document ou matériel justifiant "
            "le(s) statut(s) que vous avez sélectionné(s).":
                "justificatif_demo.pdf" if aleatoire.random() < 0.38 else None,
            "Titre du poste (si vous êtes actuellement employé)":
                aleatoire.choice(["Analyste junior", "Enseignant", "Stagiaire"])
                if not sans_emploi and aleatoire.random() < 0.5 else None,
            "Employeur (si vous êtes actuellement employé)":
                "Organisation de demonstration"
                if not sans_emploi and aleatoire.random() < 0.3 else None,
            "École actuelle (ou dernière école fréquentée)": "Universite de demonstration",
            "Où en êtes-vous dans votre carrière académique ?":
                aleatoire.choice(["Étudiant diplômé", "Troisième année de licence",
                                  "Deuxième année de licence", "quatrième année de licence",
                                  "première année de licence", "Ancien élève/non inscrit"]),
            "Veuillez cocher les types d'aide financière dont vous bénéficiez.":
                aleatoire.choice(["Aucun de ces types d'aide",
                                  "Aucun de ces types d'aide",
                                  "Bourse au mérite",
                                  "Aide financière / bourse fondée sur les besoins"]),
            "Vous pouvez fournir plus d'informations sur votre aide financière ici :":
                "Aucune aide" if aleatoire.random() < 0.25 else None,
            "Quel était le niveau d'études le plus élevé de vos parents ? "
            "(Diplôme d'études supérieures (doctorat, etc.))": aleatoire.random() < 0.04,
            "Quel était le niveau d'études le plus élevé de vos parents ? "
            "(Diplôme d'études supérieures (MA, MS, etc.))": aleatoire.random() < 0.12,
            "Quel était le niveau d'études le plus élevé de vos parents ? "
            "(Licence (BA, BS, BFA, etc.))": aleatoire.random() < 0.18,
            "Quel était le niveau d'études le plus élevé de vos parents ? "
            "(Diplôme d'associé)": aleatoire.random() < 0.03,
            "Quel était le niveau d'études le plus élevé de vos parents ? "
            "(Diplôme de l'enseignement secondaire)": aleatoire.random() < 0.26,
            "Quel était le niveau d'études le plus élevé de vos parents ? "
            "(Aucun de ces diplômes)": aleatoire.random() < 0.28,
            "Sur une échelle de 1 à 5, quelles sont vos connaissances en matière "
            "de science des données ?": aleatoire.choice([1, 2, 2, 3, 3, 4]),
            "Quels sont les sujets, les compétences et les technologies que vous "
            "voulez apprendre à DataCamp ?":
                ", ".join(aleatoire.sample(SUJETS, aleatoire.randint(1, 4))),
            "La bourse gratuite DataCamp Donates dure de 6 à 12 mois. Quels sont "
            "les objectifs personnels et professionnels que vous souhaitez "
            "atteindre ?": phrase(aleatoire, ampleur),
            "Pourquoi méritez-vous la bourse ?": phrase(aleatoire, ampleur + 1),
            "Quels défis personnels ou professionnels avez-vous relevés pour "
            "arriver là où vous êtes aujourd'hui ?":
                " ".join(aleatoire.sample(DEFIS, min(ampleur, len(DEFIS)))),
            "Combien de temps allez-vous consacrer à l'utilisation régulière "
            "de DataCamp ?": aleatoire.choice(["1-2 heures/semaine", "3-5 heures/semaine",
                                               "3-5 heures/semaine", ">5 heures/semaine"]),
            "Serez-vous en mesure de nous fournir, ainsi qu'à DataCamp, un "
            "témoignage de 3 à 5 phrases sur votre expérience ?":
                aleatoire.choice(["Oui", "Oui", "Oui", "Peut-être", "Non"]),
            "identifiant": "demo" + str(i).zfill(4),
            "age": round(aleatoire.uniform(18, 34), 1),
            "pays": aleatoire.choice(PAYS),
        })

    return pd.DataFrame(lignes)


dossier = os.path.join(config.RACINE, "exemple")
if not os.path.exists(dossier):
    os.makedirs(dossier)

table = fabriquer()
chemin = os.path.join(dossier, "exemple_candidatures.csv")
table.to_csv(chemin, index=False)

print("Fichier de demonstration ecrit :", chemin)
print("Lignes :", len(table), " Colonnes :", len(table.columns))
print("")
print("Aucune de ces candidatures ne correspond a une personne reelle.")
print("Les reponses sont assemblees a partir d'un vocabulaire fixe.")
print("Depose ce fichier dans l'application pour l'essayer.")
