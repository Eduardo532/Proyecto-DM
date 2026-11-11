import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { useDmStore } from "../stores/dm";
import { useTableStore } from "../stores/table";

/**
 * Conexión en tiempo real con la mesa. Cada evento invalida las consultas de la campaña para
 * que la interfaz muestre el estado nuevo. Se reconecta sola si se corta.
 */
export function useTableSocket(campaignId: string): void {
  const client = useQueryClient();
  const token = useDmStore((s) => s.tokens[campaignId]);
  const setAi = useTableStore((s) => s.setAi);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let ping: ReturnType<typeof setInterval> | undefined;
    let closed = false;
    let pending: ReturnType<typeof setTimeout> | undefined;

    const refresh = () => {
      clearTimeout(pending);
      pending = setTimeout(() => client.invalidateQueries({ queryKey: ["c", campaignId] }), 120);
    };

    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const query = token ? `?dm_token=${encodeURIComponent(token)}` : "";
      socket = new WebSocket(`${protocol}://${window.location.host}/ws/campaigns/${campaignId}${query}`);
      socket.onmessage = (message) => {
        const data = JSON.parse(String(message.data)) as { kind: string; busy?: boolean; text?: string };
        if (data.kind === "ai_status") {
          setAi(Boolean(data.busy), data.text ?? "");
        } else if (data.kind === "event") {
          refresh();
        }
      };
      socket.onopen = () => {
        ping = setInterval(() => socket?.readyState === WebSocket.OPEN && socket.send("ping"), 25_000);
        refresh();
      };
      socket.onclose = () => {
        clearInterval(ping);
        if (!closed) retry = setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      clearTimeout(pending);
      clearInterval(ping);
      socket?.close();
    };
  }, [campaignId, token, client, setAi]);
}
