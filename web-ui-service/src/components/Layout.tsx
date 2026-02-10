import { NavLink, Outlet } from 'react-router-dom';

export default function Layout() {
  const linkBase =
    'flex items-center gap-2.5 px-3 py-2 text-text-secondary text-sm font-medium rounded-md hover:text-text hover:bg-surface-hover transition-all duration-150';
  const linkActive = 'text-accent! bg-accent-subtle! font-semibold!';

  return (
    <div className="flex min-h-screen bg-bg">
      {/* Sidebar */}
      <nav className="w-[230px] bg-surface border-r border-border shrink-0 sticky top-0 h-screen flex flex-col overflow-y-auto">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 pt-5 pb-4">
          <div className="flex items-center justify-center w-8 h-8 rounded-md bg-gradient-to-br from-status-open to-sev-high text-sm">
            🔥
          </div>
          <span className="text-base font-bold tracking-tight text-text">IncidentOps</span>
        </div>

        {/* Navigation */}
        <div className="flex-1 px-3 pt-1">
          <div className="text-[0.65rem] font-semibold uppercase tracking-widest text-text-muted px-3 pt-4 pb-2">
            Overview
          </div>
          <ul className="list-none p-0 m-0 flex flex-col gap-0.5">
            <li>
              <NavLink
                to="/"
                end
                className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ''}`}
              >
                <span className="w-5 text-center text-base opacity-75">📊</span>
                Dashboard
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/oncall"
                className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ''}`}
              >
                <span className="w-5 text-center text-base opacity-75">👤</span>
                On-Call
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/metrics"
                className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ''}`}
              >
                <span className="w-5 text-center text-base opacity-75">📈</span>
                Metrics
              </NavLink>
            </li>
          </ul>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-border text-[0.7rem] text-text-muted">
          IncidentOps · Local Edition
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 p-6 lg:p-8 xl:p-10 overflow-y-auto min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
