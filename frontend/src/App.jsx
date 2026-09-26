import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import PredictPage from "./pages/PredictPage.jsx";
import RepurposePage from "./pages/RepurposePage.jsx";

const linkClass = ({ isActive }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-indigo-100 text-indigo-800" : "text-slate-600 hover:text-slate-900"}`;

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <nav className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
            <span className="mr-4 text-lg font-bold text-indigo-700">Drug Discovery</span>
            <NavLink to="/predict" className={linkClass}>Predict molecule</NavLink>
            <NavLink to="/repurpose" className={linkClass}>Repurpose drugs</NavLink>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">
          <Routes>
            <Route path="/" element={<Navigate to="/predict" replace />} />
            <Route path="/predict" element={<PredictPage />} />
            <Route path="/repurpose" element={<RepurposePage />} />
            <Route path="*" element={<Navigate to="/predict" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
