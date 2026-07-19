'use client';

import React, { useEffect, useState } from 'react';
import SentimentSummary from '../../components/dashboard/SentimentSummary';
import RepeatPurchaseDriversSection from '../../components/dashboard/RepeatPurchaseDriversSection';
import ExplorationBarriersSection from '../../components/dashboard/ExplorationBarriersSection';
import DiscoveryMethodsSection from '../../components/dashboard/DiscoveryMethodsSection';
import HabitDriversSection from '../../components/dashboard/HabitDriversSection';
import InformationNeedsSection from '../../components/dashboard/InformationNeedsSection';
import FrustrationsSection from '../../components/dashboard/FrustrationsSection';
import SegmentsSection from '../../components/dashboard/SegmentsSection';
import UnmetNeedsSection from '../../components/dashboard/UnmetNeedsSection';
import OpportunitiesSection from '../../components/dashboard/OpportunitiesSection';
import styles from '../../styles/dashboard.module.css';

export default function DashboardPage() {
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
        console.error('Error fetching dashboard data:', err);
        setErrorMsg(err.message || 'Unknown error occurred while loading dashboard data.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.headerSection}>
          <h1 className={styles.pageTitle}>Executive Review Discovery Dashboard</h1>
          <p className={styles.pageSubtitle}>Loading metrics...</p>
        </div>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>🔄</div>
          <p>Fetching the latest review intelligence from database...</p>
        </div>
      </div>
    );
  }

  if (errorMsg || !data) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.headerSection}>
          <h1 className={styles.pageTitle}>Executive Review Discovery Dashboard</h1>
          <p className={styles.pageSubtitle}>Unable to load dashboard data.</p>
        </div>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>⚠️</div>
          <p>Error loading dashboard metrics: {errorMsg || 'Data file not found.'}</p>
          <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
            Please ensure you have executed the Python pipeline to generate the data: <code>python main.py</code>
          </p>
        </div>
      </div>
    );
  }

  const { metrics } = data;

  return (
    <div className={styles.dashboardContainer}>
      <div className={styles.headerSection}>
        <h1 className={styles.pageTitle}>Executive Review Discovery Dashboard</h1>
        <p className={styles.pageSubtitle}>
          Weekly aggregated insights, metric visualisations, and AI-discovered opportunities from Zepto user feedback.
        </p>
      </div>

      <SentimentSummary distribution={data.sentiment_distribution} />

      <RepeatPurchaseDriversSection drivers={metrics.repeat_purchase_drivers || []} />
      <ExplorationBarriersSection barriers={metrics.exploration_barriers || []} />
      <DiscoveryMethodsSection methods={metrics.discovery_methods || []} />
      <HabitDriversSection drivers={metrics.habit_drivers || []} />
      <InformationNeedsSection needs={metrics.information_needs || []} />
      <FrustrationsSection frustrations={metrics.top_frustrations || []} />
      <SegmentsSection segments={metrics.underserved_segments || []} />
      <UnmetNeedsSection needs={metrics.unmet_needs || []} />
      <OpportunitiesSection opportunities={metrics.opportunities || []} />
    </div>
  );
}
