import { NavLink, Route, Routes } from "react-router-dom";

import { DmDocuments } from "./DmDocuments";
import { DmEntities } from "./DmEntities";
import { DmFacts } from "./DmFacts";
import { DmLog } from "./DmLog";
import { DmMaps } from "./DmMaps";
import { DmScenes } from "./DmScenes";
import { DmSettings } from "./DmSettings";

const TABS = [
  ["", "Escenas"],
  ["documentos", "Importar"],
  ["mapas", "Mapas"],
  ["criaturas", "Criaturas y PNJ"],
  ["secretos", "Secretos y memoria"],
  ["registro", "Registro"],
  ["ajustes", "Ajustes"],
] as const;

export function DmView({ campaignId }: { campaignId: string }) {
  const base = `/c/${campaignId}/dm`;
  return (
    <div className="pt-2">
      <nav className="mb-4 flex flex-wrap gap-2 border-b border-blood/40 pb-2">
        {TABS.map(([path, label]) => (
          <NavLink
            key={path}
            end={path === ""}
            to={path ? `${base}/${path}` : base}
            className={({ isActive }) => `rounded px-3 py-1 text-sm ${isActive ? "bg-blood/40 text-parchment" : "text-parchment-dim hover:text-parchment"}`}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route index element={<DmScenes campaignId={campaignId} />} />
        <Route path="documentos" element={<DmDocuments campaignId={campaignId} />} />
        <Route path="mapas" element={<DmMaps campaignId={campaignId} />} />
        <Route path="criaturas" element={<DmEntities campaignId={campaignId} />} />
        <Route path="secretos" element={<DmFacts campaignId={campaignId} />} />
        <Route path="registro" element={<DmLog campaignId={campaignId} />} />
        <Route path="ajustes" element={<DmSettings campaignId={campaignId} />} />
      </Routes>
    </div>
  );
}
