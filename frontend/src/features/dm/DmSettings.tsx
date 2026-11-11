import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { keys, useAiStatus, useCampaign, useSession } from "../../api/hooks";
import { Badge, Button, ErrorText, Field, Input, Panel, Select } from "../../components/ui";

export function DmSettings({ campaignId }: { campaignId: string }) {
  const campaign = useCampaign(campaignId);
  const session = useSession(campaignId);
  const ai = useAiStatus();
  const client = useQueryClient();
  const [pin, setPin] = useState("");
  const refresh = () => {
    client.invalidateQueries({ queryKey: ["c", campaignId] });
    client.invalidateQueries({ queryKey: keys.campaign(campaignId) });
  };
  const update = useMutation({
    mutationFn: (body: Record<string, unknown>) => api(`/campaigns/${campaignId}`, { method: "PATCH", body, campaignId }),
    onSettled: refresh,
  });
  const setPinMutation = useMutation({
    mutationFn: () => api(`/campaigns/${campaignId}/dm/pin`, { method: "PUT", body: { pin }, campaignId }),
    onSuccess: () => setPin(""),
    onSettled: refresh,
  });
  const pause = useMutation({
    mutationFn: (paused: boolean) => api(`/campaigns/${campaignId}/sessions/${session.data?.id}`, { method: "PATCH", body: { ai_paused: paused }, campaignId }),
    onSettled: refresh,
  });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Inteligencia artificial">
        {ai.data && (
          <ul className="text-sm">
            <li>
              Proveedor: <strong>{ai.data.provider}</strong> {ai.data.ready ? <Badge tone="moss">listo</Badge> : <Badge tone="blood">no disponible</Badge>}
            </li>
            {ai.data.model && <li>Modelo: {ai.data.model}</li>}
            {ai.data.missing?.length ? <li>Faltan: {ai.data.missing.join(", ")}</li> : null}
          </ul>
        )}
        {session.data && (
          <Button className="mt-3" variant={session.data.ai_paused ? "primary" : "danger"} onClick={() => pause.mutate(!session.data?.ai_paused)}>
            {session.data.ai_paused ? "Reanudar la IA" : "Pausar la IA (dirijo yo)"}
          </Button>
        )}
        <ErrorText error={pause.error} />
      </Panel>
      <Panel title="Campaña">
        <div className="flex flex-col gap-3">
          <Field label="Dados">
            <Select value={campaign.data?.dice_mode ?? "ask"} onChange={(e) => update.mutate({ dice_mode: e.target.value })}>
              <option value="ask">Elegir en cada tirada</option>
              <option value="digital">Siempre digitales</option>
              <option value="manual">Siempre físicos</option>
            </Select>
          </Field>
          <form
            className="flex items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setPinMutation.mutate();
            }}
          >
            <Field label="Nuevo PIN del DM (vacío = sin PIN)">
              <Input type="password" value={pin} onChange={(e) => setPin(e.target.value)} />
            </Field>
            <Button>Cambiar PIN</Button>
          </form>
          <ErrorText error={update.error ?? setPinMutation.error} />
        </div>
      </Panel>
    </div>
  );
}
