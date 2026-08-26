# web/backend/app/api/v1/desk.py
# Namespace de synchronisation desktop/web (favoris, colonnes, filtres, sync incrémental).
# Blueprint monté sur /api/v1/desk. Compatible mobile/tiers (JWT Bearer standard).

import json
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.desk_state import DeskFavorite, DeskFilterPreset, DeskColumnConfig, SyncEvent
from app.security.tenant import get_current_tenant_id
from app.realtime.socket_server import emit_preference_update

desk_bp = Blueprint("desk", __name__, url_prefix="/api/v1/desk")


def _user_id():
    uid = get_jwt_identity()
    return int(uid) if isinstance(uid, str) and uid.isdigit() else uid


def _tenant_id():
    return get_current_tenant_id()


def _record_event(entity, module, payload):
    """Incrémente la révision et journalise la mutation pour le pull/polling."""
    try:
        last = (
            SyncEvent.query.filter_by(user_id=_user_id())
            .order_by(SyncEvent.revision.desc())
            .first()
        )
        next_rev = (last.revision + 1) if last else 1
        ev = SyncEvent(
            tenant_id=_tenant_id(),
            user_id=_user_id(),
            entity=entity,
            module=module,
            payload=payload,
            revision=next_rev,
        )
        db.session.add(ev)
        db.session.commit()
        emit_preference_update(entity, _user_id(), payload)
        return next_rev
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning("Erreur journalisation sync: %s", exc)
        db.session.rollback()
        return None


# ============================ FAVORIS =====================================
@desk_bp.route("/favorites", methods=["GET"])
@jwt_required()
def list_favorites():
    rows = (
        DeskFavorite.query.filter_by(user_id=_user_id(), is_active=True)
        .order_by(DeskFavorite.updated_at.desc())
        .all()
    )
    return jsonify({"favorites": [r.to_public() for r in rows]}), 200


@desk_bp.route("/favorites", methods=["POST"])
@jwt_required()
def upsert_favorite():
    data = request.get_json(force=True, silent=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({"message": "path requis"}), 400
    fav = DeskFavorite.query.filter_by(
        user_id=_user_id(), path=path, is_active=True
    ).first()
    if fav:
        fav.label = data.get("label", fav.label)
        fav.data = data.get("data", fav.data)
    else:
        fav = DeskFavorite(
            tenant_id=_tenant_id(),
            user_id=_user_id(),
            path=path,
            label=data.get("label"),
            data=data.get("data"),
        )
        db.session.add(fav)
    db.session.commit()
    _record_event("favorite", None, fav.to_public())
    return jsonify({"favorites": [r.to_public() for r in
               DeskFavorite.query.filter_by(user_id=_user_id(), is_active=True).all()]}), 200


@desk_bp.route("/favorites/<path:key>", methods=["DELETE"])
@jwt_required()
def delete_favorite(key):
    fav = DeskFavorite.query.filter_by(
        user_id=_user_id(), path=key, is_active=True
    ).first()
    if fav:
        fav.is_active = False
        db.session.commit()
        _record_event("favorite", None, {"id": fav.id, "path": key, "deleted": True})
    return jsonify({"favorites": [r.to_public() for r in
               DeskFavorite.query.filter_by(user_id=_user_id(), is_active=True).all()]}), 200


# ============================ FILTRES =====================================
@desk_bp.route("/filters/<module>", methods=["GET"])
@jwt_required()
def list_filters(module):
    rows = DeskFilterPreset.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).all()
    return jsonify({"module": module, "presets": [r.to_public() for r in rows]}), 200


@desk_bp.route("/filters/<module>", methods=["POST"])
@jwt_required()
def upsert_filter(module):
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "name requis"}), 400
    preset_id = data.get("id")
    preset = None
    if preset_id:
        preset = DeskFilterPreset.query.filter_by(
            user_id=_user_id(), module=module, id=preset_id, is_active=True
        ).first()
    if not preset:
        preset = DeskFilterPreset.query.filter_by(
            user_id=_user_id(), module=module, name=name, is_active=True
        ).first()
    if preset:
        preset.name = name
        preset.filters = data.get("filters", preset.filters)
        preset.is_default = bool(data.get("isDefault", preset.is_default))
    else:
        preset = DeskFilterPreset(
            tenant_id=_tenant_id(),
            user_id=_user_id(),
            module=module,
            name=name,
            filters=data.get("filters", []),
            is_default=bool(data.get("isDefault", False)),
        )
        db.session.add(preset)
    if preset.is_default:
        DeskFilterPreset.query.filter_by(
            user_id=_user_id(), module=module, is_active=True
        ).filter(DeskFilterPreset.id != preset.id).update({"is_default": False})
    db.session.commit()
    _record_event("filter", module, preset.to_public())
    rows = DeskFilterPreset.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).all()
    return jsonify({"module": module, "presets": [r.to_public() for r in rows]}), 200


@desk_bp.route("/filters/<module>/<int:fid>", methods=["DELETE"])
@jwt_required()
def delete_filter(module, fid):
    preset = DeskFilterPreset.query.filter_by(
        user_id=_user_id(), module=module, id=fid, is_active=True
    ).first()
    if preset:
        preset.is_active = False
        db.session.commit()
        _record_event("filter", module, {"id": fid, "deleted": True})
    rows = DeskFilterPreset.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).all()
    return jsonify({"module": module, "presets": [r.to_public() for r in rows]}), 200


# ============================ COLONNES ====================================
@desk_bp.route("/columns/<module>", methods=["GET"])
@jwt_required()
def get_columns(module):
    cfg = DeskColumnConfig.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).first()
    if not cfg:
        return jsonify({"module": module, "config": {"widths": {}, "hidden": [], "sort": []}}), 200
    return jsonify(cfg.to_public()), 200


@desk_bp.route("/columns/<module>", methods=["POST"])
@jwt_required()
def save_columns(module):
    data = request.get_json(force=True, silent=True) or {}
    cfg = DeskColumnConfig.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).first()
    if cfg:
        cfg.widths = data.get("widths", cfg.widths)
        cfg.hidden = data.get("hidden", cfg.hidden)
        cfg.sort = data.get("sort", cfg.sort)
        cfg.version = data.get("version", cfg.version)
    else:
        cfg = DeskColumnConfig(
            tenant_id=_tenant_id(),
            user_id=_user_id(),
            module=module,
            widths=data.get("widths", {}),
            hidden=data.get("hidden", []),
            sort=data.get("sort", []),
            version=data.get("version", 1),
        )
        db.session.add(cfg)
    db.session.commit()
    _record_event("column", module, cfg.to_public())
    return jsonify(cfg.to_public()), 200


@desk_bp.route("/columns/<module>", methods=["DELETE"])
@jwt_required()
def reset_columns(module):
    cfg = DeskColumnConfig.query.filter_by(
        user_id=_user_id(), module=module, is_active=True
    ).first()
    if cfg:
        cfg.is_active = False
        db.session.commit()
    empty = {"widths": {}, "hidden": [], "sort": []}
    _record_event("column", module, {"module": module, "config": empty})
    return jsonify({"module": module, "config": empty}), 200


# ============================ SYNC INCERTEMENTAL ==========================
@desk_bp.route("/sync/mutations", methods=["POST"])
@jwt_required()
def sync_mutations():
    """Alias de /sync/push (compatible desktopApi.js historique)."""
    return sync_push()


@desk_bp.route("/sync/push", methods=["POST"])
@jwt_required()
def sync_push():
    """Applique un batch de mutations (provenant de la file hors-ligne d'un client)."""
    body = request.get_json(force=True, silent=True) or {}
    mutations = body.get("mutations", [])
    revision = None
    for m in mutations:
        entity = m.get("entity")
        op = m.get("op")
        p = m.get("payload", {})
        if entity == "favorite":
            if op == "delete":
                fav = DeskFavorite.query.filter_by(user_id=_user_id(), path=p.get("key"), is_active=True).first()
                if fav:
                    fav.is_active = False
            else:
                fav = DeskFavorite.query.filter_by(user_id=_user_id(), path=p.get("path"), is_active=True).first()
                if fav:
                    fav.label = p.get("label", fav.label); fav.data = p.get("data", fav.data)
                else:
                    fav = DeskFavorite(tenant_id=_tenant_id(), user_id=_user_id(),
                                       path=p.get("path"), label=p.get("label"), data=p.get("data"))
                    db.session.add(fav)
        elif entity == "column":
            mod = p.get("module")
            if op == "delete":
                c = DeskColumnConfig.query.filter_by(user_id=_user_id(), module=mod, is_active=True).first()
                if c: c.is_active = False
            else:
                c = DeskColumnConfig.query.filter_by(user_id=_user_id(), module=mod, is_active=True).first()
                cfg = p.get("config", {})
                if c:
                    c.widths = cfg.get("widths", c.widths); c.hidden = cfg.get("hidden", c.hidden); c.sort = cfg.get("sort", c.sort)
                else:
                    c = DeskColumnConfig(tenant_id=_tenant_id(), user_id=_user_id(), module=mod,
                                         widths=cfg.get("widths", {}), hidden=cfg.get("hidden", []), sort=cfg.get("sort", []))
                    db.session.add(c)
        elif entity == "filter":
            mod = p.get("module")
            if op == "delete":
                fp = DeskFilterPreset.query.filter_by(user_id=_user_id(), module=mod, id=p.get("id"), is_active=True).first()
                if fp: fp.is_active = False
            else:
                fp = DeskFilterPreset.query.filter_by(user_id=_user_id(), module=mod, id=p.get("id"), is_active=True).first()
                if not fp:
                    fp = DeskFilterPreset.query.filter_by(user_id=_user_id(), module=mod, name=p.get("name"), is_active=True).first()
                if fp:
                    fp.name = p.get("name", fp.name); fp.filters = p.get("filters", fp.filters)
                else:
                    fp = DeskFilterPreset(tenant_id=_tenant_id(), user_id=_user_id(), module=mod,
                                           name=p.get("name", "Sans nom"), filters=p.get("filters", []))
                    db.session.add(fp)
        db.session.commit()
        revision = _record_event(entity, p.get("module"), p)
    return jsonify({"revision": revision or 0, "applied": len(mutations)}), 200


@desk_bp.route("/sync/pull", methods=["GET"])
@jwt_required()
def sync_pull():
    """Renvoie l'état complet courant (dernière écriture gagne côté client)."""
    favs = [r.to_public() for r in
            DeskFavorite.query.filter_by(user_id=_user_id(), is_active=True).all()]
    modules = db.session.query(DeskFilterPreset.module).filter_by(
        user_id=_user_id(), is_active=True).distinct().all()
    filters = [
        {"module": mod[0], "presets": [r.to_public() for r in
         DeskFilterPreset.query.filter_by(user_id=_user_id(), module=mod[0], is_active=True).all()]}
        for mod in modules
    ]
    cols = [
        r.to_public() for r in
        DeskColumnConfig.query.filter_by(user_id=_user_id(), is_active=True).all()
    ]
    last = SyncEvent.query.filter_by(user_id=_user_id()).order_by(SyncEvent.revision.desc()).first()
    return jsonify({
        "favorites": favs,
        "filters": filters,
        "columns": cols,
        "revision": last.revision if last else 0,
    }), 200


@desk_bp.route("/sync/status", methods=["GET"])
@jwt_required()
def sync_status():
    last = SyncEvent.query.filter_by(user_id=_user_id()).order_by(SyncEvent.revision.desc()).first()
    return jsonify({"revision": last.revision if last else 0}), 200


@desk_bp.route("/events", methods=["GET"])
@jwt_required()
def events_poll():
    """Fallback polling temps-réel : événements depuis `since` (epoch ms)."""
    since = request.args.get("since", type=int)
    q = SyncEvent.query.filter_by(user_id=_user_id())
    if since:
        # compare with created_at epoch ms
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(since / 1000.0, tz=timezone.utc)
        q = q.filter(SyncEvent.created_at > dt)
    events = q.order_by(SyncEvent.id.asc()).limit(200).all()
    now = int(datetime.utcnow().timestamp() * 1000)
    return jsonify({"events": [e.to_public() for e in events], "now": now}), 200
