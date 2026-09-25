import { lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { FarmerLayout } from "./layouts/FarmerLayout";
import { OfficerLayout } from "./layouts/OfficerLayout";

// Routes are code-split so the farmer app loads without the officer console (Guide 11.2).
const MapPage = lazy(() => import("./pages/MapPage"));
const PriorityPage = lazy(() => import("./pages/PriorityPage"));
const ReviewPage = lazy(() => import("./pages/ReviewPage"));
const VerificationPage = lazy(() => import("./pages/VerificationPage"));
const ImpactPage = lazy(() => import("./pages/ImpactPage"));
const BulletinPage = lazy(() => import("./pages/BulletinPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const FarmerToday = lazy(() => import("./pages/farmer/FarmerToday"));
const FarmerForecast = lazy(() => import("./pages/farmer/FarmerForecast"));
const FarmerFarm = lazy(() => import("./pages/farmer/FarmerFarm"));

/** "/" goes to the map and keeps the query, so shared links still work. */
function RedirectToMap() {
  const { search } = useLocation();
  return <Navigate to={{ pathname: "/map", search }} replace />;
}

/** Route table from Frontend Guide section 5. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<RedirectToMap />} />
        <Route element={<OfficerLayout />}>
          <Route path="map" element={<MapPage />} />
          <Route path="priority" element={<PriorityPage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="verification" element={<VerificationPage />} />
          <Route path="impact" element={<ImpactPage />} />
          <Route path="bulletin/:pid" element={<BulletinPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="farmer" element={<FarmerLayout />}>
          <Route index element={<FarmerToday />} />
          <Route path="forecast" element={<FarmerForecast />} />
          <Route path="farm" element={<FarmerFarm />} />
        </Route>
      </Route>
    </Routes>
  );
}
