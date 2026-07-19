'use client';

import React, { useEffect, useState } from 'react';
import styles from '../../styles/dashboard.module.css';

export default function OpportunitiesPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch('/api/dashboard', { cache: 'no-store' });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `HTTP error! Status: ${res.status}`);
        }
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        console.error('Error fetching opportunities data:', err);
        setErrorMsg(err.message || 'Unknown error occurred.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>🔄</div>
          <p>Loading product opportunities...</p>
        </div>
      </div>
    );
  }

  if (errorMsg || !data) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>⚠️</div>
          <p>Error loading product opportunities: {errorMsg || 'Data file not found.'}</p>
        </div>
      </div>
    );
  }

  const opportunities = data.metrics?.opportunities || [];
  const hasData = opportunities.length > 0;

  return (
    <div className={styles.dashboardContainer}>
      <div className={styles.headerSection}>
        <h1 className={styles.pageTitle}>Product Opportunities &amp; AI Solutions</h1>
        <p className={styles.pageSubtitle}>
          Deep dive into the tactical and strategic product recommendations discovered by the PRDE pipeline.
        </p>
      </div>

      {hasData ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          {opportunities.map((item: any, index: number) => (
            <div
              key={index}
              className={styles.oppCard}
              style={{
                borderLeft: '4px solid var(--primary)',
                background: 'rgba(255, 255, 255, 0.02)',
                padding: '2rem'
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                paddingBottom: '1rem',
                marginBottom: '1.5rem'
              }}>
                <span className={styles.oppLabel} style={{ fontSize: '0.8rem' }}>Opportunity #{index + 1}</span>
                <span style={{
                  fontSize: '0.8rem',
                  color: 'var(--primary)',
                  fontWeight: '700',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>
                  High Priority
                </span>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '2rem'
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  <div>
                    <span className={styles.oppLabel}>Identified Problem</span>
                    <h2 style={{
                      fontSize: '1.3rem',
                      fontWeight: '800',
                      color: 'var(--text-main)',
                      marginTop: '0.25rem',
                      marginBottom: '0.5rem',
                      lineHeight: '1.3'
                    }}>
                      {item.problem}
                    </h2>
                  </div>

                  <div>
                    <span className={styles.oppLabel}>Supporting User Evidence</span>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: '1.5', marginTop: '0.25rem' }}>
                      {item.evidence}
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  <div className={styles.oppSolutionBlock}>
                    <span className={styles.oppLabel}>Suggested AI-Driven Feature</span>
                    <p className={styles.oppSolutionValue} style={{ fontSize: '0.95rem', fontWeight: '600', marginTop: '0.25rem' }}>
                      {item.suggested_ai_solution}
                    </p>
                  </div>

                  <div>
                    <span className={styles.oppLabel}>Expected Business Impact</span>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', fontWeight: '500', lineHeight: '1.5', marginTop: '0.25rem' }}>
                      {item.expected_impact}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>⚡</div>
          <p>No product opportunities identified in this batch.</p>
        </div>
      )}
    </div>
  );
}
