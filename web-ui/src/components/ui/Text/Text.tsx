import React from 'react';

type TextVariant = 'h1' | 'h2' | 'h3' | 'body' | 'label' | 'caption';

interface TextProps {
    variant?: TextVariant;
    children: React.ReactNode;
    className?: string;
}

const variantConfig: Record<TextVariant, { tag: keyof React.JSX.IntrinsicElements; classes: string }> = {
    h1: { tag: 'h1', classes: 'text-3xl font-semibold text-text-primary tracking-tight' },
    h2: { tag: 'h2', classes: 'text-2xl font-semibold text-text-primary tracking-tight' },
    h3: { tag: 'h3', classes: 'text-xl font-semibold text-text-primary' },
    body: { tag: 'p', classes: 'text-base text-text-secondary' },
    label: { tag: 'span', classes: 'text-xs font-semibold text-text-muted uppercase tracking-widest' },
    caption: { tag: 'span', classes: 'text-xs text-text-muted' },
};

export default function Text({ variant = 'body', children, className = '' }: TextProps) {
    const config = variantConfig[variant];
    const Tag = config.tag as React.ElementType;

    return <Tag className={`${config.classes} ${className}`}>{children}</Tag>;
}
