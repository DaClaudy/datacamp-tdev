# utilite_reelle.py - Mesure du gain dans la condition reelle d'emploi
"""
L'analyse du memoire mesure la performance sur les deux vagues reunies, avec
un indicateur de vague parmi les variables. C'est legitime pour une analyse,
mais ce n'est pas la condition d'emploi de l'application : celle-ci classe les
candidatures d'une seule vague, et ne peut evidemment pas savoir de quelle
vague il s'agit puisqu'elle est nouvelle.

Ce script mesure donc l'utilite dans la condition reelle : un modele sans
indicateur de vague, et un classement calcule a l'interieur de chaque vague.

    python src/utilite_reelle.py
"""

import os
import sys

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import variables

GRAINE = config.GRAINE



# Chargement des donnees
def charger():
    chemins = config.verifier_donnees()
    a = pd.read_csv(chemins[0]); a["vague"] = "janv24"
    b = pd.read_csv(chemins[1]); b["vague"] = "janv25"
    com = [c for c in a.columns if c in set(b.columns)]
    d = pd.concat([a[com], b[com]], ignore_index=True)
    cd = variables.colonne_contenant(d, ["submitted"])
    d = d.sort_values(cd).drop_duplicates(subset=["vague", "identifiant"], keep="last")
    return d.reset_index(drop=True)


def nouveau_modele():
    return make_pipeline(StandardScaler(),
                         LogisticRegression(max_iter=4000, C=0.5,
                                            class_weight="balanced",
                                            random_state=GRAINE))


donnees = charger()
y = donnees["cible_selectionne"].astype(int)
vague = donnees["vague"]
vectoriseur = variables.ajuster_tfidf(donnees)
x = variables.construire_tout(donnees, vectoriseur)

print("=" * 72)
print("UTILITE DANS LA CONDITION REELLE D'EMPLOI")
print("=" * 72)
print("\nModele sans indicateur de vague.")
print("Probabilites calculees hors echantillon, classement a l'interieur de")
print("chaque vague, puisque c'est ainsi que l'application est utilisee.\n")


# Notation hors echantillon
# Chaque candidature est notee par un modele qui ne l'a jamais vue.
proba = np.zeros(len(y))
for itrain, itest in StratifiedKFold(5, shuffle=True, random_state=GRAINE).split(x, y):
    m = nouveau_modele()
    m.fit(x.iloc[itrain], y.iloc[itrain])
    proba[itest] = m.predict_proba(x.iloc[itest])[:, 1]


# Classement a l'interieur de chaque vague
# C'est ainsi que l'application est utilisee : une vague a la fois.
for v in sorted(vague.unique()) + ["ensemble"]:
    masque = np.ones(len(y), dtype=bool) if v == "ensemble" else (vague == v).values
    yv = y.values[masque]
    pv = proba[masque]
    if yv.sum() < 5:
        continue
    ordre = np.argsort(-pv)
    yc = yv[ordre]
    print("-" * 72)
    print(v, ":", len(yv), "candidatures,", int(yv.sum()), "retenues",
          "(" + str(round(yv.mean() * 100, 1)) + " %)")
    print("  AUC :", round(roc_auc_score(yv, pv), 3))
    print("  " + "lus".rjust(6), "part".rjust(7), "trouves".rjust(11),
          "precision".rjust(11), "gain".rjust(7))
    for part in [0.10, 0.20, 0.30, 0.50]:
        k = max(1, int(round(len(yv) * part)))
        trouves = int(yc[:k].sum())
        print("  " + str(k).rjust(6), (str(round(part * 100)) + " %").rjust(7),
              (str(trouves) + "/" + str(int(yv.sum()))).rjust(11),
              (str(round(trouves / k * 100, 1)) + " %").rjust(11),
              ("x" + str(round(trouves / (yv.mean() * k), 2))).rjust(7))
    cumul = np.cumsum(yc)
    moitie = int(np.argmax(cumul >= yv.sum() / 2) + 1)
    hasard = int(round(len(yv) / 2))
    print("  Moitie des laureats :", moitie, "dossiers lus au lieu de", hasard,
          "soit", str(round((1 - moitie / hasard) * 100, 1)) + " % de lecture en moins")

print("\n" + "=" * 72)
print("A RETENIR")
print("=" * 72)
print("Le gain annonce dans l'application doit etre celui mesure ici, et non")
print("celui de l'analyse du memoire qui beneficie de l'indicateur de vague.")
