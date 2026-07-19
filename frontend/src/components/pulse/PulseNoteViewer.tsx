'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import styles from '../../styles/pulse.module.css';

interface PulseNoteViewerProps {
  pulseNoteText: string;
  weekEnding?: string;
}

export default function PulseNoteViewer({ pulseNoteText, weekEnding = 'N/A' }: PulseNoteViewerProps) {
  return (
    <div className={styles.pulseContainer}>
      <div className={styles.header}>
        <h1 className={styles.title}>Weekly Executive Pulse Note</h1>
        <div className={styles.meta}>
          <span>Week Ending: <strong>{weekEnding}</strong></span>
          <span className={styles.badge}>AI-Generated Summary</span>
        </div>
      </div>
      <div className={styles.markdown}>
        <ReactMarkdown>{pulseNoteText}</ReactMarkdown>
      </div>
    </div>
  );
}
