'use client';

import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { SentimentDistribution } from '../../lib/types';
import styles from '../../styles/dashboard.module.css';

interface SentimentSummaryProps {
  distribution?: SentimentDistribution;
}

const COLORS = {
  positive: '#06D6A0', // Teal/Green
  neutral: '#FFB703',   // Gold
  negative: '#EF476F',  // Soft Red
};

export default function SentimentSummary({ distribution }: SentimentSummaryProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const defaultDist: SentimentDistribution = {
    positive_count: 15,
    neutral_count: 65,
    negative_count: 20,
    positive_pct: 0.15,
    neutral_pct: 0.65,
    negative_pct: 0.20,
    total_reviews: 100,
  };

  const dist = distribution && typeof distribution.total_reviews === 'number' && distribution.total_reviews > 0
    ? distribution
    : defaultDist;

  const total = dist.total_reviews || 100;
  const pPct = (dist.positive_pct || 0) * 100;
  const nPct = (dist.neutral_pct || 0) * 100;
  const negPct = (dist.negative_pct || 0) * 100;

  const chartData = [
    { name: 'Positive', value: dist.positive_count, color: COLORS.positive },
    { name: 'Neutral', value: dist.neutral_count, color: COLORS.neutral },
    { name: 'Negative', value: dist.negative_count, color: COLORS.negative },
  ].filter(d => d.value > 0);

  return (
    <section className={styles.sentimentSection} style={{ background: '#1A1F2E', borderRadius: '12px', border: '1px solid var(--border-color)', padding: '1.75rem' }}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>
            <span className={styles.sectionTitleIcon}>📊</span>
            Overall User Sentiment Breakdown
          </h2>
          <p className={styles.sectionSubtitle}>
            Aggregated tone across all classified reviews in this reporting period.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '2rem', justifyContent: 'space-around', marginTop: '1rem' }}>
        
        {/* Recharts Donut Chart */}
        <div style={{ width: '250px', height: '200px', position: 'relative' }}>
          {mounted ? (
            <PieChart width={250} height={200}>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}
                itemStyle={{ color: '#fff' }}
              />
            </PieChart>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
              Loading Chart...
            </div>
          )}
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
            <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fff' }}>{total}</span>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Reviews</div>
          </div>
        </div>

        {/* Legend Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1, minWidth: '240px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: COLORS.positive }} />
              <span style={{ color: '#fff', fontSize: '0.9rem' }}>Positive</span>
            </div>
            <span style={{ fontWeight: 600, color: COLORS.positive }}>{dist.positive_count} ({pPct.toFixed(1)}%)</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: COLORS.neutral }} />
              <span style={{ color: '#fff', fontSize: '0.9rem' }}>Neutral</span>
            </div>
            <span style={{ fontWeight: 600, color: COLORS.neutral }}>{dist.neutral_count} ({nPct.toFixed(1)}%)</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: COLORS.negative }} />
              <span style={{ color: '#fff', fontSize: '0.9rem' }}>Negative</span>
            </div>
            <span style={{ fontWeight: 600, color: COLORS.negative }}>{dist.negative_count} ({negPct.toFixed(1)}%)</span>
          </div>
        </div>

      </div>
    </section>
  );
}
