# modele.py - Entrainement du modele et sauvegarde de l'artefact
"""
Entrainement du modele de classement et sauvegarde de l'artefact utilise par
l'application.

Le modele apprend la decision d'attribution du comite de TDEV a partir des
informations du dossier de candidature. Il ne recoit ni le genre ni
l'indicateur de vague : le premier parce qu'un critere de priorite doit rester
applique explicitement et non appris, le second parce qu'une nouvelle vague
n'en a pas.

    python src/modele.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import variables

GRAINE = config.GRAINE



# Chargement des deux vagues et dedoublonnage
def charger():
    chemins = config.verifier_donnees()
    morceaux = []
    for chemin in chemins:
        bloc = pd.read_csv(chemin)
        nom = os.path.basename(chemin)
        bloc["vague"] = nom.replace("anonymise_vague_", "").replace(".csv", "")
        morceaux.append(bloc)
    commun = set(morceaux[0].columns)
    for bloc in morceaux[1:]:
        commun = commun & set(bloc.columns)
    commun = [c for c in morceaux[0].columns if c in commun]
    donnees = pd.concat([b[commun] for b in morceaux], ignore_index=True)

    colonne_date = variables.colonne_contenant(donnees, ["submitted"])
    if colonne_date is not None:
        donnees = donnees.sort_values(colonne_date)
    avant = len(donnees)
    donnees = donnees.drop_duplicates(subset=["vague", "identifiant"], keep="last")
    donnees = donnees.reset_index(drop=True)
    print("Candidatures en double supprimees :", avant - len(donnees))
    return donnees



# Etape 1 : les donnees
print("=" * 66)
print("ENTRAINEMENT DU MODELE DE CLASSEMENT")
print("=" * 66)

donnees = charger()
y = donnees["cible_selectionne"].astype(int)
print("\nEffectif :", len(donnees), " retenus :", int(y.sum()),
      "(" + str(round(y.mean() * 100, 1)) + " %)")


# Etape 2 : les variables
# Ni le genre ni l'indicateur de vague ne sont construits ici.
vectoriseur = variables.ajuster_tfidf(donnees)
x = variables.construire_tout(donnees, vectoriseur)
print("Variables construites :", x.shape[1])
print("Le genre et l'indicateur de vague ne figurent pas dans cette liste.")


# Etape 3 : le modele
# Regression logistique reguliere, classes ponderees pour compenser le
# desequilibre entre retenus et non retenus.
modele = make_pipeline(StandardScaler(),
                       LogisticRegression(max_iter=4000, C=0.5,
                                          class_weight="balanced",
                                          random_state=GRAINE))

print("\n" + "-" * 66)
print("EVALUATION")
print("-" * 66)


# Evaluation 1 : decoupage 70 / 30, exige par le guide
x_train, x_test, y_train, y_test = train_test_split(
    x, y, test_size=config.PART_TEST, stratify=y, random_state=GRAINE)
modele.fit(x_train, y_train)
proba_test = modele.predict_proba(x_test)[:, 1]
print("Decoupage 70/30, test sur", len(y_test), "candidatures")
print("  AUC    :", round(roc_auc_score(y_test, proba_test), 3))
print("  AUC-PR :", round(average_precision_score(y_test, proba_test), 3))


# Evaluation 2 : validation croisee repetee, pour l'intervalle de confiance
decoupage = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=GRAINE)
scores = cross_val_score(modele, x, y, cv=decoupage, scoring="roc_auc", n_jobs=-1)
bas, haut = np.percentile(scores, 2.5), np.percentile(scores, 97.5)
print("\nValidation croisee repetee, 25 estimations")
print("  AUC moyen :", round(scores.mean(), 3),
      " intervalle a 95 % : [", round(bas, 3), ";", round(haut, 3), "]")
if bas > 0.5:
    print("  L'intervalle exclut 0.5 : le signal est reel.")
else:
    print("  L'intervalle contient 0.5 : prudence dans l'interpretation.")

print("\n" + "-" * 66)
print("UTILITE EN MODE CLASSEMENT")
print("-" * 66)

# Evaluation 3 : utilite en mode classement
# Chaque candidature est notee par un modele qui ne l'a pas vue.
proba_hors = np.zeros(len(y))
for itrain, itest in StratifiedKFold(5, shuffle=True, random_state=GRAINE).split(x, y):
    m = make_pipeline(StandardScaler(),
                      LogisticRegression(max_iter=4000, C=0.5,
                                         class_weight="balanced",
                                         random_state=GRAINE))
    m.fit(x.iloc[itrain], y.iloc[itrain])
    proba_hors[itest] = m.predict_proba(x.iloc[itest])[:, 1]

ordre = np.argsort(-proba_hors)
y_classe = y.values[ordre]
print("  " + "lus".rjust(6), "part".rjust(8), "trouves".rjust(10),
      "precision".rjust(11), "gain".rjust(7))
for part in [0.10, 0.20, 0.30, 0.50]:
    k = int(round(len(y) * part))
    trouves = int(y_classe[:k].sum())
    print("  " + str(k).rjust(6), (str(round(part * 100)) + " %").rjust(8),
          (str(trouves) + "/" + str(int(y.sum()))).rjust(10),
          (str(round(trouves / k * 100, 1)) + " %").rjust(11),
          ("x" + str(round(trouves / (y.mean() * k), 2))).rjust(7))

cumul = np.cumsum(y_classe)
moitie = int(np.argmax(cumul >= y.sum() / 2) + 1)
print("\n  Moitie des laureats trouvee en lisant", moitie, "dossiers au lieu de",
      int(round(len(y) / 2)))

print("\n" + "-" * 66)
print("REENTRAINEMENT SUR LA TOTALITE ET SAUVEGARDE")
print("-" * 66)

# Reentrainement sur la totalite avant sauvegarde
modele.fit(x, y)

if not os.path.exists(config.DOSSIER_MODELE):
    os.makedirs(config.DOSSIER_MODELE)

artefact = {
    "modele": modele,
    "vectoriseur": vectoriseur,
    "colonnes": list(x.columns),
    "taux_de_base": float(y.mean()),
    "effectif_entrainement": int(len(y)),
    "retenus_entrainement": int(y.sum()),
    "auc_moyen": float(scores.mean()),
    "auc_bas": float(bas),
    "auc_haut": float(haut),
    "vagues": sorted(donnees["vague"].unique().tolist()),
    "version": "1.0"
}
joblib.dump(artefact, config.CHEMIN_MODELE)

coefficients = pd.Series(modele.named_steps["logisticregression"].coef_[0],
                         index=x.columns).sort_values(ascending=False)
coefficients.to_csv(config.CHEMIN_COEFFICIENTS, header=["poids"])

resume = {k: artefact[k] for k in ["taux_de_base", "effectif_entrainement",
                                   "retenus_entrainement", "auc_moyen",
                                   "auc_bas", "auc_haut", "vagues", "version"]}
with open(config.CHEMIN_RESUME, "w") as f:
    json.dump(resume, f, indent=2)

print("Artefact ecrit : modele/modele_selection.joblib")
print("Coefficients   : modele/coefficients.csv")
print("Resume         : modele/resume.json")

print("\nVariables qui poussent le plus vers l'acceptation :")
for nom, valeur in coefficients.head(8).items():
    print("   ", nom.ljust(28), round(valeur, 3))
print("\nVariables qui poussent le plus vers le refus :")
for nom, valeur in coefficients.tail(8)[::-1].items():
    print("   ", nom.ljust(28), round(valeur, 3))
