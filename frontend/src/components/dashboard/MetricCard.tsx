import React from 'react';
import RatingBar from '../charts/RatingBar';
import styles from '../../styles/dashboard.module.css';

interface MetricCardProps {
  title: string;
  count: number;
  averageRating: number;
  children?: React.ReactNode;
}

export default function MetricCard({
  title,
  count,
  averageRating,
  children
}: MetricCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <h3 className={styles.cardTitle}>{title}</h3>
        <div className={styles.badgeGroup}>
          <span className={styles.countBadge}>{count} reviews</span>
        </div>
      </div>

      {children && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem', marginBottom: '0.5rem' }}>
          {children}
        </div>
      )}

      <div className={styles.cardFooter}>
        <div className={styles.metricRow}>
          <span>Average User Rating:</span>
          <RatingBar rating={averageRating} />
        </div>
      </div>
    </div>
  );
}
