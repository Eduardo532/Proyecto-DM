"""Mapas, entidades, niebla de guerra y conocimiento: estado real del mundo y proyecciones.

Las funciones ``*_for_players`` construyen lo que puede ver la mesa. Nunca devuelven
información exclusiva del DM ni elementos ocultos que aún no se han descubierto.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.engines.errors import RuleViolation
from app.engines.maps.grid import DoorState, Grid, Occupancy, Terrain, cell_label, shortest_path
from app.engines.maps.vision import Light, LightSource, Viewer, group_visible, light_map
from app.models import Character, Entity, Fact, FactAwareness, GameMap, Scene
from app.services.characters import sheet_data
from app.services.events import append_event

AMBIENT = {"bright": Light.BRIGHT, "dim": Light.DIM, "dark": Light.DARK}


# ---------------------------------------------------------------- mapas ----
def grid_for(game_map: GameMap) -> Grid:
    logic = game_map.logic or {}
    grid = Grid(game_map.width_cells, game_map.height_cells, game_map.cell_size_ft,
                diagonal_rule=str(logic.get("diagonal_rule", "5e")))  # fmt: skip
    for x, y, terrain in logic.get("terrain", []):
        grid.terrain[(int(x), int(y))] = Terrain(terrain)
    for door in logic.get("doors", []):
        grid.doors[(int(door["x"]), int(door["y"]))] = DoorState(door.get("state", "closed"))
    return grid


def lights_for(game_map: GameMap, grid: Grid) -> dict[tuple[int, int], Light]:
    sources = [
        LightSource((int(s["x"]), int(s["y"])), int(s.get("bright_ft", 20)), int(s.get("dim_ft", 20)))
        for s in (game_map.logic or {}).get("lights", [])
    ]
    return light_map(grid, sources, AMBIENT.get(game_map.ambient_light, Light.BRIGHT))


def _viewers(db: Session, game_map: GameMap) -> list[Viewer]:
    viewers: list[Viewer] = []
    rows = db.scalars(select(Entity).where(Entity.map_id == game_map.id, Entity.kind == "character"))
    for entity in rows:
        if entity.x is None or entity.y is None:
            continue
        darkvision = 0
        blinded = "blinded" in entity.conditions
        if entity.character_id:
            character = db.get(Character, entity.character_id)
            if character:
                darkvision = sheet_data(character).darkvision_ft
                blinded = blinded or "blinded" in character.conditions
                if character.status == "dead":
                    continue
        viewers.append(Viewer((entity.x, entity.y), darkvision_ft=darkvision, blinded=blinded))
    return viewers


def visible_now(db: Session, game_map: GameMap) -> set[tuple[int, int]]:
    if not game_map.fog_enabled:
        return {(x, y) for x in range(game_map.width_cells) for y in range(game_map.height_cells)}
    grid = grid_for(game_map)
    return group_visible(grid, _viewers(db, game_map), lights_for(game_map, grid))


def update_fog(db: Session, game_map: GameMap) -> set[tuple[int, int]]:
    visible = visible_now(db, game_map)
    explored = {(int(c[0]), int(c[1])) for c in game_map.explored} | visible
    game_map.explored = sorted([list(c) for c in explored])
    return visible


def map_for_dm(game_map: GameMap) -> dict[str, Any]:
    return {
        "id": game_map.id,
        "name": game_map.name,
        "origin": game_map.origin,
        "width_cells": game_map.width_cells,
        "height_cells": game_map.height_cells,
        "cell_size_ft": game_map.cell_size_ft,
        "grid_offset_x": game_map.grid_offset_x,
        "grid_offset_y": game_map.grid_offset_y,
        "cell_size_px": game_map.cell_size_px,
        "ambient_light": game_map.ambient_light,
        "has_background": game_map.background_asset_id is not None,
        "fog_enabled": game_map.fog_enabled,
        "logic": game_map.logic,
        "explored": game_map.explored,
    }


def map_for_players(db: Session, game_map: GameMap) -> dict[str, Any]:
    visible = visible_now(db, game_map)
    explored = {(int(c[0]), int(c[1])) for c in game_map.explored} | visible
    logic = game_map.logic or {}

    def known(x: int, y: int) -> bool:
        return not game_map.fog_enabled or (int(x), int(y)) in explored

    doors = [
        d for d in logic.get("doors", [])
        if known(d["x"], d["y"]) and (not d.get("secret") or d.get("discovered"))
    ]  # fmt: skip
    data = map_for_dm(game_map)
    data["logic"] = {
        "terrain": [t for t in logic.get("terrain", []) if known(t[0], t[1])],
        "doors": doors,
        "lights": [s for s in logic.get("lights", []) if known(s["x"], s["y"])],
    }
    data["explored"] = sorted([list(c) for c in explored])
    data["visible"] = sorted([list(c) for c in visible])
    return data


# ------------------------------------------------------------- entidades ---
def entity_for_dm(entity: Entity) -> dict[str, Any]:
    return {
        "id": entity.id,
        "scene_id": entity.scene_id,
        "map_id": entity.map_id,
        "kind": entity.kind,
        "character_id": entity.character_id,
        "npc_id": entity.npc_id,
        "name": entity.name,
        "name_public": entity.name_public,
        "x": entity.x,
        "y": entity.y,
        "size": entity.size,
        "hp_current": entity.hp_current,
        "hp_max": entity.hp_max,
        "armor_class": entity.armor_class,
        "conditions": entity.conditions,
        "hidden": entity.hidden,
        "disposition": entity.disposition,
        "stats": entity.stats,
        "token_color": entity.token_color,
    }


def apparent_health(current: int | None, maximum: int | None) -> str | None:
    if current is None or not maximum:
        return None
    ratio = current / maximum
    if current <= 0:
        return "caído"
    if ratio >= 1:
        return "ileso"
    if ratio > 0.5:
        return "herido"
    if ratio > 0.25:
        return "malherido"
    return "a punto de caer"


def entity_for_players(entity: Entity, character: Character | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": entity.id,
        "kind": entity.kind,
        "character_id": entity.character_id,
        "name": entity.name if entity.kind == "character" else (entity.name_public or entity.name),
        "x": entity.x,
        "y": entity.y,
        "size": entity.size,
        "conditions": entity.conditions,
        "disposition": entity.disposition,
        "token_color": entity.token_color,
        "map_id": entity.map_id,
        "scene_id": entity.scene_id,
    }
    if character is not None:
        data.update(hp_current=character.hp_current, hp_max=character.hp_max, conditions=character.conditions)
    else:
        data["health"] = apparent_health(entity.hp_current, entity.hp_max)
    return data


def entities_for_players(db: Session, campaign_id: str, scene_id: str | None) -> list[dict[str, Any]]:
    query = select(Entity).where(Entity.campaign_id == campaign_id, Entity.hidden.is_(False))
    if scene_id:
        query = query.where(Entity.scene_id == scene_id)
    result: list[dict[str, Any]] = []
    visible_by_map: dict[str, set[tuple[int, int]]] = {}
    for entity in db.scalars(query):
        if entity.kind != "character" and entity.map_id and entity.x is not None and entity.y is not None:
            if entity.map_id not in visible_by_map:
                game_map = db.get(GameMap, entity.map_id)
                visible_by_map[entity.map_id] = visible_now(db, game_map) if game_map else set()
            if (entity.x, entity.y) not in visible_by_map[entity.map_id]:
                continue
        character = db.get(Character, entity.character_id) if entity.character_id else None
        result.append(entity_for_players(entity, character))
    return result


def move_entity(
    db: Session, entity: Entity, x: int, y: int, *, budget_ft: int | None = None, actor_kind: str = "player",
    session_id: str | None = None,
) -> dict[str, Any]:  # fmt: skip
    """Mueve un token validando el camino con la capa lógica. Devuelve camino y coste."""
    if entity.map_id is None:
        raise RuleViolation("La entidad no está en ningún mapa.")
    game_map = db.get(GameMap, entity.map_id)
    if game_map is None:
        raise RuleViolation("El mapa no existe.")
    grid = grid_for(game_map)
    target = (x, y)
    if not grid.in_bounds(target):
        raise RuleViolation(f"{cell_label(target)} está fuera del mapa.")
    if entity.x is None or entity.y is None:
        path, cost = [target], 0  # colocación inicial
        if grid.blocks_movement(target):
            raise RuleViolation(f"No se puede colocar en {cell_label(target)}.")
    else:
        others = db.scalars(select(Entity).where(Entity.map_id == entity.map_id, Entity.id != entity.id))
        hostile: set[tuple[int, int]] = set()
        friendly: set[tuple[int, int]] = set()
        for other in others:
            if other.x is None or other.y is None or other.kind == "object":
                continue
            enemies = {entity.disposition, other.disposition} == {"ally", "hostile"} or (
                entity.kind == "character" and other.disposition == "hostile"
            )
            (hostile if enemies else friendly).add((other.x, other.y))
        occupancy = Occupancy(frozenset(hostile), frozenset(friendly))
        if target in friendly or target in hostile:
            raise RuleViolation(f"{cell_label(target)} está ocupada.")
        found = shortest_path(grid, (entity.x, entity.y), target, occupancy)
        if found is None:
            raise RuleViolation(f"No hay camino posible hasta {cell_label(target)}.")
        path = found
        cost = sum(grid.step_cost_ft(a, b) for a, b in pairwise(path))
        if budget_ft is not None and cost > budget_ft:
            raise RuleViolation(f"Moverse a {cell_label(target)} cuesta {cost} pies y solo quedan {budget_ft}.")
    entity.x, entity.y = target
    update_fog(db, game_map)
    append_event(
        db, entity.campaign_id, "entity_moved",
        {"entity_id": entity.id,
         "name": entity.name if entity.kind == "character" else entity.name_public or entity.name,
         "to": cell_label(target), "x": x, "y": y, "cost_ft": cost},
        actor_kind=actor_kind, session_id=session_id, visibility="dm" if entity.hidden else "public",
    )  # fmt: skip
    return {"path": [list(c) for c in path], "cost_ft": cost, "to": cell_label(target)}


# ----------------------------------------------------------- conocimiento --
def known_facts(db: Session, campaign_id: str) -> list[Fact]:
    aware = select(FactAwareness.fact_id).where(FactAwareness.knower_kind.in_(("party", "character")))
    return list(
        db.scalars(
            select(Fact)
            .where(Fact.campaign_id == campaign_id, or_(Fact.knowledge_level == "public", Fact.id.in_(aware)))
            .order_by(Fact.created_at)
        )
    )


def reveal_fact(
    db: Session, fact: Fact, *, to: str = "party", character_id: str | None = None, actor_kind: str = "dm",
    session_id: str | None = None,
) -> bool:  # fmt: skip
    """Marca un hecho como conocido. Devuelve False si ya se conocía."""
    knower_kind, knower_id = ("character", character_id) if to == "character" and character_id else ("party", "party")
    if db.get(FactAwareness, (fact.id, knower_kind, knower_id)):
        return False
    event = append_event(
        db, fact.campaign_id, "fact_revealed",
        {"fact_id": fact.id, "subject": fact.subject, "statement": fact.statement, "to": knower_kind,
         "character_id": character_id},
        actor_kind=actor_kind, session_id=session_id,
    )  # fmt: skip
    db.add(FactAwareness(fact_id=fact.id, knower_kind=knower_kind, knower_id=knower_id, learned_event_id=event.id))
    return True


def scene_for_players(scene: Scene) -> dict[str, Any]:
    return {
        "id": scene.id,
        "name": scene.name,
        "summary": scene.summary_public,
        "map_id": scene.map_id,
        "status": scene.status,
        "lighting": scene.lighting,
    }
