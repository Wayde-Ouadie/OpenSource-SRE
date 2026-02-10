import React from 'react';

type ProgressVariant =
    | 'critical'
    | 'high'
    | 'medium'
    | 'low'
    | 'triggered'
    | 'acknowledged'
    | 'resolved'
    | 'default';

interface ProgressProps {
    value: number;
    max?: number;
    variant?: ProgressVariant;
    className?: string;
}

const variantClasses: Record<ProgressVariant, string> = {
    critical: 'progress--critical',
    high: 'progress--high',
    medium: 'progress--medium',
    low: 'progress--low',
    triggered: 'progress--triggered',
    acknowledged: 'progress--acknowledged',
    resolved: 'progress--resolved',
    default: '',
};

export default function Progress({ value, max = 100, variant = 'default', className = '' }: ProgressProps) {
    const safeValue = Math.min(Math.max(value, 0), max);

    return (
        <progress
            className={`progress ${variantClasses[variant]} ${className}`}
            value={safeValue}
            max={max}
        />
    );
}
