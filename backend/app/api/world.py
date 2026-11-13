"""Escenas, mapas, entidades, hechos, PNJ, misiones y memoria.

Las rutas sin token DM devuelven solo lo que la mesa puede ver.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import CampaignDep, Db, DmCampaign, IsDm, commit
from app.models import Campaign, DocumentAsset, Entity, Fact, GameMap, MemoryEntry, Npc, Quest, Scene
from app.schemas.world import (
    EntityCreate,
    EntityUpdate,
    FactCreate,
    FactOut,
    FactUpdate,
    MapCreate,
    MapUpdate,
    MemoryIn,
    MemoryOut,
    Move,
    NpcIn,
    NpcOut,
    QuestIn,
    QuestOut,
    Reveal,
    SceneCreate,
    SceneOut,
    SceneUpdate,
)
from app.document_processing.classify import player_text
from app.services import world
from app.services.errors import Forbidden, NotFound
from app.services.events import append_event
from app.services.sessions import open_session

router = APIRouter(tags=["mundo"])


def _owned[T: (Scene, GameMap, Entity, Fact, Npc, Quest, MemoryEntry)](
    db: Db, model: type[T], campaign: Campaign, item_id: str
) -> T:
    item = db.get(model, item_id)
    if item is None or item.campaign_id != campaign.id:
        raise NotFound("El elemento no existe.")
    return item


# --------------------------------------------------------------- escenas ---
@router.get("/campaigns/{campaign_id}/scenes", response_model=list[dict[str, Any]])
def list_scenes(campaign: CampaignDep, db: Db, dm: IsDm) -> list[dict[str, Any]]:
    rows = db.scalars(select(Scene).where(Scene.campaign_id == campaign.id).order_by(Scene.order_index))
    if dm:
        return [SceneOut.model_validate(s).model_dump() for s in rows]
    return [world.scene_for_players(s) for s in rows if s.status != "unvisited"]


@router.post("/campaigns/{campaign_id}/scenes", response_model=SceneOut, status_code=201)
def create_scene(campaign: DmCampaign, body: SceneCreate, db: Db) -> Scene:
    scene = Scene(campaign_id=campaign.id, **body.model_dump())
    db.add(scene)
    commit(db)
    return scene


@router.patch("/campaigns/{campaign_id}/scenes/{scene_id}", response_model=SceneOut)
def update_scene(campaign: DmCampaign, scene_id: str, body: SceneUpdate, db: Db) -> Scene:
    scene = _owned(db, Scene, campaign, scene_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(scene, key, value)
    commit(db)
    return scene


@router.delete("/campaigns/{campaign_id}/scenes/{scene_id}", status_code=204)
def delete_scene(campaign: DmCampaign, scene_id: str, db: Db) -> None:
    db.delete(_owned(db, Scene, campaign, scene_id))
    commit(db)


# ----------------------------------------------------------------- mapas ---
@router.get("/campaigns/{campaign_id}/maps", response_model=list[dict[str, Any]])
def list_maps(campaign: CampaignDep, db: Db, dm: IsDm) -> list[dict[str, Any]]:
    rows = list(db.scalars(select(GameMap).where(GameMap.campaign_id == campaign.id).order_by(GameMap.created_at)))
    if dm:
        return [world.map_for_dm(m) for m in rows]
    visited = select(Scene).where(Scene.campaign_id == campaign.id, Scene.status != "unvisited")
    shown = {s.map_id for s in db.scalars(visited)}
    return [{"id": m.id, "name": m.name} for m in rows if m.id in shown]


@router.post("/campaigns/{campaign_id}/maps", response_model=dict[str, Any], status_code=201)
def create_map(campaign: DmCampaign, body: MapCreate, db: Db) -> dict[str, Any]:
    if body.background_asset_id:
        asset = db.get(DocumentAsset, body.background_asset_id)
        if asset is None or asset.campaign_id != campaign.id:
            raise NotFound("La imagen no existe.")
    game_map = GameMap(campaign_id=campaign.id, origin="pdf" if body.background_asset_id else "manual",
                       logic={"terrain": [], "doors": [], "lights": []}, explored=[], **body.model_dump())
    db.add(game_map)
    commit(db)
    return world.map_for_dm(game_map)


@router.get("/campaigns/{campaign_id}/maps/{map_id}", response_model=dict[str, Any])
def read_map(campaign: CampaignDep, map_id: str, db: Db, dm: IsDm) -> dict[str, Any]:
    game_map = _owned(db, GameMap, campaign, map_id)
    return world.map_for_dm(game_map) if dm else world.map_for_players(db, game_map)


@router.patch("/campaigns/{campaign_id}/maps/{map_id}", response_model=dict[str, Any])
def update_map(campaign: DmCampaign, map_id: str, body: MapUpdate, db: Db) -> dict[str, Any]:
    game_map = _owned(db, GameMap, campaign, map_id)
    data = body.model_dump(exclude_unset=True, exclude={"reset_fog"})
    for key, value in data.items():
        if value is not None or key == "cell_height_px":
            setattr(game_map, key, value)
    if body.logic is not None:
        world.grid_for(game_map)  # valida la capa lógica
    if body.reset_fog:
        game_map.explored = []
    world.update_fog(db, game_map)
    append_event(db, campaign.id, "map_updated", {"map_id": game_map.id})
    commit(db)
    return world.map_for_dm(game_map)


@router.get("/campaigns/{campaign_id}/maps/{map_id}/image")
def map_image(campaign: CampaignDep, map_id: str, db: Db, dm: IsDm, variant: str = "player",
              dm_token: str | None = None) -> FileResponse:
    from app.services.dm_auth import tokens

    game_map = _owned(db, GameMap, campaign, map_id)
    asset = None
    if variant == "dm":
        if not (dm or tokens.check(dm_token, campaign.id)):
            raise Forbidden("La versión del DM requiere el modo DM.")
        if game_map.dm_background_asset_id:
            asset = db.get(DocumentAsset, game_map.dm_background_asset_id)
    if asset is None or not Path(asset.file_path).is_file():
        asset = db.get(DocumentAsset, game_map.background_asset_id) if game_map.background_asset_id else None
    if asset is None or not Path(asset.file_path).is_file():
        raise NotFound("El mapa no tiene imagen.")
    return FileResponse(asset.file_path)


@router.post("/campaigns/{campaign_id}/maps/{map_id}/detect-grid", response_model=dict[str, Any])
def detect_grid(campaign: DmCampaign, map_id: str, db: Db) -> dict[str, Any]:
    """Mide la cuadrícula de la imagen de fondo (o de su versión con cuadrícula) y ajusta el mapa."""
    from app.engines.errors import RuleViolation
    from app.importing.maps import GRID_CONFIDENCE, cells_for, estimate_grid

    game_map = _owned(db, GameMap, campaign, map_id)
    background = db.get(DocumentAsset, game_map.background_asset_id) if game_map.background_asset_id else None
    if background is None:
        raise RuleViolation("El mapa no tiene imagen de fondo.")
    source = background
    if background.group_key:
        sibling = db.scalar(select(DocumentAsset).where(
            DocumentAsset.campaign_id == campaign.id, DocumentAsset.group_key == background.group_key,
            DocumentAsset.variant == "grid", DocumentAsset.width == background.width,
            DocumentAsset.height == background.height))
        source = sibling or background
    guess = estimate_grid(Path(source.file_path))
    if guess is None or guess.confidence < GRID_CONFIDENCE:
        raise RuleViolation("No se ve una cuadrícula clara en la imagen. Ajusta el tamaño de casilla a mano.")
    game_map.cell_size_px = guess.cell_w
    game_map.cell_height_px = None if guess.square else guess.cell_h
    game_map.grid_offset_x, game_map.grid_offset_y = guess.offset_x, guess.offset_y
    game_map.width_cells, game_map.height_cells = cells_for(
        int(background.width - guess.offset_x), int(background.height - guess.offset_y), guess.cell_w, guess.cell_h)
    world.update_fog(db, game_map)
    append_event(db, campaign.id, "map_updated", {"map_id": game_map.id})
    commit(db)
    return {**world.map_for_dm(game_map), "grid_confidence": guess.confidence}


@router.delete("/campaigns/{campaign_id}/maps/{map_id}", status_code=204)
def delete_map(campaign: DmCampaign, map_id: str, db: Db) -> None:
    db.delete(_owned(db, GameMap, campaign, map_id))
    commit(db)


# ------------------------------------------------------------- entidades ---
@router.get("/campaigns/{campaign_id}/entities", response_model=list[dict[str, Any]])
def list_entities(campaign: CampaignDep, db: Db, dm: IsDm, scene_id: str | None = None) -> list[dict[str, Any]]:
    if dm:
        query = select(Entity).where(Entity.campaign_id == campaign.id)
        if scene_id:
            query = query.where(Entity.scene_id == scene_id)
        return [world.entity_for_dm(e) for e in db.scalars(query)]
    return world.entities_for_players(db, campaign.id, scene_id)


@router.post("/campaigns/{campaign_id}/entities", response_model=dict[str, Any], status_code=201)
def create_entity(campaign: DmCampaign, body: EntityCreate, db: Db) -> dict[str, Any]:
    entity = Entity(campaign_id=campaign.id, hp_current=body.hp_max, conditions=[], **body.model_dump())
    db.add(entity)
    db.flush()
    append_event(db, campaign.id, "entity_created", {"entity_id": entity.id, "name": entity.name}, actor_kind="dm",
                 visibility="dm")
    commit(db)
    return world.entity_for_dm(entity)


@router.patch("/campaigns/{campaign_id}/entities/{entity_id}", response_model=dict[str, Any])
def update_entity(campaign: CampaignDep, entity_id: str, body: EntityUpdate, db: Db, dm: IsDm) -> dict[str, Any]:
    entity = _owned(db, Entity, campaign, entity_id)
    data = body.model_dump(exclude_unset=True)
    # La mesa solo puede asignar mapa/escena a los tokens de sus propios personajes.
    allowed_for_players = {"map_id", "scene_id"}
    if not dm and (entity.kind != "character" or set(data) - allowed_for_players):
        raise Forbidden("Hace falta el modo DM para editar esta entidad.")
    for key, value in data.items():
        setattr(entity, key, value)
    if "hidden" in data and data["hidden"] is False:
        append_event(db, campaign.id, "entity_revealed", world.entity_for_players(entity), actor_kind="dm")
    if entity.map_id:
        game_map = db.get(GameMap, entity.map_id)
        if game_map:
            world.update_fog(db, game_map)
    commit(db)
    return world.entity_for_dm(entity) if dm else world.entity_for_players(entity)


@router.post("/campaigns/{campaign_id}/entities/{entity_id}/move", response_model=dict[str, Any])
def move_entity(campaign: CampaignDep, entity_id: str, body: Move, db: Db, dm: IsDm) -> dict[str, Any]:
    entity = _owned(db, Entity, campaign, entity_id)
    if not dm and entity.kind != "character":
        raise Forbidden("La mesa solo puede mover a sus personajes.")
    session = open_session(db, campaign.id)
    budget = None
    if session and session.state == "combat":
        from app.services.combat import movement_budget

        budget = movement_budget(db, campaign.id, entity.id, enforce_turn=not dm)
    result = world.move_entity(db, entity, body.x, body.y, budget_ft=budget, actor_kind="dm" if dm else "player",
                               session_id=session.id if session else None)
    if session and session.state == "combat":
        from app.services.combat import spend_movement

        spend_movement(db, campaign.id, entity.id, int(result["cost_ft"]))
    commit(db)
    return result


@router.delete("/campaigns/{campaign_id}/entities/{entity_id}", status_code=204)
def delete_entity(campaign: DmCampaign, entity_id: str, db: Db) -> None:
    db.delete(_owned(db, Entity, campaign, entity_id))
    commit(db)


# ---------------------------------------------------------------- hechos ---
@router.get("/campaigns/{campaign_id}/facts", response_model=list[FactOut])
def list_facts(campaign: CampaignDep, db: Db, dm: IsDm) -> list[FactOut]:
    if dm:
        rows = db.scalars(select(Fact).where(Fact.campaign_id == campaign.id).order_by(Fact.created_at))
        return [FactOut.model_validate(f) for f in rows]
    result = []
    for fact in world.known_facts(db, campaign.id):
        out = FactOut.model_validate(fact)
        out.statement = player_text(fact.statement)
        out.discovery = {}
        out.keywords = []
        result.append(out)
    return result


@router.post("/campaigns/{campaign_id}/facts", response_model=FactOut, status_code=201)
def create_fact(campaign: DmCampaign, body: FactCreate, db: Db) -> Fact:
    fact = Fact(campaign_id=campaign.id, source="manual", **body.model_dump())
    db.add(fact)
    commit(db)
    return fact


@router.patch("/campaigns/{campaign_id}/facts/{fact_id}", response_model=FactOut)
def update_fact(campaign: DmCampaign, fact_id: str, body: FactUpdate, db: Db) -> Fact:
    fact = _owned(db, Fact, campaign, fact_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(fact, key, value)
    commit(db)
    return fact


@router.post("/campaigns/{campaign_id}/facts/{fact_id}/reveal", status_code=204)
def reveal(campaign: DmCampaign, fact_id: str, body: Reveal, db: Db) -> None:
    fact = _owned(db, Fact, campaign, fact_id)
    session = open_session(db, campaign.id)
    world.reveal_fact(db, fact, to=body.to, character_id=body.character_id,
                      session_id=session.id if session else None)
    commit(db)


@router.delete("/campaigns/{campaign_id}/facts/{fact_id}", status_code=204)
def delete_fact(campaign: DmCampaign, fact_id: str, db: Db) -> None:
    db.delete(_owned(db, Fact, campaign, fact_id))
    commit(db)


# ------------------------------------------------------------------- PNJ ---
@router.get("/campaigns/{campaign_id}/npcs", response_model=list[dict[str, Any]])
def list_npcs(campaign: CampaignDep, db: Db, dm: IsDm) -> list[dict[str, Any]]:
    rows = db.scalars(select(Npc).where(Npc.campaign_id == campaign.id).order_by(Npc.name))
    if dm:
        return [NpcOut.model_validate(n).model_dump() for n in rows]
    return [{"id": n.id, "name": n.name, "description": n.public_description, "status": n.status}
            for n in rows if n.known_to_party]


@router.post("/campaigns/{campaign_id}/npcs", response_model=NpcOut, status_code=201)
def create_npc(campaign: DmCampaign, body: NpcIn, db: Db) -> Npc:
    npc = Npc(campaign_id=campaign.id, **body.model_dump())
    db.add(npc)
    commit(db)
    return npc


@router.put("/campaigns/{campaign_id}/npcs/{npc_id}", response_model=NpcOut)
def update_npc(campaign: DmCampaign, npc_id: str, body: NpcIn, db: Db) -> Npc:
    npc = _owned(db, Npc, campaign, npc_id)
    for key, value in body.model_dump().items():
        setattr(npc, key, value)
    commit(db)
    return npc


@router.delete("/campaigns/{campaign_id}/npcs/{npc_id}", status_code=204)
def delete_npc(campaign: DmCampaign, npc_id: str, db: Db) -> None:
    db.delete(_owned(db, Npc, campaign, npc_id))
    commit(db)


# -------------------------------------------------------------- misiones ---
@router.get("/campaigns/{campaign_id}/quests", response_model=list[dict[str, Any]])
def list_quests(campaign: CampaignDep, db: Db, dm: IsDm) -> list[dict[str, Any]]:
    rows = db.scalars(select(Quest).where(Quest.campaign_id == campaign.id).order_by(Quest.created_at))
    if dm:
        return [QuestOut.model_validate(q).model_dump() for q in rows]
    return [{"id": q.id, "title": q.title, "description": q.description_public, "status": q.status}
            for q in rows if q.status != "unknown"]


@router.post("/campaigns/{campaign_id}/quests", response_model=QuestOut, status_code=201)
def create_quest(campaign: DmCampaign, body: QuestIn, db: Db) -> Quest:
    quest = Quest(campaign_id=campaign.id, **body.model_dump())
    db.add(quest)
    commit(db)
    return quest


@router.put("/campaigns/{campaign_id}/quests/{quest_id}", response_model=QuestOut)
def update_quest(campaign: DmCampaign, quest_id: str, body: QuestIn, db: Db) -> Quest:
    quest = _owned(db, Quest, campaign, quest_id)
    previous = quest.status
    for key, value in body.model_dump().items():
        setattr(quest, key, value)
    if previous != quest.status and quest.status != "unknown":
        append_event(db, campaign.id, "quest_updated", {"quest_id": quest.id, "title": quest.title,
                     "status": quest.status}, actor_kind="dm")
    commit(db)
    return quest


# --------------------------------------------------------------- memoria ---
@router.get("/campaigns/{campaign_id}/memory", response_model=list[MemoryOut])
def list_memory(campaign: CampaignDep, db: Db, dm: IsDm) -> list[MemoryEntry]:
    query = select(MemoryEntry).where(MemoryEntry.campaign_id == campaign.id, MemoryEntry.superseded_by.is_(None))
    if not dm:
        query = query.where(MemoryEntry.visibility == "public")
    return list(db.scalars(query.order_by(MemoryEntry.created_at.desc()).limit(300)))


@router.post("/campaigns/{campaign_id}/memory", response_model=MemoryOut, status_code=201)
def create_memory(campaign: DmCampaign, body: MemoryIn, db: Db) -> MemoryEntry:
    entry = MemoryEntry(campaign_id=campaign.id, edited_by_dm=True, **body.model_dump())
    db.add(entry)
    commit(db)
    return entry


@router.put("/campaigns/{campaign_id}/memory/{memory_id}", response_model=MemoryOut)
def correct_memory(campaign: DmCampaign, memory_id: str, body: MemoryIn, db: Db) -> MemoryEntry:
    """Corrige un recuerdo sin borrarlo: crea uno nuevo y marca el anterior como reemplazado."""
    old = _owned(db, MemoryEntry, campaign, memory_id)
    entry = MemoryEntry(campaign_id=campaign.id, edited_by_dm=True, source_event_ids=old.source_event_ids,
                        **body.model_dump())
    db.add(entry)
    db.flush()
    old.superseded_by = entry.id
    append_event(db, campaign.id, "memory_corrected", {"old": old.id, "new": entry.id}, actor_kind="dm",
                 visibility="dm")
    commit(db)
    return entry
