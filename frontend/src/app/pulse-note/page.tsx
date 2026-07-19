'use client';

import React, { useEffect, useState } from 'react';
import PulseNoteViewer from '../../components/pulse/PulseNoteViewer';
import styles from '../../styles/dashboard.module.css';

export default function PulseNotePage() {
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
        console.error('Error fetching pulse note data:', err);
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
          <p>Loading weekly pulse note...</p>
        </div>
      </div>
    );
  }

  if (errorMsg || !data) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>⚠️</div>
          <p>Error loading pulse note: {errorMsg || 'Data file not found.'}</p>
        </div>
      </div>
    );
  }

  return (
    <PulseNoteViewer
      pulseNoteText={data.pulse_note_text}
      weekEnding={data.week_ending}
    />
  );
}
