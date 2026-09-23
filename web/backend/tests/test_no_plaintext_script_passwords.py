# -*- coding: utf-8 -*-
"""Verifie qu'aucun script de `scripts/` ne contient de mot de passe en clair.

Banniere P0 #70 / A3 : les bannieres `Super123!`, `Test1234!` et les
residus `TechPass123!`... de reset_enterprise_passwords.py sont interdits
dans `web/backend/scripts/*.py`. Les scripts lisent les mots de passe
depuis l'environnement (`DEFAULT_ADMIN_PASSWORD`, `SEED_MADA_PASSWORD`,
`SEED_USER_PASSWORD`, ...) — voir `.env.example`.
"""
import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'scripts'
FORBIDDEN_PASSWORDS = (
    'Super123!',
    'Test1234!',
    'TechPass123!',
    'GreenPass123!',
    'DistriPass123!',
    'GlobalPass123!',
    'MegaPass123!',
)
# Motif plus large : un mot de passe suivi d'un repli `or '...'` (fallback
# en clair apres getenv/getenv). Les replis aleatoires (`or secrets....`)
# sont autorises, pas les litteraux de chaines.
PASSWORD_OR_STRING_FALLBACK = re.compile(r"(?i)password.{0,200}?\bor\s+['\"]")


def test_no_plaintext_passwords_in_scripts():
    """Aucun script ne doit contenir une banniere de mot de passe en clair."""
    offenders = []
    for path in sorted(SCRIPTS_DIR.glob('*.py')):
        content = path.read_text(encoding='utf-8')
        for password in FORBIDDEN_PASSWORDS:
            if password in content:
                offenders.append(f'{path.name}: {password}')
        for line_no, line in enumerate(content.splitlines(), 1):
            if PASSWORD_OR_STRING_FALLBACK.search(line):
                offenders.append(f'{path.name}:{line_no}: repli or "..." en clair')
    assert not offenders, (
        'Mots de passe en clair trouves dans scripts/ '
        '(lire via variables d\'env, jamais en dur) : '
        + ', '.join(offenders)
    )
