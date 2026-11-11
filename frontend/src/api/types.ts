export type KnowledgeLevel = "public" | "conditional" | "dm";

export interface Campaign {
  id: string;
  name: string;
  description: string;
  game_system: string;
  dice_mode: "digital" | "manual" | "ask";
  settings: Record<string, unknown>;
  status: string;
  has_dm_pin: boolean;
  created_at: string;
  updated_at: string;
}

export interface Player {
  id: string;
  campaign_id: string;
  display_name: string;
  color: string;
  turn_order: number;
}

export type AbilityKey = "str" | "dex" | "con" | "int" | "wis" | "cha";

export interface Attack {
  name: string;
  ability: AbilityKey;
  proficient: boolean;
  attack_bonus_extra: number;
  damage: string;
  damage_type: string;
  reach_ft: number;
  range_ft: number | null;
  range_long_ft: number | null;
}

export interface InventoryItem {
  name: string;
  quantity: number;
  equipped: boolean;
  weight_lb: number;
  notes: string;
}

export interface SheetData {
  abilities: Record<AbilityKey, number>;
  skill_proficiencies: string[];
  skill_expertise: string[];
  save_proficiencies: AbilityKey[];
  jack_of_all_trades: boolean;
  initiative_bonus_extra: number;
  darkvision_ft: number;
  resistances: string[];
  immunities: string[];
  vulnerabilities: string[];
  attacks: Attack[];
  spellcasting_ability: AbilityKey | null;
  spells: { name: string; level: number; prepared: boolean; description: string }[];
  spell_slots: Record<string, { max: number; used: number }>;
  features: { name: string; description: string; uses_max: number | null; uses_used: number }[];
  feats: string[];
  inventory: InventoryItem[];
  coins: { cp: number; sp: number; ep: number; gp: number; pp: number };
  languages: string[];
  other_proficiencies: string[];
  hit_die: string;
  hit_dice_used: number;
  personality: string;
}

export interface Derived {
  proficiency_bonus: number;
  ability_modifiers: Record<AbilityKey, number>;
  skills: Record<string, number>;
  saves: Record<AbilityKey, number>;
  initiative: number;
  passive_perception: number;
  passive_investigation: number;
  passive_insight: number;
  spell_save_dc: number | null;
  spell_attack_bonus: number | null;
  attacks: { name: string; bonus: number; damage: string; damage_type: string }[];
}

export interface Character {
  id: string;
  campaign_id: string;
  player_id: string | null;
  name: string;
  race: string;
  char_class: string;
  subclass: string;
  level: number;
  background: string;
  alignment: string;
  xp: number;
  sheet: SheetData;
  hp_max: number;
  hp_current: number;
  hp_temp: number;
  armor_class: number;
  speed_ft: number;
  conditions: string[];
  exhaustion: number;
  death_saves: { successes?: number; failures?: number };
  stable: boolean;
  status: string;
  notes: string;
  version: number;
  derived: Derived | null;
}

export interface GameSession {
  id: string;
  campaign_id: string;
  number: number;
  state: "exploring" | "awaiting_roll" | "combat" | "paused" | "closed";
  scene_id: string | null;
  active_player_id: string | null;
  ai_paused: boolean;
  summary: Record<string, unknown>;
  started_at: string;
  ended_at: string | null;
}

export interface GameEvent {
  id: string;
  seq: number;
  type: string;
  actor_kind: string;
  actor_id: string | null;
  payload: Record<string, unknown>;
  visibility: string;
  session_id: string | null;
  created_at: string;
}

export interface Roll {
  id: string;
  character_id: string | null;
  purpose: string;
  label: string;
  expression: string;
  ability: string | null;
  skill: string | null;
  advantage: "none" | "advantage" | "disadvantage";
  status: "pending" | "resolved" | "void";
  mode: string | null;
  dice: number[];
  natural: number | null;
  modifiers: { label: string; value: number }[];
  modifier_total: number;
  total: number | null;
  dc: number | null;
  outcome: string | null;
  reason: string;
  breakdown?: string;
}

export interface Scene {
  id: string;
  name: string;
  summary?: string;
  summary_public?: string;
  summary_dm?: string;
  map_id: string | null;
  status: string;
  order_index?: number;
  lighting: string;
}

export interface MapLogic {
  terrain: [number, number, string][];
  doors: { x: number; y: number; state: string; secret?: boolean; discovered?: boolean; fact_id?: string }[];
  lights: { x: number; y: number; bright_ft: number; dim_ft: number }[];
  diagonal_rule?: string;
}

export interface GameMap {
  id: string;
  name: string;
  origin: string;
  width_cells: number;
  height_cells: number;
  cell_size_ft: number;
  grid_offset_x: number;
  grid_offset_y: number;
  cell_size_px: number;
  ambient_light: string;
  has_background: boolean;
  fog_enabled: boolean;
  logic: MapLogic;
  explored: [number, number][];
  visible?: [number, number][];
}

export interface EntityView {
  id: string;
  kind: "character" | "npc" | "creature" | "object";
  character_id: string | null;
  npc_id?: string | null;
  name: string;
  name_public?: string;
  x: number | null;
  y: number | null;
  size: string;
  conditions: string[];
  disposition: "ally" | "neutral" | "hostile";
  token_color: string;
  map_id: string | null;
  scene_id: string | null;
  hp_current?: number | null;
  hp_max?: number | null;
  health?: string | null;
  hidden?: boolean;
  armor_class?: number | null;
  stats?: Record<string, unknown>;
}

export interface Fact {
  id: string;
  subject: string;
  statement: string;
  scene_id: string | null;
  knowledge_level: KnowledgeLevel;
  discovery: Record<string, unknown>;
  keywords: string[];
  source: string;
  status: string;
}

export interface CombatView {
  id: string;
  status: string;
  round: number;
  current_entity_id: string;
  order: {
    entity_id: string;
    name: string;
    initiative: number;
    kind: string;
    disposition: string;
    removed: boolean;
    budget: { action: boolean; bonus: boolean; reaction: boolean; movement_ft: number } | null;
  }[];
  log: string[];
}

export interface DocumentInfo {
  id: string;
  title: string;
  filename: string;
  page_count: number;
  status: "pending" | "processing" | "ready" | "error";
  progress: number;
  log: string[];
  created_at: string;
}

export interface Chunk {
  id: string;
  document_id: string;
  ordinal: number;
  page_start: number;
  page_end: number;
  section: string;
  kind: string;
  text: string;
  knowledge_level: KnowledgeLevel;
  classification_source: string;
  classification_reason: string;
  scene_id: string | null;
}

export interface Asset {
  id: string;
  document_id: string;
  page: number;
  width: number;
  height: number;
  kind: string;
  knowledge_level: KnowledgeLevel;
  caption: string;
}

export interface Npc {
  id: string;
  name: string;
  public_description?: string;
  description?: string;
  personality?: string;
  motivations?: string;
  secrets?: string;
  voice?: string;
  attitude?: string;
  status: string;
  known_to_party?: boolean;
}

export interface Quest {
  id: string;
  title: string;
  description?: string;
  description_public?: string;
  description_dm?: string;
  status: string;
}

export interface MemoryEntry {
  id: string;
  scope: string;
  scope_id: string | null;
  content: string;
  importance: number;
  visibility: "public" | "dm";
  edited_by_dm: boolean;
  superseded_by: string | null;
}

export interface AiStatus {
  provider: string;
  reachable: boolean;
  models: string[];
  missing?: string[];
  ready: boolean;
  model?: string;
}
