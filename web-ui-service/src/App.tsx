import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const IncidentDetail = lazy(() => import('./pages/IncidentDetail'));
const OnCall = lazy(() => import('./pages/OnCall'));
const Metrics = lazy(() => import('./pages/Metrics'));

function PageLoader() {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-text-muted text-sm">
      <span className="w-4.5 h-4.5 border-2 border-border border-t-accent rounded-full animate-spin" />
      Loading…
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/incidents/:id" element={<IncidentDetail />} />
            <Route path="/oncall" element={<OnCall />} />
            <Route path="/metrics" element={<Metrics />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
