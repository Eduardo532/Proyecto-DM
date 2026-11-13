import { useEffect, useState } from "react";

import { imageUrl } from "../../api/client";
import { useCampaignMutation, useEntities, useMaps } from "../../api/hooks";
import type { GameMap, MapLogic } from "../../api/types";
import { Button, Empty, ErrorText, Field, Input, Panel, Select } from "../../components/ui";
import { MapCanvas } from "../maps/MapCanvas";

type Tool = "floor" | "wall" | "difficult" | "water" | "pit" | "door" | "secret_door" | "light" | "erase";

const TOOLS: [Tool, string][] = [
  ["wall", "Muro"],
  ["floor", "Suelo"],
  ["difficult", "Terreno difícil"],
  ["water", "Agua"],
  ["pit", "Foso"],
  ["door", "Puerta"],
  ["secret_door", "Puerta secreta"],
  ["light", "Antorcha (luz)"],
  ["erase", "Borrar puerta/luz"],
];

function applyTool(logic: MapLogic, tool: Tool, x: number, y: number): MapLogic {
  const terrain = logic.terrain.filter(([tx, ty]) => tx !== x || ty !== y);
  const doors = logic.doors.filter((d) => d.x !== x || d.y !== y);
  const lights = logic.lights.filter((l) => l.x !== x || l.y !== y);
  switch (tool) {
    case "floor":
      return { ...logic, terrain, doors };
    case "wall":
    case "difficult":
    case "water":
    case "pit":
      return { ...logic, terrain: [...terrain, [x, y, tool]], doors };
    case "door":
      return { ...logic, terrain, doors: [...doors, { x, y, state: "closed" }] };
    case "secret_door":
      return { ...logic, terrain, doors: [...doors, { x, y, state: "closed", secret: true, discovered: false }] };
    case "light":
      return { ...logic, lights: [...lights, { x, y, bright_ft: 20, dim_ft: 20 }] };
    case "erase":
      return { ...logic, doors, lights };
  }
}

function normalize(logic: Partial<MapLogic> | undefined): MapLogic {
  return { ...logic, terrain: logic?.terrain ?? [], doors: logic?.doors ?? [], lights: logic?.lights ?? [] };
}

export function DmMaps({ campaignId }: { campaignId: string }) {
  const maps = useMaps(campaignId);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = maps.data?.find((m) => m.id === selectedId) ?? maps.data?.[0];
  const create = useCampaignMutation<Record<string, unknown>, GameMap>(campaignId, "POST", "/maps");
  const [form, setForm] = useState({ name: "", width_cells: 20, height_cells: 15 });

  return (
    <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
      <div className="flex flex-col gap-4">
        <Panel title="Mapas">
          {maps.data?.length === 0 && <Empty>Importa mapas (imágenes, PDF o ZIP) en «Importar», o crea uno en blanco.</Empty>}
          <ul className="flex flex-col gap-1">
            {maps.data?.map((m) => (
              <li key={m.id}>
                <button className={`w-full rounded px-2 py-1 text-left ${selected?.id === m.id ? "bg-ink-3 ring-1 ring-gold" : "hover:bg-ink-3"}`} onClick={() => setSelectedId(m.id)}>
                  {m.name} <span className="text-xs text-parchment-dim">{m.width_cells}×{m.height_cells}</span>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Mapa en blanco">
          <form
            className="flex flex-col gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate(form, { onSuccess: (m) => setSelectedId(m.id) });
            }}
          >
            <Input placeholder="Nombre" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <div className="flex gap-2">
              <Input type="number" min={1} max={200} value={form.width_cells} onChange={(e) => setForm({ ...form, width_cells: Number(e.target.value) })} />
              <Input type="number" min={1} max={200} value={form.height_cells} onChange={(e) => setForm({ ...form, height_cells: Number(e.target.value) })} />
            </div>
            <Button variant="primary">Crear</Button>
            <ErrorText error={create.error} />
          </form>
        </Panel>
      </div>
      {selected && <MapEditor key={selected.id} campaignId={campaignId} map={selected} />}
    </div>
  );
}

function MapEditor({ campaignId, map }: { campaignId: string; map: GameMap }) {
  const entities = useEntities(campaignId);
  const [logic, setLogic] = useState<MapLogic>(normalize(map.logic));
  const [tool, setTool] = useState<Tool>("wall");
  const [dirty, setDirty] = useState(false);
  const [calibration, setCalibration] = useState({
    width_cells: map.width_cells,
    height_cells: map.height_cells,
    cell_size_px: map.cell_size_px,
    cell_height_px: map.cell_height_px,
    grid_offset_x: map.grid_offset_x,
    grid_offset_y: map.grid_offset_y,
    ambient_light: map.ambient_light,
    fog_enabled: map.fog_enabled,
  });
  const save = useCampaignMutation<Record<string, unknown>>(campaignId, "PATCH", `/maps/${map.id}`);
  const remove = useCampaignMutation<null>(campaignId, "DELETE", `/maps/${map.id}`);
  const detect = useCampaignMutation<null, GameMap & { grid_confidence: number }>(campaignId, "POST", `/maps/${map.id}/detect-grid`);
  const [dmVersion, setDmVersion] = useState(map.has_dm_background);
  useEffect(() => {
    setLogic(normalize(map.logic));
  }, [map.logic]);
  const preview: GameMap = { ...map, ...calibration, logic };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-1">
        {TOOLS.map(([key, label]) => (
          <Button key={key} variant={tool === key ? "primary" : "ghost"} onClick={() => setTool(key)}>
            {label}
          </Button>
        ))}
        <Button
          variant="primary"
          className="ml-auto"
          disabled={save.isPending}
          onClick={() => save.mutate({ ...calibration, logic }, { onSuccess: () => setDirty(false) })}
        >
          {dirty ? "Guardar cambios *" : "Guardar"}
        </Button>
      </div>
      <MapCanvas
        map={preview}
        entities={entities.data ?? []}
        backgroundUrl={map.has_background ? imageUrl(campaignId, `/maps/${map.id}/image${dmVersion && map.has_dm_background ? "?variant=dm" : ""}`) : null}
        dm
        onCellClick={(x, y) => {
          setLogic((current) => applyTool(current, tool, x, y));
          setDirty(true);
        }}
        height={700}
      />
      {map.has_dm_background && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-parchment-dim">Imagen:</span>
          <Button variant={dmVersion ? "primary" : "ghost"} onClick={() => setDmVersion(true)}>
            Versión DM
          </Button>
          <Button variant={dmVersion ? "ghost" : "primary"} onClick={() => setDmVersion(false)}>
            Lo que ve la mesa
          </Button>
        </div>
      )}
      <ErrorText error={save.error ?? remove.error ?? detect.error} />
      <Panel title="Calibración y opciones">
        <div className="grid gap-3 sm:grid-cols-4">
          <Field label="Columnas">
            <Input type="number" min={1} max={200} value={calibration.width_cells} onChange={(e) => setCalibration({ ...calibration, width_cells: Number(e.target.value) })} />
          </Field>
          <Field label="Filas">
            <Input type="number" min={1} max={200} value={calibration.height_cells} onChange={(e) => setCalibration({ ...calibration, height_cells: Number(e.target.value) })} />
          </Field>
          <Field label={calibration.cell_height_px ? "Ancho de casilla (px)" : "Casilla (px de la imagen)"}>
            <Input type="number" step={0.5} min={3} value={calibration.cell_size_px} onChange={(e) => setCalibration({ ...calibration, cell_size_px: Number(e.target.value) })} />
          </Field>
          {calibration.cell_height_px !== null && (
            <Field label="Alto de casilla (px)">
              <Input type="number" step={0.5} min={3} value={calibration.cell_height_px} onChange={(e) => setCalibration({ ...calibration, cell_height_px: Number(e.target.value) })} />
            </Field>
          )}
          <Field label="Luz ambiental">
            <Select value={calibration.ambient_light} onChange={(e) => setCalibration({ ...calibration, ambient_light: e.target.value })}>
              <option value="bright">Brillante</option>
              <option value="dim">Tenue</option>
              <option value="dark">Oscuridad</option>
            </Select>
          </Field>
          <Field label="Desplazamiento X (px)">
            <Input type="number" step={0.5} value={calibration.grid_offset_x} onChange={(e) => setCalibration({ ...calibration, grid_offset_x: Number(e.target.value) })} />
          </Field>
          <Field label="Desplazamiento Y (px)">
            <Input type="number" step={0.5} value={calibration.grid_offset_y} onChange={(e) => setCalibration({ ...calibration, grid_offset_y: Number(e.target.value) })} />
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={calibration.fog_enabled} onChange={(e) => setCalibration({ ...calibration, fog_enabled: e.target.checked })} />
            Niebla de guerra
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={calibration.cell_height_px !== null}
              onChange={(e) => setCalibration({ ...calibration, cell_height_px: e.target.checked ? calibration.cell_size_px : null })}
            />
            Casillas rectangulares
          </label>
          {map.has_background && (
            <div className="flex items-end">
              <Button
                disabled={detect.isPending}
                onClick={() =>
                  detect.mutate(null, {
                    onSuccess: (m) =>
                      setCalibration({
                        ...calibration,
                        width_cells: m.width_cells,
                        height_cells: m.height_cells,
                        cell_size_px: m.cell_size_px,
                        cell_height_px: m.cell_height_px,
                        grid_offset_x: m.grid_offset_x,
                        grid_offset_y: m.grid_offset_y,
                      }),
                  })
                }
              >
                {detect.isPending ? "Midiendo…" : "Detectar cuadrícula"}
              </Button>
            </div>
          )}
          <div className="flex items-end gap-2">
            <Button onClick={() => save.mutate({ reset_fog: true })}>Reiniciar niebla</Button>
            <Button variant="danger" onClick={() => window.confirm("¿Borrar el mapa?") && remove.mutate(null)}>
              Borrar
            </Button>
          </div>
        </div>
        <p className="mt-2 text-xs text-parchment-dim">
          Ajusta casilla y desplazamiento hasta que la cuadrícula coincida con la del dibujo. Las paredes que pintes son las que el motor usa para movimiento y visión.
        </p>
      </Panel>
    </div>
  );
}
