import { useEvents } from "../../api/hooks";
import { Badge, Panel } from "../../components/ui";
import { eventSummary } from "../../lib/events";

export function DmLog({ campaignId }: { campaignId: string }) {
  const events = useEvents(campaignId);
  return (
    <Panel title="Registro completo de eventos (incluye los del DM)">
      <ul className="flex max-h-[75vh] flex-col gap-1 overflow-auto font-mono text-xs scroll-thin">
        {[...(events.data ?? [])].reverse().map((e) => (
          <li key={e.id} className="border-b border-line/30 py-1">
            <span className="text-parchment-dim">#{e.seq}</span> <Badge tone={e.visibility === "public" ? "default" : "blood"}>{e.visibility}</Badge>{" "}
            <Badge>{e.actor_kind}</Badge> <strong>{e.type}</strong> {eventSummary(e) ?? ""}
            {(e.type === "ai_decision" || e.type === "leak_blocked" || e.type === "narration") && (
              <pre className="mt-1 whitespace-pre-wrap text-parchment-dim">{JSON.stringify(e.payload, null, 1).slice(0, 1200)}</pre>
            )}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
