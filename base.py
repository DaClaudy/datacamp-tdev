# base.py - Mise en base de donnees et mesure de l'effet de l'indexation
"""
Mise en base de donnees des candidatures et mesure de l'effet de l'indexation.

Choix du moteur : SQLite. La base doit pouvoir etre transmise dans une archive
et rejouee par un tiers sans installation de serveur. Le volume en jeu, de
l'ordre du millier de lignes, ne justifie aucune architecture distribuee.

Protection des donnees : aucune adresse electronique n'est stockee en clair.
La base ne contient que son empreinte SHA-256 tronquee, deja calculee lors de
la pseudonymisation. L'export SQL livre dans l'archive ne contient donc aucun
identifiant direct.

    python src/base.py
"""

import hashlib
import os
import sqlite3
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import variables

CHEMIN_BASE = config.CHEMIN_BASE
CHEMIN_DUMP = config.CHEMIN_DUMP
NB_REPETITIONS = 200
FACTEUR_VOLUME = 50


# Schema de la base : quatre tables
SCHEMA = """
DROP TABLE IF EXISTS resultat_modele;
DROP TABLE IF EXISTS candidature;
DROP TABLE IF EXISTS membre;
DROP TABLE IF EXISTS vague;

CREATE TABLE vague (
    id_vague        INTEGER PRIMARY KEY,
    libelle         TEXT NOT NULL UNIQUE,
    annee           INTEGER NOT NULL,
    formulaire      TEXT NOT NULL,
    role_protocole  TEXT NOT NULL
);

CREATE TABLE candidature (
    id_candidature  INTEGER PRIMARY KEY,
    id_vague        INTEGER NOT NULL REFERENCES vague(id_vague),
    empreinte       TEXT NOT NULL,
    age             REAL,
    pays            TEXT,
    genre           TEXT,
    niveau_ds       REAL,
    temps_hebdo     INTEGER,
    temoignage      INTEGER,
    parents_niveau  INTEGER,
    nb_mots_total   INTEGER,
    nb_mots_merite  INTEGER,
    doc_justificatif INTEGER,
    retenu          INTEGER NOT NULL
);

CREATE TABLE membre (
    id_membre       INTEGER PRIMARY KEY,
    empreinte       TEXT NOT NULL,
    equipe          TEXT,
    date_export     TEXT
);

CREATE TABLE resultat_modele (
    id_resultat     INTEGER PRIMARY KEY,
    id_candidature  INTEGER NOT NULL REFERENCES candidature(id_candidature),
    version_modele  TEXT NOT NULL,
    score           REAL NOT NULL,
    rang            INTEGER,
    date_execution  TEXT NOT NULL
);
"""


# Requete dont on mesure le temps d'execution
# C'est la plus frequente : elle joint les candidatures aux membres.
REQUETE_MESUREE = """
SELECT v.libelle,
       COUNT(DISTINCT c.id_candidature) AS candidatures,
       SUM(c.retenu) AS retenues,
       COUNT(m.id_membre) AS correspondances
FROM candidature c
JOIN vague v ON v.id_vague = c.id_vague
LEFT JOIN membre m ON m.empreinte = c.empreinte
GROUP BY v.libelle
"""



# Fonctions utilitaires
def empreinte(texte):
    return hashlib.sha256(str(texte).encode("utf-8")).hexdigest()[:16]


def charger_candidatures():
    chemins = config.verifier_donnees()
    libelles = ["janvier 2024", "janvier 2025"]
    morceaux = []
    for libelle, chemin in zip(libelles, chemins):
        bloc = pd.read_csv(chemin)
        bloc["vague"] = libelle
        morceaux.append(bloc)
    commun = set(morceaux[0].columns)
    for bloc in morceaux[1:]:
        commun = commun & set(bloc.columns)
    commun = [c for c in morceaux[0].columns if c in commun]
    donnees = pd.concat([b[commun] for b in morceaux], ignore_index=True)
    colonne_date = variables.colonne_contenant(donnees, ["submitted"])
    donnees = donnees.sort_values(colonne_date)
    donnees = donnees.drop_duplicates(subset=["vague", "identifiant"], keep="last")
    return donnees.reset_index(drop=True)


def mesurer(connexion, repetitions):
    debut = time.perf_counter()
    for _ in range(repetitions):
        connexion.execute(REQUETE_MESUREE).fetchall()
    return (time.perf_counter() - debut) / repetitions * 1000



# Etape 1 : creation de la base et chargement
print("=" * 70)
print("MISE EN BASE ET MESURE DE L'INDEXATION")
print("=" * 70)

if not os.path.exists(config.DOSSIER_SQL):
    os.makedirs(config.DOSSIER_SQL)
if os.path.exists(CHEMIN_BASE):
    os.remove(CHEMIN_BASE)

connexion = sqlite3.connect(CHEMIN_BASE)
connexion.executescript(SCHEMA)

donnees = charger_candidatures()
structurelles = variables.construire_structurelles(donnees)
longueurs = variables.construire_longueurs(donnees)
genre = variables.extraire_genre(donnees)
pays = variables.extraire_pays(donnees)

vagues = [("janvier 2024", 2024, "DataCamp Donates", "apprentissage"),
          ("janvier 2025", 2025, "DataCamp Donates", "test hors-temps")]
for i, v in enumerate(vagues, start=1):
    connexion.execute(
        "INSERT INTO vague (id_vague, libelle, annee, formulaire, role_protocole)"
        " VALUES (?, ?, ?, ?, ?)", (i,) + v)
index_vague = {v[0]: i for i, v in enumerate(vagues, start=1)}

lignes = []
for i in range(len(donnees)):
    lignes.append((
        i + 1,
        index_vague[donnees["vague"].iloc[i]],
        str(donnees["identifiant"].iloc[i]),
        float(structurelles["age"].iloc[i]),
        str(pays.iloc[i]),
        str(genre.iloc[i]),
        float(structurelles["niveau_datascience"].iloc[i]),
        int(structurelles["temps_hebdo"].iloc[i]),
        int(structurelles["temoignage"].iloc[i]),
        int(structurelles["parents_niveau"].iloc[i]),
        int(longueurs["nb_mots_total"].iloc[i]),
        int(longueurs["nb_mots_merite"].iloc[i]),
        int(structurelles["doc_justificatif"].iloc[i]),
        int(donnees["cible_selectionne"].iloc[i])))
connexion.executemany(
    "INSERT INTO candidature VALUES (" + ",".join(["?"] * 14) + ")", lignes)

# Table membre : les empreintes des candidats retenus, qui sont ceux
# effectivement inscrits sur la plateforme.
membres = [(i + 1, l[2], "equipe " + str(l[1]), "2026-05-26")
           for i, l in enumerate(lignes) if l[13] == 1]
connexion.executemany("INSERT INTO membre VALUES (?, ?, ?, ?)", membres)
connexion.commit()

print("\nTables chargees")
for table in ["vague", "candidature", "membre", "resultat_modele"]:
    n = connexion.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
    print("  " + table.ljust(18), str(n).rjust(6), "lignes")

print("\nAffichage par defaut des tables, cinq premieres lignes de candidature :")
apercu = pd.read_sql_query(
    "SELECT id_candidature, id_vague, substr(empreinte,1,8) AS empreinte,"
    " age, pays, nb_mots_total, retenu FROM candidature LIMIT 5", connexion)
print(apercu.to_string(index=False))



# Etape 2 : mesure au volume reel, avec et sans index
print("\n" + "-" * 70)
print("MESURE AU VOLUME REEL")
print("-" * 70)
connexion.execute("DROP INDEX IF EXISTS idx_candidature_empreinte")
connexion.execute("DROP INDEX IF EXISTS idx_membre_empreinte")
sans = mesurer(connexion, NB_REPETITIONS)
connexion.execute("CREATE INDEX idx_candidature_empreinte ON candidature(empreinte)")
connexion.execute("CREATE INDEX idx_membre_empreinte ON membre(empreinte)")
connexion.execute("ANALYZE")
avec = mesurer(connexion, NB_REPETITIONS)
print("  sans index :", round(sans, 3), "ms")
print("  avec index :", round(avec, 3), "ms")
print("  rapport    : x", round(sans / avec, 2) if avec > 0 else "n/a")

print("\n" + "-" * 70)
print("MESURE SUR UN VOLUME MULTIPLIE PAR", FACTEUR_VOLUME)
print("-" * 70)
print("Les lignes sont repliquees en suffixant l'empreinte du numero de")
print("replique des deux cotes de la jointure, ce qui conserve la selectivite")
print("et evite une explosion combinatoire qui fausserait la mesure.")


# Etape 3 : mesure sur un volume multiplie par cinquante
# L'interet d'un index depend du volume. Ne presenter que le cas favorable
# reviendrait a choisir la mesure qui arrange.
connexion.execute("DROP INDEX IF EXISTS idx_candidature_empreinte")
connexion.execute("DROP INDEX IF EXISTS idx_membre_empreinte")

suivant = len(lignes)
gros_c, gros_m = [], []
for r in range(1, FACTEUR_VOLUME):
    for l in lignes:
        suivant += 1
        gros_c.append((suivant, l[1], l[2] + "r" + str(r)) + l[3:])
suivant_m = len(membres)
for r in range(1, FACTEUR_VOLUME):
    for m in membres:
        suivant_m += 1
        gros_m.append((suivant_m + 1000000, m[1] + "r" + str(r), m[2], m[3]))
connexion.executemany(
    "INSERT INTO candidature VALUES (" + ",".join(["?"] * 14) + ")", gros_c)
connexion.executemany("INSERT INTO membre VALUES (?, ?, ?, ?)", gros_m)
connexion.commit()

n_c = connexion.execute("SELECT COUNT(*) FROM candidature").fetchone()[0]
n_m = connexion.execute("SELECT COUNT(*) FROM membre").fetchone()[0]
print("\n  candidature :", n_c, "lignes   membre :", n_m, "lignes")

sans_gros = mesurer(connexion, 20)
connexion.execute("CREATE INDEX idx_candidature_empreinte ON candidature(empreinte)")
connexion.execute("CREATE INDEX idx_membre_empreinte ON membre(empreinte)")
connexion.execute("ANALYZE")
avec_gros = mesurer(connexion, 20)
print("  sans index :", round(sans_gros, 3), "ms")
print("  avec index :", round(avec_gros, 3), "ms")
print("  rapport    : x", round(sans_gros / avec_gros, 2) if avec_gros > 0 else "n/a")

print("\nPlan d'execution avec index :")
for ligne in connexion.execute("EXPLAIN QUERY PLAN " + REQUETE_MESUREE).fetchall():
    print("   ", ligne[-1])

print("\n" + "-" * 70)
print("TABLEAU A REPORTER DANS LE MEMOIRE")
print("-" * 70)
print("  " + "volume".ljust(26), "sans index".rjust(12), "avec index".rjust(12),
      "rapport".rjust(10))
print("  " + ("reel, " + str(len(lignes)) + " candidatures").ljust(26),
      (str(round(sans, 3)) + " ms").rjust(12), (str(round(avec, 3)) + " ms").rjust(12),
      ("x" + str(round(sans / avec, 2))).rjust(10))
print("  " + ("x50, " + str(n_c) + " candidatures").ljust(26),
      (str(round(sans_gros, 3)) + " ms").rjust(12),
      (str(round(avec_gros, 3)) + " ms").rjust(12),
      ("x" + str(round(sans_gros / avec_gros, 2))).rjust(10))

# On retire les lignes de test de volume avant l'export
connexion.execute("DELETE FROM candidature WHERE id_candidature > ?", (len(lignes),))
connexion.execute("DELETE FROM membre WHERE id_membre > 1000000")
connexion.commit()
connexion.isolation_level = None
connexion.execute("VACUUM")
connexion.isolation_level = ""


# Etape 4 : export SQL, sans aucun identifiant direct
with open(CHEMIN_DUMP, "w", encoding="utf-8") as f:
    f.write("-- Export de la base du projet TDEV DataCamp Donates\n")
    f.write("-- Aucune adresse electronique ni nom ne figure dans cet export.\n")
    f.write("-- La colonne empreinte contient un hachage SHA-256 tronque.\n\n")
    for ligne in connexion.iterdump():
        f.write(ligne + "\n")

connexion.close()
print("\nBase ecrite :", CHEMIN_BASE)
print("Export SQL  :", CHEMIN_DUMP)
