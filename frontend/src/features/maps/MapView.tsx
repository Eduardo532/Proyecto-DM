import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, imageUrl } from "../../api/client";
import { useCombat, useEntities, useMap, useMaps, useScenes, useSession } from "../../api/hooks";
import type { EntityView } from "../../api/types";
import { Empty, ErrorText, Panel, Select } from "../../components/ui";
import { useIsDm } from "../../stores/dm";
import { CombatTracker } from "../combat/CombatTracker";
import { MapCanvas } from "./MapCanvas";

export function MapView({ campaignId }: { campaignId: string }) {
  const dm = useIsDm(campaignId);
  const session = useSession(campaignId);
  const scenes = useScenes(campaignId);
  const maps = useMaps(campaignId);
  const scene = scenes.data?.find((s) => s.id === session.data?.scene_id);
  const [chosen, setChosen] = useState<string | null>(null);
  const mapId = chosen ?? scene?.map_id ?? (dm ? maps.data?.[0]?.id : undefined) ?? null;
  const map = useMap(campaignId, mapId);
  const entities = useEntities(campaignId);
  const combat = useCombat(campaignId);
  const [selected, setSelected] = useState<EntityView | null>(null);
  const client = useQueryClient();
  const move = useMutation({
    mutationFn: ({ entity, x, y }: { entity: EntityView; x: number; y: number }) =>
      api(`/campaigns/${campaignId}/entities/${entity.id}/move`, { method: "POST", body: { x, y }, campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const place = useMutation({
    mutationFn: ({ entity, x, y }: { entity: EntityView; x: number; y: number }) =>
      api(`/campaigns/${campaignId}/entities/${entity.id}`, { method: "PATCH", body: { map_id: mapId, scene_id: scene?.id ?? null }, campaignId }).then(() =>
        api(`/campaigns/${campaignId}/entities/${entity.id}/move`, { method: "POST", body: { x, y }, campaignId }),
      ),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });

  if (!mapId) {
    return (
      <div className="pt-4">
        <Empty>No hay mapa para la escena actual. El DM puede crearlo o asociarlo en el Panel DM → Mapas.</Empty>
      </div>
    );
  }
  const unplaced = (entities.data ?? []).filter((e) => e.kind === "character" && (e.map_id !== mapId || e.x === null));

  return (
    <div className="grid gap-4 pt-1 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex flex-col gap-2">
        {dm && (
          <Select value={mapId} onChange={(e) => setChosen(e.target.value)} className="w-72">
            {maps.data?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </Select>
        )}
        {map.data && (
          <MapCanvas
            map={map.data}
            entities={entities.data ?? []}
            backgroundUrl={map.data.has_background ? imageUrl(campaignId, `/maps/${map.data.id}/image`) : null}
            dm={dm}
            selectedEntityId={selected?.id}
            onEntityClick={(entity) => (dm || entity.kind === "character" ? setSelected(entity) : undefined)}
            onCellClick={(x, y) => {
              if (!selected) return;
              if (selected.map_id !== mapId || selected.x === null) place.mutate({ entity: selected, x, y });
              else move.mutate({ entity: selected, x, y });
            }}
          />
        )}
        <ErrorText error={move.error ?? place.error} />
        <p className="text-sm text-parchment-dim">
          {selected ? `Seleccionado: ${selected.name}. Haz clic en una casilla para moverlo.` : "Selecciona la ficha de un personaje y después la casilla de destino."}
        </p>
      </div>
      <div className="flex flex-col gap-4">
        {combat.data && <CombatTracker campaignId={campaignId} combat={combat.data} />}
        {unplaced.length > 0 && (
          <Panel title="Colocar en el mapa">
            <ul className="flex flex-col gap-1">
              {unplaced.map((e) => (
                <li key={e.id}>
                  <button className={`w-full rounded px-2 py-1 text-left ${selected?.id === e.id ? "bg-ink-3 ring-1 ring-gold" : "hover:bg-ink-3"}`} onClick={() => setSelected(e)}>
                    {e.name}
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-parchment-dim">Elige un personaje y haz clic en su casilla inicial.</p>
          </Panel>
        )}
        <Panel title="Leyenda">
          <ul className="text-sm text-parchment-dim">
            <li>⬛ Desconocido · ▪️ Explorado · casillas claras: visibles ahora</li>
            <li>🟫 Puerta · 🟦 Agua · 🟧 Terreno difícil</li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}
