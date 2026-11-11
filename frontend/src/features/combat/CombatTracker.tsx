import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { CombatView } from "../../api/types";
import { Badge, Button, ErrorText, Panel } from "../../components/ui";
import { useIsDm } from "../../stores/dm";

export function CombatTracker({ campaignId, combat }: { campaignId: string; combat: CombatView }) {
  const dm = useIsDm(campaignId);
  const client = useQueryClient();
  const refresh = () => client.invalidateQueries({ queryKey: ["c", campaignId] });
  const next = useMutation({ mutationFn: () => api(`/campaigns/${campaignId}/combat/next`, { method: "POST", campaignId }), onSettled: refresh });
  const spend = useMutation({
    mutationFn: (body: { entity_id: string; kind: string; action?: string }) => api(`/campaigns/${campaignId}/combat/action`, { method: "POST", body, campaignId }),
    onSettled: refresh,
  });
  const end = useMutation({ mutationFn: () => api(`/campaigns/${campaignId}/combat/end`, { method: "POST", campaignId }), onSettled: refresh });
  const current = combat.order.find((c) => c.entity_id === combat.current_entity_id);
  const budget = current?.budget;

  return (
    <Panel title={`Combate · ronda ${combat.round}`} actions={dm && <Button variant="danger" onClick={() => end.mutate()}>Terminar</Button>}>
      <ol className="flex flex-col gap-1">
        {combat.order.map((c) => (
          <li
            key={c.entity_id}
            className={`flex items-center justify-between rounded px-2 py-1 ${c.entity_id === combat.current_entity_id ? "bg-gold/20 ring-1 ring-gold" : ""} ${c.removed ? "line-through opacity-50" : ""}`}
          >
            <span>
              {c.name} {c.disposition === "hostile" && <Badge tone="blood">enemigo</Badge>}
            </span>
            <span className="tabular-nums text-parchment-dim">{c.initiative}</span>
          </li>
        ))}
      </ol>
      {current && budget && (
        <div className="mt-3 rounded border border-line p-2 text-sm">
          <p className="mb-2">
            Turno de <strong>{current.name}</strong> · movimiento restante {budget.movement_ft} pies
          </p>
          <div className="flex flex-wrap gap-1">
            <Button disabled={!budget.action} onClick={() => spend.mutate({ entity_id: current.entity_id, kind: "action" })}>
              Acción {budget.action ? "✓" : "✗"}
            </Button>
            <Button disabled={!budget.bonus} onClick={() => spend.mutate({ entity_id: current.entity_id, kind: "bonus" })}>
              Adicional {budget.bonus ? "✓" : "✗"}
            </Button>
            <Button disabled={!budget.action} onClick={() => spend.mutate({ entity_id: current.entity_id, kind: "action", action: "dash" })}>
              Correr
            </Button>
            <Button disabled={!budget.action} onClick={() => spend.mutate({ entity_id: current.entity_id, kind: "action", action: "disengage" })}>
              Retirarse
            </Button>
          </div>
        </div>
      )}
      <Button variant="primary" className="mt-3 w-full" onClick={() => next.mutate()} disabled={next.isPending}>
        Terminar turno →
      </Button>
      <ErrorText error={next.error ?? spend.error ?? end.error} />
    </Panel>
  );
}
