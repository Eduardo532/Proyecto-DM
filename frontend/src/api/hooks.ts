import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useIsDm } from "../stores/dm";
import { api } from "./client";
import type {
  AiStatus,
  Campaign,
  Character,
  CombatView,
  EntityView,
  Fact,
  GameEvent,
  GameMap,
  GameSession,
  MemoryEntry,
  Npc,
  Player,
  Quest,
  Roll,
  Scene,
  Marker,
} from "./types";

/** Claves de caché: la del DM y la de la mesa se separan para no mezclar datos. */
export const keys = {
  campaigns: ["campaigns"] as const,
  campaign: (id: string) => ["campaign", id] as const,
  scoped: (id: string, dm: boolean, name: string, extra?: unknown) =>
    ["c", id, dm ? "dm" : "mesa", name, extra ?? null] as const,
};

export function useCampaigns() {
  return useQuery({ queryKey: keys.campaigns, queryFn: () => api<Campaign[]>("/campaigns") });
}

export function useCampaign(id: string) {
  return useQuery({ queryKey: keys.campaign(id), queryFn: () => api<Campaign>(`/campaigns/${id}`) });
}

function useScoped<T>(campaignId: string, name: string, path: string, extra?: unknown, enabled = true) {
  const dm = useIsDm(campaignId);
  return useQuery({
    queryKey: keys.scoped(campaignId, dm, name, extra),
    queryFn: () => api<T>(`/campaigns/${campaignId}${path}`, { campaignId }),
    enabled,
  });
}

export const usePlayers = (id: string) => useScoped<Player[]>(id, "players", "/players");
export const useCharacters = (id: string) => useScoped<Character[]>(id, "characters", "/characters");
export const useSession = (id: string) => useScoped<GameSession | null>(id, "session", "/sessions/current");
export const useSessions = (id: string) => useScoped<GameSession[]>(id, "sessions", "/sessions");
export const useEvents = (id: string) => useScoped<GameEvent[]>(id, "events", "/events?limit=300");
export const usePendingRolls = (id: string) => useScoped<Roll[]>(id, "rolls", "/rolls?status=pending");
export const useScenes = (id: string) => useScoped<Scene[]>(id, "scenes", "/scenes");
export const useMaps = (id: string) => useScoped<GameMap[]>(id, "maps", "/maps");
export const useMarkers = (id: string) => useScoped<Marker[]>(id, "markers", "/markers");
export const useFacts = (id: string) => useScoped<Fact[]>(id, "facts", "/facts");
export const useNpcs = (id: string) => useScoped<Npc[]>(id, "npcs", "/npcs");
export const useQuests = (id: string) => useScoped<Quest[]>(id, "quests", "/quests");
export const useMemory = (id: string) => useScoped<MemoryEntry[]>(id, "memory", "/memory");
export const useCombat = (id: string) => useScoped<CombatView | null>(id, "combat", "/combat");

export function useMap(campaignId: string, mapId: string | null | undefined) {
  return useScoped<GameMap>(campaignId, "map", `/maps/${mapId}`, mapId, Boolean(mapId));
}

export function useEntities(campaignId: string, sceneId?: string | null) {
  const query = sceneId ? `?scene_id=${sceneId}` : "";
  return useScoped<EntityView[]>(campaignId, "entities", `/entities${query}`, sceneId ?? "all");
}

export function useAiStatus() {
  return useQuery({
    queryKey: ["ai-status"],
    queryFn: () => api<AiStatus>("/ai/status"),
    refetchInterval: 30_000,
  });
}

/** Mutación genérica que invalida todo lo de la campaña al terminar. */
export function useCampaignMutation<TBody, TResult = unknown>(
  campaignId: string,
  method: string,
  path: string | ((body: TBody) => string),
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: TBody) =>
      api<TResult>(`/campaigns/${campaignId}${typeof path === "function" ? path(body) : path}`, {
        method,
        body: method === "DELETE" ? undefined : body,
        campaignId,
      }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
}
