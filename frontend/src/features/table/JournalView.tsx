import { useFacts, useMemory, useNpcs, useQuests, useSessions } from "../../api/hooks";
import { Empty, Panel } from "../../components/ui";

export function JournalView({ campaignId }: { campaignId: string }) {
  const sessions = useSessions(campaignId);
  const facts = useFacts(campaignId);
  const npcs = useNpcs(campaignId);
  const quests = useQuests(campaignId);
  const memory = useMemory(campaignId);
  return (
    <div className="grid gap-4 pt-1 lg:grid-cols-2">
      <Panel title="Sesiones">
        {sessions.data?.filter((s) => s.state === "closed").length ? (
          <ul className="flex flex-col gap-4">
            {sessions.data
              .filter((s) => s.state === "closed")
              .map((s) => {
                const summary = s.summary as { situacion_final?: string; acontecimientos?: string[] };
                return (
                  <li key={s.id}>
                    <h3 className="font-display text-gold">Sesión {s.number}</h3>
                    <ul className="ml-4 list-disc font-serif">
                      {(summary.acontecimientos ?? []).slice(0, 8).map((line, i) => (
                        <li key={i}>{line}</li>
                      ))}
                    </ul>
                    {summary.situacion_final && <p className="mt-1 font-serif italic">{summary.situacion_final}</p>}
                  </li>
                );
              })}
          </ul>
        ) : (
          <Empty>Aún no hay sesiones cerradas.</Empty>
        )}
      </Panel>
      <div className="flex flex-col gap-4">
        <Panel title="Lo que sabemos">
          {facts.data?.length ? (
            <ul className="flex flex-col gap-1 font-serif">
              {facts.data.map((f) => (
                <li key={f.id}>• {f.statement}</li>
              ))}
            </ul>
          ) : (
            <Empty>Nada todavía.</Empty>
          )}
        </Panel>
        <Panel title="Personajes conocidos">
          {npcs.data?.length ? (
            <ul className="flex flex-col gap-1">
              {npcs.data.map((n) => (
                <li key={n.id}>
                  <strong className="font-serif">{n.name}</strong> — {n.description ?? n.public_description}
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Nadie todavía.</Empty>
          )}
        </Panel>
        <Panel title="Misiones">
          {quests.data?.length ? quests.data.map((q) => <p key={q.id} className="font-serif">{q.title} ({q.status})</p>) : <Empty>Ninguna.</Empty>}
        </Panel>
        <Panel title="Recuerdos">
          {memory.data?.length ? memory.data.map((m) => <p key={m.id} className="font-serif">• {m.content}</p>) : <Empty>Ninguno.</Empty>}
        </Panel>
      </div>
    </div>
  );
}
