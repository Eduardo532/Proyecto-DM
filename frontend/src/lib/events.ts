import type { GameEvent } from "../api/types";

/** Texto breve para el registro de acontecimientos (la narración tiene su propio componente). */
export function eventSummary(event: GameEvent): string | null {
  const p = event.payload as Record<string, unknown>;
  const s = (key: string) => String(p[key] ?? "");
  switch (event.type) {
    case "session_started":
      return `Comienza la sesión ${s("number")}.`;
    case "session_closed":
      return `Fin de la sesión ${s("number")}.`;
    case "active_player":
      return p.name ? `Turno de ${s("name")}.` : null;
    case "scene_changed":
      return `Escena: ${s("name")}.`;
    case "roll_requested":
      return `Tirada pendiente: ${s("label")}.`;
    case "roll_resolved":
      return `🎲 ${s("label")}: ${s("breakdown") || s("total")}${p.outcome ? ` — ${outcomeLabel(s("outcome"))}` : ""}`;
    case "free_roll":
      return `🎲 ${s("label")}: ${s("breakdown")}`;
    case "fact_revealed":
      return `Descubierto: ${s("statement")}`;
    case "character_hp": {
      const changes = (p.changes ?? {}) as Record<string, unknown>;
      if (p.kind === "damage") return `${s("name")} recibe ${s("damage")} de daño (PG ${String(changes.hp_current ?? "")}).`;
      if (p.kind === "heal") return `${s("name")} recupera ${s("amount")} PG.`;
      return `${s("name")} obtiene ${s("amount")} PG temporales.`;
    }
    case "character_condition":
      return `${s("name")}: ${p.present ? "gana" : "pierde"} ${s("condition")}.`;
    case "death_save":
      return `${s("name")} — salvación contra muerte: ${s("natural")} (${p.success ? "éxito" : "fallo"}).`;
    case "entity_moved":
      return `${s("name")} se mueve a ${s("to")} (${s("cost_ft")} pies).`;
    case "combat_started":
      return "¡Comienza el combate!";
    case "combat_turn":
      return `Ronda ${s("round")}: turno de ${s("name")}.`;
    case "combat_ended":
      return "Termina el combate.";
    case "enemy_attack":
      return `${s("attacker")} → ${s("target")}: ${s("detail")} (${p.hit ? "impacta" : "falla"})`;
    case "quest_updated":
      return `Misión «${s("title")}»: ${s("status")}.`;
    case "ai_unavailable":
      return `⚠ ${s("message")}`;
    case "entity_revealed":
      return `Aparece: ${s("name")}.`;
    default:
      return null;
  }
}

export function outcomeLabel(outcome: string | null | undefined): string {
  switch (outcome) {
    case "success":
      return "éxito";
    case "failure":
      return "fallo";
    case "critical":
      return "¡crítico!";
    case "fumble":
      return "pifia";
    default:
      return "";
  }
}
