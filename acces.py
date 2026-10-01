# acces.py - Authentification et gestion des deux roles
"""
Controle d'acces de l'application.

Deux roles. Le role lecteur donne acces au chargement, au classement et aux
quotas. Le role administrateur ajoute le back office : etat du modele, contenu
de la base, journal des executions.

Les mots de passe ne sont jamais stockes en clair. Le fichier config.yaml ne
contient que leur empreinte SHA-256. Changer un mot de passe consiste a
recalculer cette empreinte, la procedure est decrite dans le README.
"""

import hashlib
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as reglages

CHEMIN_CONFIG = reglages.CHEMIN_COMPTES


# Comptes de secours si le fichier de configuration est absent
COMPTES_PAR_DEFAUT = [
    {"identifiant": "lecteur", "role": "lecteur",
     "empreinte": "216e8f0bcc088e0736cb6659d079e758ae3344c7cfad368479707991587d0084"},
    {"identifiant": "admin", "role": "administrateur",
     "empreinte": "8ef95be7af9f77ff3567198efea4e40d0485f53502079f8432462bbff2439fd7"}
]


def empreinte(texte):
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()



# Lecture des comptes depuis config.yaml
def lire_comptes():
    """Lit les comptes depuis config.yaml, sans dependance a une bibliotheque."""
    if not os.path.exists(CHEMIN_CONFIG):
        return COMPTES_PAR_DEFAUT
    comptes, courant = [], {}
    dans_section = False
    for ligne in open(CHEMIN_CONFIG, encoding="utf-8"):
        nue = ligne.strip()
        if nue.startswith("comptes:"):
            dans_section = True
            continue
        if not dans_section:
            continue
        if nue.startswith("- identifiant:"):
            if courant:
                comptes.append(courant)
            courant = {"identifiant": nue.split(":", 1)[1].strip().strip('"')}
        elif nue.startswith("role:"):
            courant["role"] = nue.split(":", 1)[1].strip().strip('"')
        elif nue.startswith("empreinte:"):
            courant["empreinte"] = nue.split(":", 1)[1].strip().strip('"')
        elif nue and not nue.startswith("-") and ":" in nue and courant:
            break
    if courant:
        comptes.append(courant)
    return comptes if comptes else COMPTES_PAR_DEFAUT



# Verification du mot de passe par comparaison des empreintes
def verifier(identifiant, mot_de_passe):
    for compte in lire_comptes():
        if compte.get("identifiant") == identifiant:
            if compte.get("empreinte") == empreinte(mot_de_passe):
                return compte.get("role")
    return None



# Formulaire de connexion, affiche tant que l'utilisateur n'est pas identifie
def demander_connexion():
    """Affiche le formulaire tant que l'utilisateur n'est pas identifie."""
    if st.session_state.get("role"):
        return st.session_state["role"]

    st.title("Aide a la lecture des candidatures")
    st.markdown("Programme de bourses DataCamp Donates, TDEV.")
    st.markdown("Merci de vous identifier pour continuer.")

    with st.form("connexion"):
        identifiant = st.text_input("Identifiant",
                                    help="Fourni par l'administrateur de TDEV.")
        mot_de_passe = st.text_input("Mot de passe", type="password",
                                     help="Huit caracteres au minimum.")
        valide = st.form_submit_button("Se connecter")

    if valide:
        role = verifier(identifiant.strip(), mot_de_passe)
        if role is None:
            st.error("Identifiant ou mot de passe incorrect.")
        else:
            st.session_state["role"] = role
            st.session_state["identifiant"] = identifiant.strip()
            st.rerun()

    st.stop()
