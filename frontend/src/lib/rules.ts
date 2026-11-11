import type { AbilityKey } from "../api/types";

export const ABILITIES: { key: AbilityKey; name: string; short: string }[] = [
  { key: "str", name: "Fuerza", short: "FUE" },
  { key: "dex", name: "Destreza", short: "DES" },
  { key: "con", name: "Constitución", short: "CON" },
  { key: "int", name: "Inteligencia", short: "INT" },
  { key: "wis", name: "Sabiduría", short: "SAB" },
  { key: "cha", name: "Carisma", short: "CAR" },
];

export const SKILLS: Record<string, { label: string; ability: AbilityKey }> = {
  acrobatics: { label: "Acrobacias", ability: "dex" },
  animal_handling: { label: "Trato con Animales", ability: "wis" },
  arcana: { label: "Conocimiento Arcano", ability: "int" },
  athletics: { label: "Atletismo", ability: "str" },
  deception: { label: "Engaño", ability: "cha" },
  history: { label: "Historia", ability: "int" },
  insight: { label: "Perspicacia", ability: "wis" },
  intimidation: { label: "Intimidación", ability: "cha" },
  investigation: { label: "Investigación", ability: "int" },
  medicine: { label: "Medicina", ability: "wis" },
  nature: { label: "Naturaleza", ability: "int" },
  perception: { label: "Percepción", ability: "wis" },
  performance: { label: "Interpretación", ability: "cha" },
  persuasion: { label: "Persuasión", ability: "cha" },
  religion: { label: "Religión", ability: "int" },
  sleight_of_hand: { label: "Juego de Manos", ability: "dex" },
  stealth: { label: "Sigilo", ability: "dex" },
  survival: { label: "Supervivencia", ability: "wis" },
};

export const CONDITIONS: Record<string, string> = {
  blinded: "Cegado",
  charmed: "Hechizado",
  deafened: "Ensordecido",
  frightened: "Asustado",
  grappled: "Agarrado",
  incapacitated: "Incapacitado",
  invisible: "Invisible",
  paralyzed: "Paralizado",
  petrified: "Petrificado",
  poisoned: "Envenenado",
  prone: "Derribado",
  restrained: "Apresado",
  stunned: "Aturdido",
  unconscious: "Inconsciente",
};

export const DAMAGE_TYPES: Record<string, string> = {
  slashing: "cortante",
  piercing: "perforante",
  bludgeoning: "contundente",
  fire: "fuego",
  cold: "frío",
  lightning: "relámpago",
  thunder: "trueno",
  acid: "ácido",
  poison: "veneno",
  necrotic: "necrótico",
  radiant: "radiante",
  force: "fuerza",
  psychic: "psíquico",
};

export const KNOWLEDGE_LABELS: Record<string, string> = {
  public: "Público",
  conditional: "Condicionado",
  dm: "Solo DM",
};

export function signed(value: number): string {
  return value >= 0 ? `+${value}` : `${value}`;
}

export function modifier(score: number): number {
  return Math.floor((score - 10) / 2);
}

export function columnLabel(x: number): string {
  let label = "";
  let n = x + 1;
  while (n > 0) {
    const rem = (n - 1) % 26;
    label = String.fromCharCode(65 + rem) + label;
    n = Math.floor((n - 1) / 26);
  }
  return label;
}

export function cellLabel(x: number, y: number): string {
  return `${columnLabel(x)}${y + 1}`;
}
