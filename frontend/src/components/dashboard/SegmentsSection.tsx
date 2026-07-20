'use client';

import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { UnderservedSegment } from '../../lib/types';
import styles from '../../styles/dashboard.module.css';
import RatingBar from '../charts/RatingBar';

interface SegmentsSectionProps {
  segments: UnderservedSegment[];
}

export default function SegmentsSection({ segments }: SegmentsSectionProps) {
  const [mounted, setMounted] = useState(false);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const hasData = segments && segments.length > 0;

  // Pre-formatted data for Recharts Radar (using full segment name as subject)
  const radarData = segments.map(item => ({
    subject: item.segment,
    severity: item.severity_score,
    rating: item.average_rating,
    fullMark: 5.0
  }));

  return (
    <section id="segments" className={styles.gridSection}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>
            <span className={styles.sectionTitleIcon}>👥</span>
            7. Underserved User Segments
          </h2>
          <p className={styles.sectionSubtitle}>
            Prioritized shopper personas mapped against discovery severity score metrics.
          </p>
        </div>
      </div>

      {hasData ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem', alignItems: 'center' }}>
          
          {/* Radar Chart */}
          <div style={{ width: '420px', height: '280px', background: 'rgba(255,255,255,0.01)', padding: '0.5rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.03)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {mounted ? (
              <RadarChart 
                cx="50%" 
                cy="50%" 
                outerRadius="60%" 
                data={radarData} 
                width={420} 
                height={280}
                margin={{ top: 15, right: 90, bottom: 15, left: 90 }}
              >
                <PolarGrid stroke="rgba(255,255,255,0.08)" />
                <PolarAngleAxis dataKey="subject" stroke="#9CA3AF" fontSize={10} />
                <PolarRadiusAxis angle={30} domain={[0, 5]} stroke="rgba(255,255,255,0.3)" fontSize={10} />
                <Radar name="Severity" dataKey="severity" stroke="#7C3AED" fill="#7C3AED" fillOpacity={0.4} />
              </RadarChart>
            ) : (
              <div style={{ color: 'var(--text-muted)' }}>Loading Segment Radar...</div>
            )}
          </div>

          {/* Segment Details cards */}
          <div style={{ flex: 1, minWidth: '320px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {segments.map((item, index) => (
              <div 
                key={index} 
                className={styles.card}
                style={{ 
                  borderColor: item.severity_rank === 1 ? 'rgba(124, 58, 237, 0.4)' : 'rgba(255,255,255,0.05)',
                  background: item.severity_rank === 1 ? 'rgba(124, 58, 237, 0.02)' : 'rgba(255,255,255,0.03)'
                }}
              >
                <div className={styles.cardHeader}>
                  <div>
                    <span style={{ fontSize: '0.7rem', color: '#7C3AED', fontWeight: 700, textTransform: 'uppercase' }}>Rank #{item.severity_rank}</span>
                    <h3 className={styles.cardTitle} style={{ fontSize: '1.1rem', marginTop: '0.1rem' }}>{item.segment}</h3>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#EF476F' }}>{item.severity_score.toFixed(2)}</div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Severity Score</div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', margin: '0.25rem 0' }}>
                  <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Sample Size</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#FFF' }}>{item.count} reviews</div>
                  </div>
                  <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>% Sample</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#7C3AED' }}>{((item.pct_sample || 0) * 100).toFixed(1)}%</div>
                  </div>
                  <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px', textAlign: 'center' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>% Negative</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#EF476F' }}>{((item.pct_negative_reviews || 0) * 100).toFixed(1)}%</div>
                  </div>
                </div>

                {item.discovery_challenges && item.discovery_challenges.length > 0 && (
                  <div style={{ background: 'rgba(255,255,255,0.01)', padding: '0.75rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.03)' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>Top Discovery Friction:</div>
                    <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: '#D1D5DB', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {item.discovery_challenges.slice(0, 2).map((ch, idx) => (
                        <li key={idx}>
                          <span style={{ fontWeight: 600, color: '#FFF' }}>{ch.pain_point}</span> 
                          <span style={{ color: 'var(--text-muted)' }}> (reported by {(ch.frequency_within_segment * 100).toFixed(0)}% of this segment)</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className={styles.cardFooter} style={{ padding: 0, border: 'none', marginTop: '0.5rem' }}>
                  <div className={styles.metricRow}>
                    <span>Average Rating:</span>
                    <RatingBar rating={item.average_rating} />
                  </div>
                </div>
              </div>
            ))}
          </div>

        </div>
      ) : (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>🔍</div>
          <p>No segment data identified in this batch.</p>
        </div>
      )}
    </section>
  );
}
