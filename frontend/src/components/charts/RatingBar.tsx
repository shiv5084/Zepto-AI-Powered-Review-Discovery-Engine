import React from 'react';

interface RatingBarProps {
  rating: number;
  max?: number;
}

export default function RatingBar({ rating, max = 5 }: RatingBarProps) {
  // Clamp rating between 0 and max
  const clampedRating = Math.max(0, Math.min(rating, max));
  const percentage = (clampedRating / max) * 100;

  // Determine color based on Spotify-inspired ratings standard
  let barColor = 'var(--rating-high)';
  if (rating < 2.5) {
    barColor = 'var(--rating-low)';
  } else if (rating < 3.8) {
    barColor = 'var(--rating-medium)';
  }

  if (rating <= 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%', maxWidth: '200px' }}>
        <div style={{ 
          flex: 1, 
          height: '6px', 
          backgroundColor: 'rgba(255, 255, 255, 0.05)', 
          borderRadius: '3px',
          overflow: 'hidden'
        }} />
        <span style={{ 
          fontSize: '0.85rem', 
          fontWeight: '500', 
          color: 'var(--text-muted)',
          minWidth: '24px',
          textAlign: 'right'
        }}>
          N/A
        </span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%', maxWidth: '200px' }}>
      <div style={{ 
        flex: 1, 
        height: '6px', 
        backgroundColor: 'rgba(255, 255, 255, 0.1)', 
        borderRadius: '3px',
        overflow: 'hidden'
      }}>
        <div style={{ 
          width: `${percentage}%`, 
          height: '100%', 
          backgroundColor: barColor, 
          borderRadius: '3px',
          transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)'
        }} />
      </div>
      <span style={{ 
        fontSize: '0.85rem', 
        fontWeight: '700', 
        color: 'var(--text-main)',
        minWidth: '24px',
        textAlign: 'right'
      }}>
        {rating.toFixed(1)}
      </span>
    </div>
  );
}
