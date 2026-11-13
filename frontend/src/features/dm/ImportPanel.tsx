import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { useCampaignMutation } from "../../api/hooks";
import type { CharacterDraft, DocumentInfo, ImportItem, ImportKind } from "../../api/types";
import { Badge, Button, ErrorText, Panel } from "../../components/ui";
import { ABILITIES, SKILLS } from "../../lib/rules";

export const ACCEPTED_FILES = ".pdf,.zip,.png,.jpg,.jpeg,.webp,.gif,.bmp";

const KIND_INFO: Record<ImportKind, { label: string; icon: string; tone: "default" | "gold" | "blood" | "moss" | "arcane" }> = {
  adventure: { label: "Aventuras", icon: "📜", tone: "gold" },
  character: { label: "Fichas de personaje", icon: "🧝", tone: "moss" },
  map: { label: "Mapas", icon: "🗺️", tone: "gold" },
  handout: { label: "Ilustraciones", icon: "🖼️", tone: "arcane" },
  token: { label: "Tokens", icon: "🪙", tone: "default" },
  marker: { label: "Marcadores de estado", icon: "🔖", tone: "default" },
  archive: { label: "Archivos comprimidos", icon: "🗜️", tone: "default" },
  ignored: { label: "Ignorados", icon: "·", tone: "default" },
};
const KIND_ORDER: ImportKind[] = ["adventure", "character", "map", "handout", "token", "marker", "ignored"];
const DOCUMENT_KIND: Record<DocumentInfo["kind"], string> = {
  pdf: "Aventura (PDF)",
  sheet: "Ficha de personaje",
  archive: "ZIP",
  image: "Imagen",
  map_pdf: "Mapa (PDF)",
};
const STATUS_LABEL: Record<ImportItem["status"], string> = {
  pending: "pendiente",
  done: "importado",
  draft: "por confirmar",
  ignored: "ignorado",
  error: "error",
};
const VARIANT_LABEL: Record<string, string> = {
  dm: "versión DM",
  player: "versión jugadores",
  grid: "con cuadrícula",
  nogrid: "sin cuadrícula",
  zones: "con zonas",
};

/** Zona de subida: acepta varios archivos a la vez (arrastrar y soltar o elegir). */
export function UploadZone({ campaignId }: { campaignId: string }) {
  const client = useQueryClient();
  const [dragging, setDragging] = useState(false);
  const [queue, setQueue] = useState<string[]>([]);
  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      for (const file of files) {
        setQueue((q) => [...q, file.name]);
        const form = new FormData();
        form.append("file", file);
        try {
          await api<DocumentInfo>(`/campaigns/${campaignId}/documents`, { method: "POST", form, campaignId });
        } finally {
          setQueue((q) => q.filter((name) => name !== file.name));
          void client.invalidateQueries({ queryKey: ["c", campaignId] });
        }
      }
    },
  });
  const send = (list: FileList | null) => {
    const files = Array.from(list ?? []);
    if (files.length) upload.mutate(files);
  };
  return (
    <div>
      <label
        className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center hover:border-gold ${dragging ? "border-gold bg-gold/5" : "border-line"}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          send(e.dataTransfer.files);
        }}
      >
        <span className="text-3xl">📦</span>
        <span className="font-serif text-lg">{upload.isPending ? `Subiendo ${queue.join(", ")}…` : "Arrastra aquí o haz clic para elegir archivos"}</span>
        <span className="max-w-2xl text-sm text-parchment-dim">
          Aventuras en PDF, fichas de personaje (D&D Beyond, Nivel20, hoja oficial rellenable o impresa), mapas (imagen o PDF, con sus versiones DM / jugadores / con y sin
          cuadrícula), ilustraciones, tokens, marcadores de estado y ZIP con todo eso dentro (también ZIP dentro de ZIP).
        </span>
        <input type="file" multiple accept={ACCEPTED_FILES} className="hidden" onChange={(e) => {
          send(e.target.files);
          e.target.value = "";
        }} />
      </label>
      <ErrorText error={upload.error} />
    </div>
  );
}

/** Lo que se detectó en un archivo importado, agrupado por tipo, con los borradores de personaje a confirmar. */
export function ImportReview({ campaignId, document }: { campaignId: string; document: DocumentInfo }) {
  const [showAll, setShowAll] = useState(false);
  const items = document.manifest.map((item, index) => ({ item, index }));
  if (items.length === 0) return null;
  const groups = KIND_ORDER.map((kind) => ({ kind, entries: items.filter(({ item }) => item.kind === kind) })).filter((g) => g.entries.length);
  return (
    <div className="mt-3 flex flex-col gap-3">
      <div className="flex flex-wrap gap-2 text-xs">
        {groups.map(({ kind, entries }) => (
          <Badge key={kind} tone={KIND_INFO[kind].tone}>
            {KIND_INFO[kind].icon} {KIND_INFO[kind].label}: {entries.length}
          </Badge>
        ))}
      </div>
      {groups
        .filter(({ kind }) => kind === "character")
        .flatMap(({ entries }) => entries)
        .map(({ item, index }) => (
          <CharacterDraftCard key={index} campaignId={campaignId} documentId={document.id} index={index} item={item} />
        ))}
      {groups
        .filter(({ kind }) => kind !== "character" && (showAll || (kind !== "marker" && kind !== "ignored")))
        .map(({ kind, entries }) => (
          <details key={kind} open={kind === "map" || kind === "adventure"} className="rounded border border-line/60 p-2">
            <summary className="cursor-pointer text-sm">
              {KIND_INFO[kind].icon} {KIND_INFO[kind].label} ({entries.length})
            </summary>
            <ul className="mt-2 flex flex-col gap-1 text-sm">
              {entries.map(({ item, index }) => (
                <li key={index} className="flex flex-wrap items-baseline gap-2">
                  <span className="font-serif">{item.name}</span>
                  {item.variant && VARIANT_LABEL[item.variant] && <Badge>{VARIANT_LABEL[item.variant]}</Badge>}
                  <Badge tone={item.status === "error" ? "blood" : item.status === "done" ? "moss" : "default"}>{STATUS_LABEL[item.status]}</Badge>
                  <span className="text-xs text-parchment-dim">{item.reason}</span>
                  {item.warnings.map((w, i) => (
                    <span key={i} className="text-xs text-gold">
                      {w}
                    </span>
                  ))}
                  <span className="w-full truncate text-xs text-parchment-dim/70">{item.path}</span>
                </li>
              ))}
            </ul>
          </details>
        ))}
      {groups.some(({ kind }) => kind === "marker" || kind === "ignored") && (
        <button type="button" className="self-start text-xs text-parchment-dim underline" onClick={() => setShowAll(!showAll)}>
          {showAll ? "Ocultar marcadores e ignorados" : "Ver también marcadores e ignorados"}
        </button>
      )}
    </div>
  );
}

function CharacterDraftCard({ campaignId, documentId, index, item }: { campaignId: string; documentId: string; index: number; item: ImportItem }) {
  const confirm = useCampaignMutation<{ overrides: { name: string } }>(campaignId, "POST", () => `/documents/${documentId}/items/${index}/confirm`);
  const dismiss = useCampaignMutation<Record<string, never>>(campaignId, "POST", () => `/documents/${documentId}/items/${index}/dismiss`);
  const draft = item.draft as CharacterDraft | undefined;
  const [name, setName] = useState(draft?.name ?? item.name);
  if (!draft) return null;
  const pending = item.status === "draft";
  return (
    <div className={`rounded border p-3 ${pending ? "border-moss" : "border-line opacity-70"}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xl">🧝</span>
        {pending ? (
          <input className="rounded border border-line bg-ink-3 px-2 py-1 font-serif text-lg" value={name} onChange={(e) => setName(e.target.value)} aria-label="Nombre del personaje" />
        ) : (
          <span className="font-serif text-lg">{draft.name}</span>
        )}
        <span className="text-sm text-parchment-dim">
          {[draft.race, `${draft.char_class} ${draft.level}`, draft.subclass, draft.background].filter(Boolean).join(" · ")}
        </span>
        <Badge tone={pending ? "gold" : item.status === "done" ? "moss" : "default"}>{STATUS_LABEL[item.status]}</Badge>
        <span className="text-xs text-parchment-dim">{item.reason}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-sm">
        <span>PG {draft.hp_max}</span>
        <span>CA {draft.armor_class}</span>
        <span>{draft.speed_ft} pies</span>
        {ABILITIES.map((a) => (
          <span key={a.key}>
            {a.short} {draft.sheet.abilities[a.key]}
          </span>
        ))}
      </div>
      <p className="mt-1 text-xs text-parchment-dim">
        Competencias: {draft.sheet.skill_proficiencies.map((s) => SKILLS[s]?.label ?? s).join(", ") || "—"}
        {draft.sheet.skill_expertise.length > 0 && ` · Pericia: ${draft.sheet.skill_expertise.map((s) => SKILLS[s]?.label ?? s).join(", ")}`}
        {" · "}
        {draft.sheet.attacks.length} ataques · {draft.sheet.spells.length} conjuros · {draft.sheet.features.length} rasgos
        {draft.sheet.languages.length > 0 && ` · Idiomas: ${draft.sheet.languages.join(", ")}`}
      </p>
      {item.warnings.map((w, i) => (
        <p key={i} className="text-xs text-gold">
          ⚠ {w}
        </p>
      ))}
      {pending && (
        <div className="mt-2 flex gap-2">
          <Button variant="primary" onClick={() => confirm.mutate({ overrides: { name } })} disabled={confirm.isPending}>
            Crear personaje
          </Button>
          <Button variant="ghost" onClick={() => dismiss.mutate({})}>
            Descartar
          </Button>
          <span className="self-center text-xs text-parchment-dim">Después podrás asignarlo a un jugador y corregir la ficha en «Personajes».</span>
        </div>
      )}
      <ErrorText error={confirm.error} />
    </div>
  );
}

export function documentKindLabel(document: DocumentInfo): string {
  return DOCUMENT_KIND[document.kind] ?? document.kind;
}
