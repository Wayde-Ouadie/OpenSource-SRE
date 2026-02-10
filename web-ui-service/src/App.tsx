import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import IncidentDetail from './pages/IncidentDetail';
import OnCall from './pages/OnCall';
import Metrics from './pages/Metrics';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incidents/:id" element={<IncidentDetail />} />
          <Route path="/oncall" element={<OnCall />} />
          <Route path="/metrics" element={<Metrics />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
