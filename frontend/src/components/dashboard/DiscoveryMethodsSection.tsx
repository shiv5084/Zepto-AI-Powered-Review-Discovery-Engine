'use client';

import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { MetricItem } from '../../lib/types';
import MetricCard from './MetricCard';
import styles from '../../styles/dashboard.module.css';

interface DiscoveryMethodsSectionProps {
  methods: MetricItem[];
}

export default function DiscoveryMethodsSection({ methods }: DiscoveryMethodsSectionProps) {
  const [mounted, setMounted] = useState(false);
  const [activeEvidence, setActiveEvidence] = useState<number | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const hasData = methods && methods.length > 0;

  const chartData = methods.map(item => ({
    name: item.theme,
    count: item.count,
    rating: item.average_rating
  }));

  return (
    <section id="discovery-methods" className={styles.gridSection}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>
            <span className={styles.sectionTitleIcon}>💡</span>
            3. Top Current Discovery Methods
          </h2>
          <p className={styles.sectionSubtitle}>
            How users currently discover products and categories on the platform.
          </p>
        </div>
      </div>

      {hasData ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          
          {/* Recharts Bar Chart */}
          <div style={{ width: '100%', height: '180px', background: 'rgba(255,255,255,0.01)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.03)' }}>
            {mounted ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                >
                  <XAxis type="number" stroke="#9CA3AF" fontSize={11} />
                  <YAxis dataKey="name" type="category" stroke="#9CA3AF" fontSize={11} width={120} />
                  <Tooltip 
                    contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Bar dataKey="count" fill="#10B981" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? '#10B981' : '#047857'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                Loading Chart...
              </div>
            )}
          </div>

          {/* Metric Cards */}
          <div className={styles.cardGrid}>
            {methods.slice(0, 3).map((item, index) => (
              <MetricCard
                key={index}
                title={item.theme}
                count={item.count}
                averageRating={item.average_rating}
              >
                {item.evidence && item.evidence.length > 0 && (
                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '0.5rem' }}>
                    <button 
                      onClick={() => setActiveEvidence(activeEvidence === index ? null : index)}
                      style={{ background: 'none', border: 'none', color: '#a7f3d0', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', padding: 0 }}
                    >
                      <span>{activeEvidence === index ? 'Hide' : 'Show'} Evidence Quote</span>
                      <span>{activeEvidence === index ? '▲' : '▼'}</span>
                    </button>
                    {activeEvidence === index && (
                      <p style={{ fontStyle: 'italic', fontSize: '0.75rem', color: '#D1D5DB', marginTop: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '4px', borderLeft: '2px solid #10B981' }}>
                        "{item.evidence[0]}"
                      </p>
                    )}
                  </div>
                )}
              </MetricCard>
            ))}
          </div>

        </div>
      ) : (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>🔍</div>
          <p>No discovery methods identified in this batch.</p>
        </div>
      )}
    </section>
  );
}
