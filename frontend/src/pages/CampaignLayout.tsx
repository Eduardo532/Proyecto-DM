import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, NavLink, Route, Routes, useNavigate, useParams } from "react-router-dom";

import { api } from "../api/client";
import { useCampaign, useSession } from "../api/hooks";
import type { GameSession } from "../api/types";
import { Button, ErrorText, Input } from "../components/ui";
import { CharactersView } from "../features/characters/CharactersView";
import { DmView } from "../features/dm/DmView";
import { JournalView } from "../features/table/JournalView";
import { MapView } from "../features/maps/MapView";
import { TableView } from "../features/table/TableView";
import { useTableSocket } from "../hooks/useTableSocket";
import { useDmStore, useIsDm } from "../stores/dm";
import { AiBanner } from "./Library";

export function CampaignLayout() {
  const { campaignId = "" } = useParams();
  const campaign = useCampaign(campaignId);
  const isDm = useIsDm(campaignId);
  const [gate, setGate] = useState(false);
  const [fading, setFading] = useState(false);
  const logout = useDmStore((s) => s.logout);
  const client = useQueryClient();
  const navigate = useNavigate();
  useTableSocket(campaignId);

  const exitDm = () => {
    setFading(true);
    const token = useDmStore.getState().tokens[campaignId];
    if (token) void fetch(`/api/campaigns/${campaignId}/dm/logout`, { method: "POST", headers: { "X-DM-Token": token } });
    logout(campaignId);
    client.removeQueries({ queryKey: ["c", campaignId, "dm"] });
    navigate(`/c/${campaignId}`);
    setTimeout(() => setFading(false), 900);
  };

  const tab = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 font-display text-sm uppercase tracking-wide ${isActive ? "border-b-2 border-gold text-gold" : "text-parchment-dim hover:text-parchment"}`;

  return (
    <div className="flex h-full flex-col">
      <header className={`flex flex-wrap items-center gap-4 border-b px-4 py-2 ${isDm ? "border-blood bg-[#2a1515]" : "border-line bg-ink-2"}`}>
        <Link to="/" className="font-display text-gold" title="Volver a la biblioteca">
          🐉
        </Link>
        <h1 className="font-display text-lg">{campaign.data?.name ?? "…"}</h1>
        <nav className="flex gap-1">
          <NavLink end to={`/c/${campaignId}`} className={tab}>
            Mesa
          </NavLink>
          <NavLink to={`/c/${campaignId}/mapa`} className={tab}>
            Mapa
          </NavLink>
          <NavLink to={`/c/${campaignId}/personajes`} className={tab}>
            Personajes
          </NavLink>
          <NavLink to={`/c/${campaignId}/diario`} className={tab}>
            Diario
          </NavLink>
          {isDm && (
            <NavLink to={`/c/${campaignId}/dm`} className={tab}>
              Panel DM
            </NavLink>
          )}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <SessionControls campaignId={campaignId} />
          {isDm ? (
            <Button variant="danger" onClick={exitDm}>
              Salir del modo DM
            </Button>
          ) : (
            <Button onClick={() => setGate(true)}>🔒 Modo DM</Button>
          )}
        </div>
      </header>
      <div className="px-4 pt-3">
        <AiBanner />
      </div>
      <main className="min-h-0 flex-1 overflow-auto px-4 pb-4 scroll-thin">
        <Routes>
          <Route index element={<TableView campaignId={campaignId} />} />
          <Route path="mapa" element={<MapView campaignId={campaignId} />} />
          <Route path="personajes" element={<CharactersView campaignId={campaignId} />} />
          <Route path="diario" element={<JournalView campaignId={campaignId} />} />
          <Route path="dm/*" element={isDm ? <DmView campaignId={campaignId} /> : <p className="p-6">Hace falta el modo DM.</p>} />
        </Routes>
      </main>
      {gate && (
        <DmGate
          campaignId={campaignId}
          onClose={() => setGate(false)}
          onDone={() => {
            setGate(false);
            navigate(`/c/${campaignId}/dm`);
          }}
        />
      )}
      {fading && <div className="pointer-events-none fixed inset-0 z-50 bg-black transition-opacity duration-700" />}
    </div>
  );
}

function SessionControls({ campaignId }: { campaignId: string }) {
  const session = useSession(campaignId);
  const client = useQueryClient();
  const start = useMutation({
    mutationFn: () => api<GameSession>(`/campaigns/${campaignId}/sessions`, { method: "POST", campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const close = useMutation({
    mutationFn: (id: string) => api<GameSession>(`/campaigns/${campaignId}/sessions/${id}/close`, { method: "POST", body: {}, campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const current = session.data;
  if (!current) {
    return (
      <Button variant="primary" onClick={() => start.mutate()} disabled={start.isPending}>
        Iniciar sesión
      </Button>
    );
  }
  return (
    <div className="flex items-center gap-2 text-sm text-parchment-dim">
      <span>
        Sesión {current.number} · {stateLabel(current.state)}
      </span>
      <Button
        onClick={() => {
          if (window.confirm("¿Cerrar la sesión? Se generará el resumen.")) close.mutate(current.id);
        }}
        disabled={close.isPending}
      >
        {close.isPending ? "Resumiendo…" : "Cerrar sesión"}
      </Button>
    </div>
  );
}

export function stateLabel(state: string): string {
  return (
    { exploring: "exploración", awaiting_roll: "esperando tirada", combat: "combate", paused: "en pausa", closed: "cerrada" }[state] ??
    state
  );
}

function DmGate({ campaignId, onClose, onDone }: { campaignId: string; onClose: () => void; onDone: () => void }) {
  const [pin, setPin] = useState("");
  const login = useDmStore((s) => s.login);
  const mutation = useMutation({
    mutationFn: () => api<{ token: string }>(`/campaigns/${campaignId}/dm/login`, { method: "POST", body: { pin } }),
    onSuccess: (data) => {
      login(campaignId, data.token);
      onDone();
    },
  });
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink">
      <form
        className="w-full max-w-sm rounded-lg border border-blood bg-ink-2 p-6 text-center"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <p className="text-4xl">🔒</p>
        <h2 className="mt-2 font-display text-xl text-gold">Modo DM</h2>
        <p className="mt-2 text-sm text-parchment-dim">
          Vas a ver los secretos de la aventura. Que los jugadores no miren la pantalla.
        </p>
        <Input className="mt-4 text-center" type="password" placeholder="PIN" value={pin} onChange={(e) => setPin(e.target.value)} autoFocus />
        <ErrorText error={mutation.error} />
        <div className="mt-4 flex justify-center gap-2">
          <Button type="button" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="danger" disabled={mutation.isPending}>
            Entrar
          </Button>
        </div>
      </form>
    </div>
  );
}
