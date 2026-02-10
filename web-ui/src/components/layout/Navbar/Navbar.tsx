import { NavLink } from 'react-router-dom';
import Icon from '../../ui/Icon/Icon';

interface NavItem {
    to: string;
    label: string;
    icon: string;
}

const navItems: NavItem[] = [
    { to: '/', label: 'Dashboard', icon: 'home' },
    { to: '/incidents', label: 'Incidents', icon: 'alert' },
    { to: '/on-call', label: 'On-Call', icon: 'user' },
    { to: '/metrics', label: 'Metrics', icon: 'chart' },
];

interface NavbarProps {
    serviceHealth: 'healthy' | 'degraded' | 'down';
}

const healthColors: Record<string, string> = {
    healthy: 'bg-success',
    degraded: 'bg-warning',
    down: 'bg-danger',
};

export default function Navbar({ serviceHealth }: NavbarProps) {
    return (
        <nav className="sticky top-0 z-40 border-b border-border/70 bg-surface/90 backdrop-blur px-spacing-xl py-spacing-md">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
                <div className="flex items-center gap-spacing-xl">
                    <div className="flex items-center gap-spacing-sm">
                        <Icon name="shield" size="lg" className="text-primary" />
                        <span className="text-lg font-semibold text-text-primary tracking-tight">
                            IncidentOps
                        </span>
                    </div>

                    <div className="flex items-center gap-spacing-xs">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.to}
                                to={item.to}
                                className={({ isActive }) =>
                                    `flex items-center gap-spacing-sm px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150 ${isActive
                                        ? 'bg-primary/15 text-primary'
                                        : 'text-text-secondary hover:text-text-primary hover:bg-surface-raised'
                                    }`
                                }
                            >
                                <Icon name={item.icon} size="sm" />
                                {item.label}
                            </NavLink>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-spacing-sm">
                    <div className="flex items-center gap-spacing-xs text-xs font-semibold uppercase tracking-wide text-text-secondary">
                        <span className={`w-2 h-2 rounded-full ${healthColors[serviceHealth]}`} />
                        <span className="capitalize">{serviceHealth}</span>
                    </div>
                </div>
            </div>
        </nav>
    );
}
