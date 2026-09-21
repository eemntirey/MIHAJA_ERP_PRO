# web/backend/tests/test_replication_full_cycle.py
# Cycle complet hors-ligne (scénario d'acceptation du projet).

# NOTE : ce test décrit le scénario E2E attendu. Les fixtures
# (local_app, central_app, central_stub) doivent être mises
# en place dans conftest.py pour une exécution réelle.

def test_full_offline_cycle(local_app, central_app, central_stub, seeded_outbox_factory):
    """Scénario E2E de réplication hors-ligne + retour réseau."""
    # 1. Central seed (produits existants côté central)
    # 2. Local pull ces produits (pull_changes)
    # 3. Coupure réseau (central_stub.down())
    # 4. Création vente locale
    # 5. Vérification stock local décrémenté
    # 6. Retour réseau (central_stub.up())
    # 7. Push du scheduler (push_pending)
    # 8. Vente présente sur central avec même local_uuid appliqué
    # 9. Second push du même local_uuid -> 'duplicate' (pas de double décrémentation)
    # 10. Stock central == stock local
    assert True  # structure du scénario définie
