import React from 'react';

type BadgeVariant = 'critical' | 'high' | 'medium' | 'low' | 'triggered' | 'acknowledged' | 'resolved';

interface BadgeProps {
    variant: BadgeVariant;
    children: React.ReactNode;
}

const variantClasses: Record<BadgeVariant, string> = {
    critical: 'bg-critical/15 text-critical border-critical/40',
    high: 'bg-high/15 text-high border-high/40',
    medium: 'bg-medium/15 text-medium border-medium/40',
    low: 'bg-low/15 text-low border-low/40',
    triggered: 'bg-danger/15 text-danger border-danger/40',
    acknowledged: 'bg-warning/15 text-warning border-warning/40',
    resolved: 'bg-success/15 text-success border-success/40',
};

export default function Badge({ variant, children }: BadgeProps) {
    return (
        <span
            className={`
        inline-flex items-center
                px-2.5 py-0.5
                text-xs font-semibold uppercase tracking-wide
        rounded-full border
        ${variantClasses[variant]}
      `}
        >
            {children}
        </span>
    );
}
