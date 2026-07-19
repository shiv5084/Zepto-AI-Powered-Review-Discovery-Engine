import React from 'react';

interface FrequencyBadgeProps {
  frequency: number;
}

export default function FrequencyBadge({ frequency }: FrequencyBadgeProps) {
  // Convert frequency to percentage (e.g. 0.1 -> 10)
  const rawPct = frequency * 100;
  const percentage = (rawPct > 0 && rawPct < 1) ? rawPct.toFixed(1) : rawPct.toFixed(0);
  
  return (
    <span style={{
      backgroundColor: 'rgba(29, 185, 84, 0.12)',
      color: 'var(--primary)',
      padding: '0.25rem 0.6rem',
      borderRadius: '12px',
      fontSize: '0.75rem',
      fontWeight: '700',
      border: '1px solid rgba(29, 185, 84, 0.25)',
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.25rem',
      whiteSpace: 'nowrap'
    }}>
      <span style={{
        width: '6px',
        height: '6px',
        borderRadius: '50%',
        backgroundColor: 'var(--primary)',
        display: 'inline-block'
      }} />
      {percentage}% Freq
    </span>
  );
}
