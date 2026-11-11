import type Konva from "konva";
import { useEffect, useMemo, useRef, useState } from "react";
import { Circle, Group, Image as KImage, Layer, Rect, Shape, Stage, Text } from "react-konva";

import type { EntityView, GameMap } from "../../api/types";
import { cellLabel } from "../../lib/rules";

const TERRAIN_COLORS: Record<string, string> = {
  wall: "#2b2520",
  difficult: "rgba(139, 101, 52, 0.55)",
  water: "rgba(60, 110, 170, 0.55)",
  pit: "rgba(0, 0, 0, 0.75)",
  void: "#000000",
};

function useHtmlImage(src: string | null): HTMLImageElement | null {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!src) {
      setImage(null);
      return;
    }
    const img = new window.Image();
    img.onload = () => setImage(img);
    img.onerror = () => setImage(null);
    img.src = src;
  }, [src]);
  return image;
}

export interface MapCanvasProps {
  map: GameMap;
  entities: EntityView[];
  backgroundUrl: string | null;
  dm: boolean;
  selectedEntityId?: string | null;
  highlight?: Set<string>;
  onCellClick?: (x: number, y: number) => void;
  onEntityClick?: (entity: EntityView) => void;
  height?: number;
}

export function MapCanvas({ map, entities, backgroundUrl, dm, selectedEntityId, highlight, onCellClick, onEntityClick, height = 640 }: MapCanvasProps) {
  const container = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  const [hover, setHover] = useState<[number, number] | null>(null);
  const image = useHtmlImage(backgroundUrl);
  const cell = map.has_background ? map.cell_size_px : 48;
  const ox = map.has_background ? map.grid_offset_x : 0;
  const oy = map.has_background ? map.grid_offset_y : 0;
  const worldW = Math.max(image?.width ?? 0, ox + map.width_cells * cell);
  const worldH = Math.max(image?.height ?? 0, oy + map.height_cells * cell);
  const scale = Math.min(width / worldW, height / worldH, 2);

  useEffect(() => {
    const el = container.current;
    if (!el) return;
    const observer = new ResizeObserver(() => setWidth(el.clientWidth));
    observer.observe(el);
    setWidth(el.clientWidth);
    return () => observer.disconnect();
  }, []);

  const explored = useMemo(() => new Set(map.explored.map(([x, y]) => `${x},${y}`)), [map.explored]);
  const visible = useMemo(() => new Set((map.visible ?? []).map(([x, y]) => `${x},${y}`)), [map.visible]);
  const showFog = !dm && map.fog_enabled;

  const toCell = (stage: Konva.Stage): [number, number] | null => {
    const pointer = stage.getPointerPosition();
    if (!pointer) return null;
    const x = Math.floor((pointer.x / scale - ox) / cell);
    const y = Math.floor((pointer.y / scale - oy) / cell);
    if (x < 0 || y < 0 || x >= map.width_cells || y >= map.height_cells) return null;
    return [x, y];
  };

  return (
    <div ref={container} className="relative w-full overflow-hidden rounded-lg border border-line bg-black">
      <Stage
        width={width}
        height={Math.min(height, worldH * scale)}
        scaleX={scale}
        scaleY={scale}
        onMouseMove={(e) => setHover(toCell(e.target.getStage()!))}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => {
          const target = toCell(e.target.getStage()!);
          if (target && onCellClick) onCellClick(target[0], target[1]);
        }}
        onTap={(e) => {
          const target = toCell(e.target.getStage()!);
          if (target && onCellClick) onCellClick(target[0], target[1]);
        }}
      >
        <Layer listening={false}>
          {image ? (
            <KImage image={image} x={0} y={0} />
          ) : (
            <Rect x={ox} y={oy} width={map.width_cells * cell} height={map.height_cells * cell} fill="#cbbd98" />
          )}
          <Shape
            sceneFunc={(ctx) => {
              // Capa lógica: terreno y puertas (en mapas sin imagen o para el DM).
              for (const [x, y, terrain] of map.logic.terrain ?? []) {
                if (terrain === "floor") continue;
                if (image && !dm && terrain === "wall") continue;
                ctx.fillStyle = TERRAIN_COLORS[terrain] ?? "transparent";
                ctx.fillRect(ox + x * cell, oy + y * cell, cell, cell);
              }
              for (const door of map.logic.doors ?? []) {
                ctx.fillStyle = door.secret && !door.discovered ? "#7b4fb3" : door.state === "open" ? "#a07b4a" : "#5a3d1e";
                const inset = cell * 0.2;
                ctx.fillRect(ox + door.x * cell + inset, oy + door.y * cell + inset, cell - 2 * inset, cell - 2 * inset);
              }
              if (dm) {
                for (const light of map.logic.lights ?? []) {
                  ctx.beginPath();
                  ctx.fillStyle = "rgba(255, 210, 120, 0.15)";
                  ctx.arc(ox + (light.x + 0.5) * cell, oy + (light.y + 0.5) * cell, ((light.bright_ft + light.dim_ft) / map.cell_size_ft) * cell, 0, Math.PI * 2);
                  ctx.fill();
                }
              }
              // Cuadrícula.
              ctx.strokeStyle = "rgba(20, 15, 10, 0.35)";
              ctx.lineWidth = 1 / scale;
              ctx.beginPath();
              for (let x = 0; x <= map.width_cells; x++) {
                ctx.moveTo(ox + x * cell, oy);
                ctx.lineTo(ox + x * cell, oy + map.height_cells * cell);
              }
              for (let y = 0; y <= map.height_cells; y++) {
                ctx.moveTo(ox, oy + y * cell);
                ctx.lineTo(ox + map.width_cells * cell, oy + y * cell);
              }
              ctx.stroke();
              if (highlight) {
                ctx.fillStyle = "rgba(201, 162, 74, 0.25)";
                for (const key of highlight) {
                  const [x, y] = key.split(",").map(Number);
                  ctx.fillRect(ox + x * cell, oy + y * cell, cell, cell);
                }
              }
            }}
          />
        </Layer>
        <Layer>
          {entities
            .filter((e) => e.x !== null && e.y !== null && e.map_id === map.id)
            .map((entity) => {
              const cx = ox + (entity.x! + 0.5) * cell;
              const cy = oy + (entity.y! + 0.5) * cell;
              const selected = entity.id === selectedEntityId;
              return (
                <Group
                  key={entity.id}
                  x={cx}
                  y={cy}
                  opacity={entity.hidden ? 0.5 : 1}
                  onClick={(e) => {
                    e.cancelBubble = true;
                    onEntityClick?.(entity);
                  }}
                  onTap={(e) => {
                    e.cancelBubble = true;
                    onEntityClick?.(entity);
                  }}
                >
                  <Circle
                    radius={cell * 0.42}
                    fill={entity.token_color}
                    stroke={selected ? "#ffd27a" : entity.disposition === "hostile" ? "#2a0d0d" : "#1d2414"}
                    strokeWidth={selected ? 4 / scale : 2 / scale}
                    shadowBlur={selected ? 12 : 0}
                    shadowColor="#ffd27a"
                  />
                  <Text
                    text={entity.name.slice(0, 2).toUpperCase()}
                    fontSize={cell * 0.36}
                    fontStyle="bold"
                    fill="#f4ecd8"
                    width={cell}
                    align="center"
                    offsetX={cell / 2}
                    offsetY={cell * 0.18}
                  />
                </Group>
              );
            })}
        </Layer>
        {showFog && (
          <Layer listening={false}>
            <Shape
              sceneFunc={(ctx) => {
                for (let x = 0; x < map.width_cells; x++) {
                  for (let y = 0; y < map.height_cells; y++) {
                    const key = `${x},${y}`;
                    if (visible.has(key)) continue;
                    ctx.fillStyle = explored.has(key) ? "rgba(10, 8, 6, 0.55)" : "#050403";
                    ctx.fillRect(ox + x * cell - 0.5, oy + y * cell - 0.5, cell + 1, cell + 1);
                  }
                }
                // Fuera de la cuadrícula (bordes de la imagen) también se oculta.
                ctx.fillStyle = "#050403";
                ctx.fillRect(0, 0, worldW, oy);
                ctx.fillRect(0, 0, ox, worldH);
                ctx.fillRect(ox + map.width_cells * cell, 0, worldW, worldH);
                ctx.fillRect(0, oy + map.height_cells * cell, worldW, worldH);
              }}
            />
          </Layer>
        )}
      </Stage>
      {hover && <div className="pointer-events-none absolute bottom-2 left-2 rounded bg-black/70 px-2 py-0.5 text-xs">{cellLabel(hover[0], hover[1])}</div>}
    </div>
  );
}
