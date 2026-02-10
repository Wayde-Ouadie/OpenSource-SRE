import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Navbar from './components/layout/Navbar/Navbar';
import Container from './components/layout/Container/Container';
import Dashboard from './pages/Dashboard/Dashboard';
import IncidentList from './pages/IncidentList/IncidentList';
import IncidentDetail from './pages/IncidentDetail/IncidentDetail';
import OnCall from './pages/OnCall/OnCall';
import Metrics from './pages/Metrics/Metrics';
import { fetchServiceHealth } from './services/api';

export default function App() {
  const [serviceHealth, setServiceHealth] = useState<'healthy' | 'degraded' | 'down'>('healthy');

  useEffect(() => {
    fetchServiceHealth()
      .then(setServiceHealth)
      .catch(() => setServiceHealth('down'));

    const interval = setInterval(() => {
      fetchServiceHealth()
        .then(setServiceHealth)
        .catch(() => setServiceHealth('down'));
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <Navbar serviceHealth={serviceHealth} />
        <Container>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/incidents" element={<IncidentList />} />
            <Route path="/incidents/:id" element={<IncidentDetail />} />
            <Route path="/on-call" element={<OnCall />} />
            <Route path="/metrics" element={<Metrics />} />
          </Routes>
        </Container>
      </div>
    </BrowserRouter>
  );
}
