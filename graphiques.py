# graphiques.py - Les visualisations de l'application
#
# Toutes les figures sont construites avec Altair, deja fourni par Streamlit.
# Trois regles tenues partout :
#   - une seule echelle par figure, jamais deux axes verticaux
#   - la couleur ne porte jamais seule l'information : chaque serie est aussi
#     nommee dans une legende et, quand c'est lisible, etiquetee directement
#   - chaque figure est accompagnee du tableau de chiffres correspondant, ce
#     qui la rend lisible par un lecteur d'ecran et verifiable

import altair as alt
import pandas as pd


# Palette
# Deux teintes seulement, validees pour la vision des couleurs et pour le
# contraste sur fond clair.
BLEU = "#2a78d6"        # ce que fait l'outil
ORANGE = "#eb6834"      # le point de comparaison
ENCRE = "#1b2a41"
GRIS = "#6b7785"
GRILLE = "#e4e7ec"

HAUTEUR = 260


def _base(figure, titre, sous_titre=None):
    """Habillage commun : titre, grille discrete, pas de cadre."""
    return figure.properties(
        height=HAUTEUR,
        title=alt.TitleParams(
            text=titre,
            subtitle=sous_titre or "",
            anchor="start",
            fontSize=15,
            subtitleFontSize=12,
            color=ENCRE,
            subtitleColor=GRIS,
            offset=12),
    ).configure_view(stroke=None).configure_axis(
        gridColor=GRILLE,
        domainColor=GRILLE,
        tickColor=GRILLE,
        labelColor=GRIS,
        titleColor=GRIS,
        labelFontSize=11,
        titleFontSize=11,
    ).configure_legend(
        labelColor=ENCRE, titleColor=GRIS, labelFontSize=12, titleFontSize=11,
        orient="top", direction="horizontal", offset=6, symbolType="square",
    )


# Figure 1 : comment les scores se repartissent
def distribution_des_scores(scores, seuil=None):
    """Histogramme des scores, avec le seuil de la liste retenue."""
    table = pd.DataFrame({"score": scores})

    barres = alt.Chart(table).mark_bar(
        color=BLEU, cornerRadiusTopLeft=3, cornerRadiusTopRight=3
    ).encode(
        x=alt.X("score:Q", bin=alt.Bin(maxbins=30),
                title="Score attribue par le modele"),
        y=alt.Y("count():Q", title="Nombre de candidatures"),
        tooltip=[alt.Tooltip("count():Q", title="Candidatures"),
                 alt.Tooltip("score:Q", bin=alt.Bin(maxbins=30), title="Score")],
    )

    if seuil is None:
        return _base(barres, "Repartition des scores",
                     "Chaque barre compte les candidatures d'un meme niveau de score")

    trait = alt.Chart(pd.DataFrame({"seuil": [seuil]})).mark_rule(
        color=ORANGE, strokeWidth=2, strokeDash=[5, 3]
    ).encode(x="seuil:Q")

    return _base(barres + trait, "Repartition des scores",
                 "Le trait orange marque le score du dernier dossier retenu")


# Figure 2 : ce que l'ordre de lecture fait gagner
def courbe_de_gain(courbe):
    """Part des laureats trouves selon la part de dossiers lus."""
    outil = pd.DataFrame(courbe)
    outil["lecture"] = "Dans l'ordre propose par l'outil"
    hasard = pd.DataFrame({"part_lue": [0, 100], "part_trouvee": [0, 100]})
    hasard["lecture"] = "Dans l'ordre d'arrivee"
    table = pd.concat([outil, hasard], ignore_index=True)

    couleurs = alt.Scale(
        domain=["Dans l'ordre propose par l'outil", "Dans l'ordre d'arrivee"],
        range=[BLEU, ORANGE])

    lignes = alt.Chart(table).mark_line(strokeWidth=2, point=False).encode(
        x=alt.X("part_lue:Q", title="Part des dossiers lus, en pour cent",
                scale=alt.Scale(domain=[0, 100], nice=False)),
        y=alt.Y("part_trouvee:Q", title="Part des laureats trouves, en pour cent",
                scale=alt.Scale(domain=[0, 100], nice=False)),
        color=alt.Color("lecture:N", scale=couleurs, title=None,
                        legend=alt.Legend(orient="top")),
        strokeDash=alt.StrokeDash(
            "lecture:N", title=None, legend=None,
            scale=alt.Scale(
                domain=["Dans l'ordre propose par l'outil",
                        "Dans l'ordre d'arrivee"],
                range=[[1, 0], [6, 4]])),
    )

    reperes = outil[outil["part_lue"].isin([10, 50])]
    points = alt.Chart(reperes).mark_point(
        size=70, filled=True, color=BLEU, stroke="white", strokeWidth=2
    ).encode(x="part_lue:Q", y="part_trouvee:Q",
             tooltip=[alt.Tooltip("part_lue:Q", title="Dossiers lus, %"),
                      alt.Tooltip("part_trouvee:Q", title="Laureats trouves, %")])

    textes = alt.Chart(reperes).mark_text(
        align="left", dx=8, dy=-8, color=ENCRE, fontSize=11
    ).encode(x="part_lue:Q", y="part_trouvee:Q",
             text=alt.Text("part_trouvee:Q", format=".0f"))

    return _base(lignes + points + textes,
                 "Ce que l'ordre de lecture fait gagner",
                 "Mesure hors echantillon sur la vague de janvier 2025")


# Figure 3 : la liste retenue ressemble-t-elle au vivier
def composition_comparee(table_vivier, table_liste, colonne, libelle, maximum=6):
    """Comparaison des parts, vivier contre liste proposee."""
    vivier = table_vivier[colonne].value_counts(normalize=True) * 100
    liste = table_liste[colonne].value_counts(normalize=True) * 100
    gardees = list(vivier.head(maximum).index)

    # une modalite absente des deux ensembles n'apporte rien a la lecture
    gardees = [m for m in gardees
               if float(vivier.get(m, 0)) > 0.4 or float(liste.get(m, 0)) > 0.4]

    lignes = []
    for modalite in gardees:
        lignes.append({"modalite": str(modalite), "ensemble": "Vivier complet",
                       "part": round(float(vivier.get(modalite, 0)), 1)})
        lignes.append({"modalite": str(modalite), "ensemble": "Liste proposee",
                       "part": round(float(liste.get(modalite, 0)), 1)})
    table = pd.DataFrame(lignes)

    couleurs = alt.Scale(domain=["Vivier complet", "Liste proposee"],
                         range=[GRIS, BLEU])

    barres = alt.Chart(table).mark_bar(
        cornerRadiusTopRight=3, cornerRadiusBottomRight=3
    ).encode(
        y=alt.Y("modalite:N", title=None, sort=gardees,
                axis=alt.Axis(labelLimit=180)),
        x=alt.X("part:Q", title="Part en pour cent"),
        yOffset=alt.YOffset("ensemble:N",
                            sort=["Vivier complet", "Liste proposee"]),
        color=alt.Color("ensemble:N", scale=couleurs, title=None,
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("modalite:N", title=libelle),
                 alt.Tooltip("ensemble:N", title="Ensemble"),
                 alt.Tooltip("part:Q", title="Part, %", format=".1f")],
    )

    valeurs = alt.Chart(table).mark_text(
        align="left", dx=4, fontSize=10, color=ENCRE
    ).encode(
        y=alt.Y("modalite:N", sort=gardees),
        x="part:Q",
        yOffset=alt.YOffset("ensemble:N",
                            sort=["Vivier complet", "Liste proposee"]),
        text=alt.Text("part:Q", format=".0f"),
    )

    hauteur = max(170, 42 * len(gardees))
    figure = (barres + valeurs).properties(height=hauteur)
    return _base(figure, "Composition comparee : " + libelle.lower(),
                 "Un ecart important ne signale pas une erreur, mais merite d'etre su")


# Figure 4 : d'ou viennent les dossiers de la liste
def origine_des_retenus(selection):
    """Repartition de la liste entre le score et les quotas."""
    comptes = selection["motif"].value_counts()
    table = pd.DataFrame({"motif": comptes.index.astype(str),
                          "nombre": comptes.values})
    table["part"] = (table["nombre"] / table["nombre"].sum() * 100).round(1)

    barres = alt.Chart(table).mark_bar(
        color=BLEU, cornerRadiusTopRight=3, cornerRadiusBottomRight=3
    ).encode(
        y=alt.Y("motif:N", title=None, sort="-x"),
        x=alt.X("nombre:Q", title="Nombre de dossiers"),
        tooltip=[alt.Tooltip("motif:N", title="Motif"),
                 alt.Tooltip("nombre:Q", title="Dossiers"),
                 alt.Tooltip("part:Q", title="Part, %", format=".1f")],
    )
    valeurs = alt.Chart(table).mark_text(
        align="left", dx=5, fontSize=11, color=ENCRE
    ).encode(y=alt.Y("motif:N", sort="-x"), x="nombre:Q", text="nombre:Q")

    figure = (barres + valeurs).properties(height=max(120, 46 * len(table)))
    return _base(figure, "Pourquoi chaque dossier figure dans la liste",
                 "Par son score, ou au titre d'un quota de priorisation")
