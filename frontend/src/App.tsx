import { Route, Routes } from "react-router-dom";

import { CampaignLayout } from "./pages/CampaignLayout";
import { Library } from "./pages/Library";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Library />} />
      <Route path="/c/:campaignId/*" element={<CampaignLayout />} />
      <Route path="*" element={<Library />} />
    </Routes>
  );
}
