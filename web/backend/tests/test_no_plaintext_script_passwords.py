# -*- coding: utf-8 -*-
"""Verifie qu'aucun script de `scripts/` ne contient de mot de passe en clair.

Banniere P0 #70 / A3 : les bannieres `Super123!` et `Test1234!` sont
interdites dans `web/backend/scripts/*.py`. Les scripts lisent les mots de
passe depuis l'environnement (`DEFAULT_ADMIN_PASSWORD`,
`SEED_MADA_PASSWORD`, ...) — voir `.env.example`.
"""
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'scripts'
FORBIDDEN_PASSWORDS = ('Super123!', 'Test1234!')


def test_no_plaintext_passwords_in_scripts():
    """Aucun script ne doit contenir une banniere de mot de passe en clair."""
    offenders = []
    for path in sorted(SCRIPTS_DIR.glob('*.py')):
        content = path.read_text(encoding='utf-8')
        for password in FORBIDDEN_PASSWORDS:
            if password in content:
                offenders.append(f'{path.name}: {password}')
    assert not offenders, (
        'Mots de passe en clair trouves dans scripts/ '
        '(lire via variables d\'env, jamais en dur) : '
        + ', '.join(offenders)
    )
