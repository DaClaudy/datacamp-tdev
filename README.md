# Aide a la lecture des candidatures DataCamp Donates

Outil d'aide a la decision pour le programme de bourses DataCamp Donates de
TDEV, Lome, Togo.

Projet de these professionnelle, Mastere Data et Intelligence Artificielle,
Nexa Digital School. Damigou Boundja, octobre 2026.

---

## Ce que fait l'application

TDEV recoit un contingent limite de licences DataCamp et le redistribue par
vagues de recrutement. En janvier 2025, mille quarante-neuf candidatures ont
ete deposees pour cent quatre-vingt-onze bourses. Le comite lit tous les
dossiers a la main.

L'application charge le fichier de candidatures d'une vague, en controle la
qualite, attribue a chaque dossier un score issu d'un modele appris sur les
decisions passees du comite, applique les quotas de priorisation de
l'association, et affiche la composition de la liste obtenue.

Elle propose un ordre de lecture. Elle ne decide pas.

### Ce qu'elle ne fait pas

- Elle ne rend pas de verdict sur un candidat.
- Elle ne remplace pas la lecture du comite.
- Elle ne se reutilise pas d'une vague a l'autre sans reentrainement.
- Elle ne conserve aucune donnee personnelle.

### Performance mesuree

Capacite a distinguer un dossier retenu d'un dossier ecarte : 0,572 sur une
echelle ou 0,50 correspond au hasard. Intervalle de confiance a 95 pour cent
de 0,49 a 0,64.

En mode classement, sur la vague de janvier 2025, mesure hors echantillon :

| Dossiers lus | Part du vivier | Laureats trouves | Precision | Gain |
|---|---|---|---|---|
| 104 | 10 % | 31 sur 191 | 29,8 % | x 1,62 |
| 207 | 20 % | 47 sur 191 | 22,7 % | x 1,23 |
| 311 | 30 % | 71 sur 191 | 22,8 % | x 1,24 |
| 518 | 50 % | 111 sur 191 | 21,4 % | x 1,16 |

Pour identifier la moitie des laureats, le comite lit 435 dossiers au lieu de
518, soit seize pour cent de lecture en moins.

---

## Aucune donnee de candidature dans ce depot

Les fichiers de candidature comportent des donnees a caractere personnel, dont
certaines relevent de categories sensibles : situation de handicap, statut de
refugie, situation financiere. La regle tenue pendant tout le projet est que
ces donnees ne quittent pas le poste de travail.

Ce depot contient donc le code et le modele deja entraine, et rien d'autre.
Le modele est un fichier de coefficients : il ne permet pas de reconstituer
une candidature.

Pour essayer l'application, un fichier de demonstration entierement fictif est
fourni dans `exemple/exemple_candidatures.csv`. Soixante candidatures
inventees, assemblees a partir d'un vocabulaire fixe, qui respectent la
structure du questionnaire DataCamp Donates. Aucune ne correspond a une
personne reelle.

---

## Essayer l'application

Identifiants de demonstration :

| Identifiant | Mot de passe | Role |
|---|---|---|
| `lecteur` | `tdev2026` | etapes 1 a 4 |
| `admin` | `adminTDEV2026` | etapes 1 a 5, dont le back office |

Une fois connecte, depose `exemple/exemple_candidatures.csv` a l'etape 1, puis
suis le menu de gauche.

Ces identifiants sont des identifiants de recette. Ils doivent etre changes
avant toute mise en service reelle. Les mots de passe ne sont pas stockes en
clair : `config.yaml` ne contient que leur empreinte SHA-256.

---

## Installation en local

Prerequis : Python 3.10 ou superieur.

```
python -m venv venv
source venv/bin/activate        # sous Windows : venv\Scripts\activate
pip install -r requirements.txt
streamlit run src/app.py
```

L'application est disponible sur http://localhost:8501

### Reconstruire le modele

Le reentrainement suppose de disposer des fichiers de candidature etiquetes,
qui ne figurent pas dans ce depot.

1. Placer les fichiers pseudonymises dans un dossier `data/` a la racine, ou
   declarer le bon dossier dans `DOSSIERS_DONNEES`, fichier `src/config.py`.
2. Lancer `python src/base.py` pour construire la base.
3. Lancer `python src/modele.py` pour reentrainer et reecrire l'artefact.

Le script affiche l'intervalle de confiance de la version produite. S'il
contient 0,50, le modele n'apporte rien sur cette vague et ne doit pas etre
mis en service.

---

## Structure du code

| Fichier | Role |
|---|---|
| `src/config.py` | constantes et chemins, seul fichier a modifier si les donnees changent de place |
| `src/variables.py` | construction des 94 variables, partage entre l'analyse et l'application |
| `src/modele.py` | entrainement, evaluation selon trois protocoles, ecriture de l'artefact |
| `src/utilite_reelle.py` | mesure du gain dans la condition reelle d'emploi |
| `src/base.py` | schema SQLite, chargement, mesure de l'indexation, export |
| `src/acces.py` | authentification et roles |
| `src/app.py` | application en cinq pages |
| `src/exemple.py` | fabrique le fichier de demonstration fictif |

`variables.py` est partage entre l'entrainement et l'application. C'est
volontaire : si l'application construisait ses variables autrement que le
script d'entrainement, le modele recevrait des colonnes ne correspondant pas a
ce qu'il a appris, et les scores seraient faux sans qu'aucune erreur ne soit
levee.

---

## Accessibilite

- Taille du texte reglable de 14 a 26 pixels depuis la barre laterale.
- Mode a contraste renforce.
- Aucune information portee par la couleur seule : chaque constat du controle
  de qualite porte un libelle en toutes lettres.
- Etiquettes et textes d'aide sur tous les champs de saisie.
- Navigation au clavier avec contour de focus visible.
- Resultats presentes en tableaux, lisibles par un lecteur d'ecran et
  exportables.
- Mise en page verifiee jusqu'a 393 pixels de large.

L'application n'a pas ete testee avec un lecteur d'ecran reel ni aupres
d'utilisateurs en situation de handicap. Ce test reste a conduire.

---

## Limites connues

1. Les criteres du comite changent d'une vague a l'autre. Un modele appris sur
   janvier 2024 ne predit pas janvier 2025. Reentrainement obligatoire a
   chaque campagne.
2. La variable la plus associee a la decision est la longueur des reponses
   redactionnelles. Ecrire longuement suppose un clavier, du temps et une
   aisance redactionnelle, inegalement repartis dans la population visee. Ce
   risque de discrimination indirecte est documente, il n'est pas resolu.
3. Le genre est le critere le plus predictif du jeu de donnees. Il est
   volontairement exclu du modele et applique sous forme de quota visible. Le
   modele en reconstitue neanmoins une partie par des variables correlees.
4. Le quota geographique par defaut est fixe a trente pour cent et non a la
   valeur historique de cinquante-cinq pour cent, calibree sur un vivier qui a
   change de composition. Cette valeur doit etre recalibree a chaque vague.
5. L'effectif d'apprentissage est de 1 246 candidatures pour 273 retenues.
   C'est peu. Tout ecart de performance inferieur a cinq points est a
   considerer comme non etabli.
