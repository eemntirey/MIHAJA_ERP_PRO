#!/usr/bin/env python3
"""Audit des dépendances Python (P2) — exécuter : python audit_deps.py"""
import subprocess
import sys

try:
    import importlib.util
    spec = importlib.util.find_spec("pip_audit")
    if spec is None:
        print("pip-audit non installé. Installation recommandée : pip install pip-audit")
        sys.exit(1)
except Exception:
    pass

try:
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "--requirement", "requirements.txt", "--desc"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
except FileNotFoundError:
    print("pip-audit non disponible dans le PATH. Installez : pip install pip-audit")
except Exception as e:
    print("Erreur audit:", e)
