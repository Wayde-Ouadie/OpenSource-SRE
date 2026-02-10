import React from 'react';

interface CardProps {
    children: React.ReactNode;
    className?: string;
}

export default function Card({ children, className = '' }: CardProps) {
    return (
        <div
            className={`
                bg-surface rounded-xl border border-border/70
                p-spacing-lg shadow-sm
        ${className}
      `}
        >
            {children}
        </div>
    );
}
