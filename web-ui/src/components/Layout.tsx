import { NavLink, Outlet } from 'react-router-dom';
import './Layout.css';

export default function Layout() {
  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="logo">
          <span className="logo-icon">🔥</span>
          IncidentOps
        </div>
        <div className="sidebar-nav">
          <div className="sidebar-section-label">Overview</div>
          <ul>
            <li>
              <NavLink to="/" end>
                <span className="nav-icon">📊</span>
                Dashboard
              </NavLink>
            </li>
            <li>
              <NavLink to="/oncall">
                <span className="nav-icon">👤</span>
                On-Call
              </NavLink>
            </li>
            <li>
              <NavLink to="/metrics">
                <span className="nav-icon">📈</span>
                Metrics
              </NavLink>
            </li>
          </ul>
        </div>
        <div className="sidebar-footer">
          IncidentOps · Local Edition
        </div>
      </nav>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
