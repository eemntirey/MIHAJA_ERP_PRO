# -*- coding: utf-8 -*-
"""app/security/password_policy.py

Politique centralisee des mots de passe pour MIHAJA ERP.

Fournit :

  - ``validate_password_strength`` : applique la politique au nouveau
    mot de passe. Centralisee ici pour eviter la duplication entre
    les routes (register, change-password, reset-password, etc.).

  - ``generate_temporary_password`` : produit un mot de passe
    temporaire sur pour la creation de compte par un Tenant. Reprend
    la politique (>= 12 caracteres, lettres + chiffres) pour eviter
    que le Tenant puisse saisir un mot de passe faible, conformement
    aux exigences de securite.

Aucun mot de passe en clair ne transite par les logs : les fonctions
retournent ``None`` en cas de succes ou un message localise, jamais
le mot de passe lui-meme.
"""

from __future__ import annotations

import re
import secrets
import string
from typing import Optional

MIN_LENGTH = 8
# Politique par defaut. Si l'application est deployee avec une
# politique plus stricte (longueur minimum elevee, symboles obligatoires,
# etc.), elle est surchargee via ``set_password_policy`` au demarrage.
_min_length: int = MIN_LENGTH
_require_uppercase: bool = True
_require_lowercase: bool = True
_require_digit: bool = True
_require_symbol: bool = False


def set_password_policy(
    *,
    min_length: Optional[int] = None,
    require_uppercase: Optional[bool] = None,
    require_lowercase: Optional[bool] = None,
    require_digit: Optional[bool] = None,
    require_symbol: Optional[bool] = None,
) -> None:
    """Permet de modifier la politique au demarrage de l''application."""
    global _min_length, _require_uppercase, _require_lowercase, _require_digit, _require_symbol
    if min_length is not None:
        _min_length = max(int(min_length), 6)
    if require_uppercase is not None:
        _require_uppercase = bool(require_uppercase)
    if require_lowercase is not None:
        _require_lowercase = bool(require_lowercase)
    if require_digit is not None:
        _require_digit = bool(require_digit)
    if require_symbol is not None:
        _require_symbol = bool(require_symbol)


def get_policy() -> dict:
    return {
        'min_length': _min_length,
        'require_uppercase': _require_uppercase,
        'require_lowercase': _require_lowercase,
        'require_digit': _require_digit,
        'require_symbol': _require_symbol,
    }


# Regex de symboles (ASCII). Si la politique n''exige pas de symboles,
# la regex n''est pas appliquee.
_SYMBOL_RE = re.compile(r'[!@#$%^&*()_+\-=\[\]{};:\"\\|,.<>/?`~]')


def validate_password_strength(password: Optional[str]) -> Optional[str]:
    """Retourne ``None`` si conforme, sinon un message d''erreur localise.

    Cette fonction est la source de verite cote serveur : le frontend
    peut l''afficher mais ne peut pas la contourner (le backend
    revalide systematiquement).
    """
    if not password or not isinstance(password, str):
        return 'Le mot de passe est requis'

    if len(password) < _min_length:
        return (
            f'Le mot de passe doit contenir au moins {_min_length} caracteres'
        )

    if _require_lowercase and not any(c.islower() for c in password):
        return 'Le mot de passe doit contenir au moins une lettre minuscule'

    if _require_uppercase and not any(c.isupper() for c in password):
        return 'Le mot de passe doit contenir au moins une lettre majuscule'

    if _require_digit and not any(c.isdigit() for c in password):
        return 'Le mot de passe doit contenir au moins un chiffre'

    if _require_symbol and not _SYMBOL_RE.search(password):
        return 'Le mot de passe doit contenir au moins un caractere special'

    return None


# Longueur minimum elevee pour les mots de passe temporaires, independante
# de la politique utilisateur, afin d''eviter qu''un Tenant puisse choisir
# (par saisie manuelle ou script) un mot de passe trivial.
_TEMP_MIN_LENGTH = 12


def generate_temporary_password(length: int = _TEMP_MIN_LENGTH) -> str:
    """Produit un mot de passe temporaire aleatoire et conforme.

    Utilise ``secrets`` (source CSPRNG) avec au moins une majuscule,
    une minuscule, deux chiffres. Evite les caracteres ambigus (0/O,
    1/l/I) pour faciliter la lecture lors de la saisie initiale.
    """
    n = max(int(length), _TEMP_MIN_LENGTH)
    # Alphabet sans caracteres ambigus
    alphabet = (
        string.ascii_uppercase.replace('O', '').replace('I', '')
        + string.ascii_lowercase.replace('l', '').replace('o', '')
        + string.digits.replace('0', '').replace('1', '')
    )

    while True:
        raw = ''.join(secrets.choice(alphabet) for _ in range(n))
        # Garantit la politique : 1+ minuscule, 1+ majuscule, 2+ chiffres
        if (
            any(c.islower() for c in raw)
            and any(c.isupper() for c in raw)
            and sum(c.isdigit() for c in raw) >= 2
        ):
            return raw