import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { keys, useAiStatus, useCampaigns } from "../api/hooks";
import type { Campaign } from "../api/types";
import { Button, Empty, ErrorText, Field, Input, Modal, Panel, Select, TextArea } from "../components/ui";

export function Library() {
  const campaigns = useCampaigns();
  const ai = useAiStatus();
  const [creating, setCreating] = useState(false);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-10 text-center">
        <p className="text-5xl">🐉</p>
        <h1 className="font-display text-4xl text-gold">Virtual Dungeon Master</h1>
        <p className="mt-2 font-serif text-lg italic text-parchment-dim">Dungeons &amp; Dragons 5e · dirigido por IA, en tu mesa</p>
      </header>

      <AiBanner />

      <Panel
        title="Campañas"
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            Nueva campaña
          </Button>
        }
      >
        {campaigns.isLoading && <Empty>Cargando…</Empty>}
        <ErrorText error={campaigns.error} />
        {campaigns.data?.length === 0 && <Empty>Aún no hay campañas. Crea la primera para empezar.</Empty>}
        <ul className="grid gap-4 sm:grid-cols-2">
          {campaigns.data?.map((c) => (
            <li key={c.id}>
              <Link
                to={`/c/${c.id}`}
                className="block rounded-lg border border-line bg-ink-3/60 p-4 transition hover:border-gold"
              >
                <h3 className="font-display text-lg text-parchment">{c.name}</h3>
                <p className="mt-1 line-clamp-2 font-serif text-parchment-dim">{c.description || "Sin descripción."}</p>
                <p className="mt-3 text-xs text-parchment-dim">
                  Actualizada {new Date(c.updated_at).toLocaleString("es")} · dados {c.dice_mode}
                  {c.has_dm_pin ? " · 🔒 PIN" : ""}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </Panel>
      {ai.data && !ai.data.ready && (
        <p className="mt-6 text-center text-sm text-parchment-dim">
          Sin IA puedes preparar campañas, fichas y mapas; la narración se activa cuando Ollama esté listo.
        </p>
      )}
      {creating && <CreateCampaign onClose={() => setCreating(false)} />}
    </main>
  );
}

export function AiBanner() {
  const ai = useAiStatus();
  if (!ai.data || ai.data.ready) return null;
  const text = !ai.data.reachable
    ? "No se puede contactar con Ollama. ¿Está en marcha?"
    : `Faltan modelos en Ollama: ${(ai.data.missing ?? []).join(", ")}. Se están descargando o hay que ejecutar «ollama pull».`;
  return <div className="mb-6 rounded-md border border-gold-dim bg-gold/10 px-4 py-3 text-sm text-gold">⚠ {text}</div>;
}

function CreateCampaign({ onClose }: { onClose: () => void }) {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", description: "", dice_mode: "ask", dm_pin: "" });
  const create = useMutation({
    mutationFn: () =>
      api<Campaign>("/campaigns", {
        method: "POST",
        body: { ...form, dm_pin: form.dm_pin || null },
      }),
    onSuccess: (campaign) => {
      client.invalidateQueries({ queryKey: keys.campaigns });
      navigate(`/c/${campaign.id}`);
    },
  });
  return (
    <Modal title="Nueva campaña" onClose={onClose}>
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <Field label="Nombre">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoFocus />
        </Field>
        <Field label="Descripción">
          <TextArea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Dados">
          <Select value={form.dice_mode} onChange={(e) => setForm({ ...form, dice_mode: e.target.value })}>
            <option value="ask">Elegir en cada tirada (físicos o digitales)</option>
            <option value="digital">Siempre digitales</option>
            <option value="manual">Siempre físicos</option>
          </Select>
        </Field>
        <Field label="PIN del modo DM (opcional, mínimo 4 caracteres)">
          <Input
            type="password"
            minLength={4}
            value={form.dm_pin}
            onChange={(e) => setForm({ ...form, dm_pin: e.target.value })}
            placeholder="Protege los secretos de la aventura"
          />
        </Field>
        <ErrorText error={create.error} />
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" disabled={create.isPending}>
            Crear
          </Button>
        </div>
      </form>
    </Modal>
  );
}
