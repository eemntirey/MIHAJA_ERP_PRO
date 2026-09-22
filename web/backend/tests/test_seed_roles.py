"""Tests minimalistes du seed des rôles/permissions système.

Garantit que le seed est idempotent (la checklist CI exige une base seedée
après un seul passage) et que les rôles super_admin/admin existent.
"""
from app.models.role_permission import RoleModel, Permission


def test_roles_seeded(db):
    assert RoleModel.query.count() >= 1
    assert Permission.query.count() >= 1
    assert RoleModel.query.filter_by(name='super_admin').first() is not None
    assert RoleModel.query.filter_by(name='admin').first() is not None


def test_seed_roles_idempotent(db):
    from scripts.seed_roles import seed_roles

    before_roles = RoleModel.query.count()
    before_perms = Permission.query.count()
    assert before_roles > 0

    seed_roles()

    assert RoleModel.query.count() == before_roles
    assert Permission.query.count() == before_perms


def test_system_roles_flag(db):
    system = RoleModel.query.filter_by(is_system=True).all()
    assert len(system) >= 1
    for role in system:
        assert role.is_system is True