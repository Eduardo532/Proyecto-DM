import { useState } from "react";

import { useCampaignMutation, useCharacters, useFacts, useMemory, useQuests, useScenes } from "../../api/hooks";
import type { Fact, Quest } from "../../api/types";
import { Badge, Button, Empty, ErrorText, Input, Panel, Select, TextArea } from "../../components/ui";
import { KNOWLEDGE_LABELS, SKILLS } from "../../lib/rules";

export function DmFacts({ campaignId }: { campaignId: string }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <FactsPanel campaignId={campaignId} />
      <div className="flex flex-col gap-4">
        <QuestsPanel campaignId={campaignId} />
        <MemoryPanel campaignId={campaignId} />
      </div>
    </div>
  );
}

function FactsPanel({ campaignId }: { campaignId: string }) {
  const facts = useFacts(campaignId);
  const scenes = useScenes(campaignId);
  const characters = useCharacters(campaignId);
  const [form, setForm] = useState({ statement: "", scene_id: "", knowledge_level: "conditional", skill: "perception", dc: 15, keywords: "" });
  const create = useCampaignMutation<Record<string, unknown>>(campaignId, "POST", "/facts");
  const reveal = useCampaignMutation<{ id: string; to: string; character_id?: string }>(campaignId, "POST", (b) => `/facts/${b.id}/reveal`);
  const remove = useCampaignMutation<string>(campaignId, "DELETE", (id) => `/facts/${id}`);
  const [target, setTarget] = useState("party");

  return (
    <Panel title="Hechos y secretos">
      <form
        className="mb-4 flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate(
            {
              statement: form.statement,
              scene_id: form.scene_id || null,
              knowledge_level: form.knowledge_level,
              discovery: form.knowledge_level === "conditional" ? { skill: form.skill, dc: form.dc } : {},
              keywords: form.keywords.split(",").map((k) => k.trim()).filter(Boolean),
            },
            { onSuccess: () => setForm({ ...form, statement: "", keywords: "" }) },
          );
        }}
      >
        <TextArea rows={2} required placeholder="Hecho (p. ej. «Tras el tapiz hay una palanca»)" value={form.statement} onChange={(e) => setForm({ ...form, statement: e.target.value })} />
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Select value={form.scene_id} onChange={(e) => setForm({ ...form, scene_id: e.target.value })}>
            <option value="">Cualquier escena</option>
            {scenes.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
          <Select value={form.knowledge_level} onChange={(e) => setForm({ ...form, knowledge_level: e.target.value })}>
            <option value="conditional">Descubrible con prueba</option>
            <option value="dm">Solo DM</option>
            <option value="public">Público</option>
          </Select>
          {form.knowledge_level === "conditional" && (
            <>
              <Select value={form.skill} onChange={(e) => setForm({ ...form, skill: e.target.value })}>
                {Object.entries(SKILLS).map(([key, info]) => (
                  <option key={key} value={key}>
                    {info.label}
                  </option>
                ))}
              </Select>
              <Input type="number" min={5} max={30} value={form.dc} onChange={(e) => setForm({ ...form, dc: Number(e.target.value) })} title="CD" />
            </>
          )}
        </div>
        <Input placeholder="Palabras que delatarían el secreto (separadas por comas)" value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} />
        <Button variant="primary">Añadir hecho</Button>
        <ErrorText error={create.error ?? reveal.error} />
      </form>
      <div className="mb-2 flex items-center gap-2 text-sm">
        Revelar a:
        <Select value={target} onChange={(e) => setTarget(e.target.value)} className="w-56">
          <option value="party">Todo el grupo</option>
          {characters.data?.map((c) => (
            <option key={c.id} value={c.id}>
              Solo {c.name}
            </option>
          ))}
        </Select>
      </div>
      {facts.data?.length === 0 && <Empty>Sin hechos registrados.</Empty>}
      <ul className="flex max-h-[60vh] flex-col gap-2 overflow-auto scroll-thin">
        {facts.data?.map((f: Fact) => (
          <li key={f.id} className="rounded border border-line p-2 text-sm">
            <div className="mb-1 flex flex-wrap items-center gap-1">
              <Badge tone={f.knowledge_level === "public" ? "moss" : f.knowledge_level === "conditional" ? "gold" : "blood"}>{KNOWLEDGE_LABELS[f.knowledge_level]}</Badge>
              {typeof f.discovery.dc === "number" && (
                <Badge>
                  {SKILLS[String(f.discovery.skill)]?.label ?? "prueba"} CD {String(f.discovery.dc)}
                </Badge>
              )}
              <Badge>{f.source}</Badge>
              <span className="ml-auto flex gap-1">
                <Button onClick={() => reveal.mutate(target === "party" ? { id: f.id, to: "party" } : { id: f.id, to: "character", character_id: target })}>Revelar</Button>
                <Button variant="subtle" onClick={() => window.confirm("¿Borrar el hecho?") && remove.mutate(f.id)}>
                  ✕
                </Button>
              </span>
            </div>
            <p className="font-serif">{f.statement}</p>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function QuestsPanel({ campaignId }: { campaignId: string }) {
  const quests = useQuests(campaignId);
  const [editing, setEditing] = useState<Partial<Quest> | null>(null);
  const save = useCampaignMutation<Partial<Quest>>(campaignId, editing?.id ? "PUT" : "POST", editing?.id ? `/quests/${editing.id}` : "/quests");
  return (
    <Panel title="Misiones" actions={<Button onClick={() => setEditing({ title: "", status: "unknown" })}>Nueva</Button>}>
      <ul className="flex flex-col gap-1">
        {quests.data?.map((q) => (
          <li key={q.id}>
            <button className="hover:text-gold" onClick={() => setEditing(q)}>
              {q.title}
            </button>{" "}
            <Badge>{q.status}</Badge>
          </li>
        ))}
      </ul>
      {editing && (
        <form
          className="mt-3 flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(editing, { onSuccess: () => setEditing(null) });
          }}
        >
          <Input required placeholder="Título" value={editing.title ?? ""} onChange={(e) => setEditing({ ...editing, title: e.target.value })} />
          <TextArea rows={2} placeholder="Descripción para la mesa" value={editing.description_public ?? ""} onChange={(e) => setEditing({ ...editing, description_public: e.target.value })} />
          <TextArea rows={2} placeholder="Notas del DM" value={editing.description_dm ?? ""} onChange={(e) => setEditing({ ...editing, description_dm: e.target.value })} />
          <Select value={editing.status ?? "unknown"} onChange={(e) => setEditing({ ...editing, status: e.target.value })}>
            <option value="unknown">Desconocida</option>
            <option value="offered">Ofrecida</option>
            <option value="active">Activa</option>
            <option value="completed">Completada</option>
            <option value="failed">Fallida</option>
          </Select>
          <ErrorText error={save.error} />
          <div className="flex justify-end gap-2">
            <Button type="button" onClick={() => setEditing(null)}>
              Cancelar
            </Button>
            <Button variant="primary">Guardar</Button>
          </div>
        </form>
      )}
    </Panel>
  );
}

function MemoryPanel({ campaignId }: { campaignId: string }) {
  const memory = useMemory(campaignId);
  const [content, setContent] = useState("");
  const create = useCampaignMutation<Record<string, unknown>>(campaignId, "POST", "/memory");
  const correct = useCampaignMutation<{ id: string; content: string; scope: string; visibility: string; importance: number }>(campaignId, "PUT", (b) => `/memory/${b.id}`);
  return (
    <Panel title="Memoria de la campaña">
      <form
        className="mb-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate({ content, scope: "campaign", importance: 3 }, { onSuccess: () => setContent("") });
        }}
      >
        <Input placeholder="Añadir recuerdo…" value={content} onChange={(e) => setContent(e.target.value)} required />
        <Button variant="primary">+</Button>
      </form>
      <ul className="flex max-h-80 flex-col gap-1 overflow-auto text-sm scroll-thin">
        {memory.data?.map((m) => (
          <li key={m.id} className="flex items-start gap-2">
            <Badge>{m.scope}</Badge>
            <span
              className="flex-1 cursor-text"
              title="Doble clic para corregir"
              onDoubleClick={() => {
                const text = window.prompt("Corregir recuerdo", m.content);
                if (text && text !== m.content) correct.mutate({ id: m.id, content: text, scope: m.scope, visibility: m.visibility, importance: m.importance });
              }}
            >
              {m.content}
            </span>
            {m.visibility === "dm" && <Badge tone="blood">DM</Badge>}
          </li>
        ))}
      </ul>
      <ErrorText error={create.error ?? correct.error} />
    </Panel>
  );
}
