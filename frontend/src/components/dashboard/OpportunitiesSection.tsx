import React from 'react';
import Link from 'next/link';
import { Opportunity } from '../../lib/types';
import styles from '../../styles/dashboard.module.css';

interface OpportunitiesSectionProps {
  opportunities: Opportunity[];
}

export default function OpportunitiesSection({ opportunities }: OpportunitiesSectionProps) {
  const hasData = opportunities && opportunities.length > 0;

  return (
    <section id="opportunities-list" className={styles.gridSection}>
      <div className={styles.sectionHeader}>
        <div>
          <h2 className={styles.sectionTitle}>
            <span className={styles.sectionTitleIcon}>⚡</span>
            9. Top 3 Product Opportunities
          </h2>
          <p className={styles.sectionSubtitle}>
            AI-driven features designed to solve critical pain points and unlock new value.
          </p>
        </div>
      </div>

      {hasData ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className={styles.oppGrid}>
            {opportunities.slice(0, 3).map((item, index) => (
              <div key={index} className={styles.oppCard}>
                <div className={styles.oppProblemBlock}>
                  <span className={styles.oppLabel}>Problem Statement</span>
                  <h3 className={styles.oppProblemTitle}>{item.problem}</h3>
                  <span className={styles.oppLabel}>Evidence Base</span>
                  <p className={styles.oppValue}>{item.evidence}</p>
                </div>
                
                <div className={styles.oppSolutionBlock}>
                  <span className={styles.oppLabel}>Suggested AI Solution</span>
                  <p className={styles.oppSolutionValue}>{item.suggested_ai_solution}</p>
                </div>

                <div>
                  <span className={styles.oppLabel}>Expected Business Impact</span>
                  <p className={styles.oppValue}>{item.expected_impact}</p>
                </div>
              </div>
            ))}
          </div>
          
          <Link href="/opportunities" style={{ alignSelf: 'center' }}>
            <button className={styles.viewAllButton}>
              Explore Expanded Opportunities View &rarr;
            </button>
          </Link>
        </div>
      ) : (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>⚡</div>
          <p>No product opportunities identified in this batch.</p>
        </div>
      )}
    </section>
  );
}
