import { useDmStore } from "../stores/dm";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function dmHeaders(campaignId?: string): Record<string, string> {
  if (!campaignId) return {};
  const token = useDmStore.getState().tokens[campaignId];
  return token ? { "X-DM-Token": token } : {};
}

function describe(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
      .join(" · ");
  }
  return "Error inesperado";
}

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; campaignId?: string; form?: FormData } = {},
): Promise<T> {
  const headers: Record<string, string> = { ...dmHeaders(options.campaignId) };
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  const response = await fetch(`/api${path}`, { method: options.method ?? "GET", headers, body });
  if (response.status === 403 && options.campaignId && useDmStore.getState().tokens[options.campaignId]) {
    // El token del DM caducó: se sale del modo DM sin mostrar nada.
    useDmStore.getState().logout(options.campaignId);
  }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (data.detail !== undefined) message = describe(data.detail);
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function imageUrl(campaignId: string, path: string): string {
  const token = useDmStore.getState().tokens[campaignId];
  const separator = path.includes("?") ? "&" : "?";
  return `/api/campaigns/${campaignId}${path}${token ? `${separator}dm_token=${encodeURIComponent(token)}` : ""}`;
}
