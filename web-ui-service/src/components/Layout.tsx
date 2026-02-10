import { NavLink, Outlet } from 'react-router-dom';
import ApiErrorBanner from './ApiErrorBanner';

export default function Layout() {
  const linkBase =
    'flex items-center gap-2.5 px-3 py-2 text-text-muted text-[0.84rem] font-medium rounded-lg hover:text-text hover:bg-white/[0.04] transition-all duration-200 relative';
  const linkActive =
    'text-accent! bg-accent-subtle! font-semibold! before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:w-[3px] before:h-4 before:rounded-full before:bg-accent';

  return (
    <div className="flex min-h-screen bg-bg">
      {/* Sidebar */}
      <nav className="w-[230px] bg-bg-subtle border-r border-border/60 shrink-0 sticky top-0 h-screen flex flex-col overflow-y-auto">
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 pt-6 pb-5">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-accent/80 to-accent shadow-[0_0_12px_rgba(110,142,251,0.2)] text-sm">
            🔥
          </div>
          <div className="flex flex-col">
            <span className="text-[0.92rem] font-bold tracking-tight text-text leading-tight">IncidentOps</span>
            <span className="text-[0.6rem] text-text-muted font-medium tracking-wide uppercase">Platform</span>
          </div>
        </div>

        <div className="mx-4 h-px bg-border/50 mb-2" />

        {/* Navigation */}
        <div className="flex-1 px-3 pt-1">
          <div className="text-[0.6rem] font-semibold uppercase tracking-[0.12em] text-text-muted/60 px-3 pt-4 pb-2">
            Overview
          </div>
          <ul className="list-none p-0 m-0 flex flex-col gap-0.5">
            <li>
              <NavLink
                to="/"
                end
                className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ''}`}
              >
                <span className="w-5 text-center text-[0.95rem]">📊</span>
                Dashboard
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/oncall"
                className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ''}`}
              >
                <span className="w-5 text-center text-[0.95rem]">👤</span>
                On-Call
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/metrics"
                className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ''}`}
              >
                <span className="w-5 text-center text-[0.95rem]">📈</span>
                Metrics
              </NavLink>
            </li>
          </ul>
        </div>

        {/* Footer */}
        <div className="px-5 py-3.5 border-t border-border/50 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-status-resolved shadow-[0_0_6px_rgba(34,197,94,0.5)]" />
          <span className="text-[0.68rem] text-text-muted font-medium">Local Edition</span>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto min-h-screen">
        <ApiErrorBanner />
        <div className="p-6 lg:p-8 xl:p-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
