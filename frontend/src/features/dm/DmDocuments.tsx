import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, imageUrl } from "../../api/client";
import { useCampaignMutation } from "../../api/hooks";
import type { Asset, Chunk, DocumentInfo, GameMap, KnowledgeLevel } from "../../api/types";
import { Badge, Button, Empty, ErrorText, Field, Input, Modal, Panel, Select } from "../../components/ui";
import { KNOWLEDGE_LABELS } from "../../lib/rules";
import { ImportReview, UploadZone, documentKindLabel } from "./ImportPanel";

const LEVEL_TONE = { public: "moss", conditional: "gold", dm: "blood" } as const;

export function DmDocuments({ campaignId }: { campaignId: string }) {
  const documents = useQuery({
    queryKey: ["c", campaignId, "dm", "documents"],
    queryFn: () => api<DocumentInfo[]>(`/campaigns/${campaignId}/documents`, { campaignId }),
    refetchInterval: (query) => ((query.state.data ?? []).some((d) => d.status === "processing" || d.status === "pending") ? 2000 : false),
  });
  const reprocess = useCampaignMutation<string>(campaignId, "POST", (id) => `/documents/${id}/reprocess`);
  const remove = useCampaignMutation<string>(campaignId, "DELETE", (id) => `/documents/${id}`);
  const all = documents.data ?? [];
  const roots = all.filter((d) => !d.parent_id || !all.some((p) => p.id === d.parent_id));

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Importar campañas, mapas y personajes">
        <UploadZone campaignId={campaignId} />
        <ul className="mt-4 flex flex-col gap-3">
          {roots.map((d) => (
            <li key={d.id} className="rounded border border-line p-3">
              <DocumentRow document={d} onReprocess={() => reprocess.mutate(d.id)} onDelete={() => {
                if (window.confirm(`¿Quitar «${d.title}»? Se borran sus fragmentos e imágenes (los personajes ya creados se mantienen).`)) remove.mutate(d.id);
              }} />
              <ImportReview campaignId={campaignId} document={d} />
              {all
                .filter((child) => child.parent_id === d.id)
                .map((child) => (
                  <div key={child.id} className="mt-2 border-l-2 border-gold/40 pl-3">
                    <DocumentRow document={child} onReprocess={() => reprocess.mutate(child.id)} />
                  </div>
                ))}
            </li>
          ))}
        </ul>
      </Panel>
      <ChunkReview campaignId={campaignId} documents={all.filter((d) => d.kind === "pdf")} />
      <AssetGallery campaignId={campaignId} />
    </div>
  );
}

function DocumentRow({ document: d, onReprocess, onDelete }: { document: DocumentInfo; onReprocess: () => void; onDelete?: () => void }) {
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-serif text-lg">{d.title}</span>
        <span className="flex items-center gap-2 text-sm text-parchment-dim">
          <Badge>{documentKindLabel(d)}</Badge>
          {d.page_count > 0 && `${d.page_count} págs.`}
          <Badge tone={d.status === "ready" ? "moss" : d.status === "error" ? "blood" : "gold"}>{STATUS[d.status]}</Badge>
          <Button onClick={onReprocess}>Reprocesar</Button>
          {onDelete && (
            <Button variant="ghost" onClick={onDelete}>
              Quitar
            </Button>
          )}
        </span>
      </div>
      {d.status !== "ready" && (
        <div className="mt-2 h-2 overflow-hidden rounded bg-ink-3">
          <div className="h-full bg-gold transition-all" style={{ width: `${d.progress}%` }} />
        </div>
      )}
      <ul className="mt-2 text-xs text-parchment-dim">
        {d.log.slice(-3).map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>
    </>
  );
}

const STATUS: Record<DocumentInfo["status"], string> = { pending: "en cola", processing: "procesando", ready: "listo", error: "error" };

function ChunkReview({ campaignId, documents }: { campaignId: string; documents: DocumentInfo[] }) {
  const [level, setLevel] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [query, setQuery] = useState("");
  const chunks = useQuery({
    queryKey: ["c", campaignId, "dm", "chunks", level, documentId],
    queryFn: () => api<Chunk[]>(`/campaigns/${campaignId}/chunks?limit=500${level ? `&level=${level}` : ""}${documentId ? `&document_id=${documentId}` : ""}`, { campaignId }),
  });
  const update = useCampaignMutation<{ id: string; knowledge_level: KnowledgeLevel }>(campaignId, "PATCH", (b) => `/chunks/${b.id}`);
  const filtered = (chunks.data ?? []).filter((c) => !query || c.text.toLowerCase().includes(query.toLowerCase()) || c.section.toLowerCase().includes(query.toLowerCase()));
  return (
    <Panel title="Revisión de la clasificación (qué puede saber la mesa)">
      <div className="mb-3 flex flex-wrap gap-2">
        <Select value={documentId} onChange={(e) => setDocumentId(e.target.value)} className="w-60">
          <option value="">Todos los documentos</option>
          {documents.map((d) => (
            <option key={d.id} value={d.id}>
              {d.title}
            </option>
          ))}
        </Select>
        <Select value={level} onChange={(e) => setLevel(e.target.value)} className="w-48">
          <option value="">Todos los niveles</option>
          <option value="public">Público</option>
          <option value="conditional">Condicionado</option>
          <option value="dm">Solo DM</option>
        </Select>
        <Input placeholder="Buscar texto…" value={query} onChange={(e) => setQuery(e.target.value)} className="w-60" />
      </div>
      {filtered.length === 0 && <Empty>Sin fragmentos.</Empty>}
      <ul className="flex max-h-[60vh] flex-col gap-2 overflow-auto scroll-thin">
        {filtered.map((c) => (
          <li key={c.id} className="rounded border border-line p-2">
            <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-parchment-dim">
              <span>p. {c.page_start}</span>
              <span>{c.section}</span>
              <Badge>{c.kind}</Badge>
              <Badge tone={LEVEL_TONE[c.knowledge_level]}>{KNOWLEDGE_LABELS[c.knowledge_level]}</Badge>
              <span className="italic">{c.classification_reason}</span>
              <span className="ml-auto flex gap-1">
                {(["public", "conditional", "dm"] as const).map((lvl) => (
                  <Button key={lvl} variant={c.knowledge_level === lvl ? "primary" : "ghost"} onClick={() => update.mutate({ id: c.id, knowledge_level: lvl })}>
                    {KNOWLEDGE_LABELS[lvl]}
                  </Button>
                ))}
              </span>
            </div>
            <p className="whitespace-pre-wrap font-serif text-sm">{c.text.slice(0, 900)}</p>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

const ASSET_KINDS: Record<string, string> = {
  map: "Mapa",
  illustration: "Ilustración",
  handout: "Ilustración / handout",
  token: "Token",
  marker: "Marcador",
  unknown: "Sin clasificar",
};

function AssetGallery({ campaignId }: { campaignId: string }) {
  const [kind, setKind] = useState("");
  const assets = useQuery({
    queryKey: ["c", campaignId, "dm", "assets"],
    queryFn: () => api<Asset[]>(`/campaigns/${campaignId}/assets`, { campaignId }),
  });
  const update = useCampaignMutation<{ id: string; kind?: string; knowledge_level?: string }>(campaignId, "PATCH", (b) => `/assets/${b.id}`);
  const [creating, setCreating] = useState<Asset | null>(null);
  const shown = (assets.data ?? []).filter((a) => !kind || a.kind === kind);
  return (
    <Panel title="Imágenes, mapas, tokens y marcadores">
      <div className="mb-3 flex flex-wrap gap-2">
        <Select value={kind} onChange={(e) => setKind(e.target.value)} className="w-56">
          <option value="">Todo ({assets.data?.length ?? 0})</option>
          {Object.entries(ASSET_KINDS).map(([value, label]) => (
            <option key={value} value={value}>
              {label} ({(assets.data ?? []).filter((a) => a.kind === value).length})
            </option>
          ))}
        </Select>
      </div>
      {shown.length === 0 && <Empty>No hay imágenes.</Empty>}
      <ul className="grid max-h-[70vh] gap-3 overflow-auto scroll-thin sm:grid-cols-2 lg:grid-cols-4">
        {shown.map((a) => (
          <li key={a.id} className="rounded border border-line p-2">
            <img
              src={imageUrl(campaignId, `/assets/${a.id}/image`)}
              alt={a.caption || `Página ${a.page}`}
              className={`w-full rounded object-contain ${a.kind === "marker" || a.kind === "token" ? "h-20" : "h-40"}`}
              loading="lazy"
            />
            <div className="mt-1 truncate text-sm" title={a.original_name || a.caption}>
              {a.caption || (a.page ? `Página ${a.page}` : "Imagen")}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-1 text-xs">
              {a.page > 0 && <span>p. {a.page}</span>}
              <Badge tone={a.kind === "map" ? "gold" : "default"}>{ASSET_KINDS[a.kind] ?? a.kind}</Badge>
              {a.variant && a.variant !== "default" && <Badge>{a.variant}</Badge>}
              {typeof a.meta.condition === "string" && <Badge tone="arcane">{a.meta.condition}</Badge>}
              <Badge tone={LEVEL_TONE[a.knowledge_level]}>{KNOWLEDGE_LABELS[a.knowledge_level]}</Badge>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {(a.kind === "map" || a.kind === "illustration" || a.kind === "handout") && <Button onClick={() => setCreating(a)}>Crear mapa</Button>}
              <Select value={a.kind} onChange={(e) => update.mutate({ id: a.id, kind: e.target.value })} className="w-36" aria-label="Tipo de imagen">
                {Object.entries(ASSET_KINDS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
              <Button onClick={() => update.mutate({ id: a.id, knowledge_level: a.knowledge_level === "public" ? "dm" : "public" })}>
                {a.knowledge_level === "public" ? "Ocultar" : "Mostrar a la mesa"}
              </Button>
            </div>
          </li>
        ))}
      </ul>
      {creating && <CreateMapFromAsset campaignId={campaignId} asset={creating} onClose={() => setCreating(null)} />}
    </Panel>
  );
}

function CreateMapFromAsset({ campaignId, asset, onClose }: { campaignId: string; asset: Asset; onClose: () => void }) {
  const [cellPx, setCellPx] = useState(50);
  const [name, setName] = useState(asset.caption || `Mapa p. ${asset.page}`);
  const create = useCampaignMutation<Record<string, unknown>, GameMap>(campaignId, "POST", "/maps");
  const calibrate = useCampaignMutation<{ id: string; cell_size_px: number }>(campaignId, "PATCH", (b) => `/maps/${b.id}`);
  const width = Math.max(1, Math.min(200, Math.round(asset.width / cellPx)));
  const height = Math.max(1, Math.min(200, Math.round(asset.height / cellPx)));
  return (
    <Modal title="Crear mapa desde imagen" onClose={onClose}>
      <div className="flex flex-col gap-3">
        <Field label="Nombre">
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label={`Tamaño de casilla en píxeles (imagen de ${asset.width}×${asset.height})`}>
          <Input type="number" min={5} value={cellPx} onChange={(e) => setCellPx(Number(e.target.value) || 50)} />
        </Field>
        <p className="text-sm text-parchment-dim">
          Resultado: {width}×{height} casillas. Después podrás afinar la calibración y dibujar paredes y puertas en Mapas.
        </p>
        <ErrorText error={create.error} />
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Cancelar</Button>
          <Button
            variant="primary"
            onClick={() =>
              create.mutate(
                { name, width_cells: width, height_cells: height, background_asset_id: asset.id },
                { onSuccess: (map) => calibrate.mutate({ id: map.id, cell_size_px: cellPx }, { onSuccess: onClose }) },
              )
            }
          >
            Crear
          </Button>
        </div>
      </div>
    </Modal>
  );
}
