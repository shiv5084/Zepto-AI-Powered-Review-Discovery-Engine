'use client';

import React, { useEffect, useState, useRef } from 'react';
import styles from '../../styles/consoleModal.module.css';

interface LogLine {
  type: 'stdout' | 'stderr' | 'error' | 'system';
  text: string;
}

type PhaseStatus = 'pending' | 'running' | 'success' | 'error';

interface ConsoleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

export default function ConsoleModal({ isOpen, onClose, onComplete }: ConsoleModalProps) {
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [exitCode, setExitCode] = useState<number | null>(null);
  const [phaseStatuses, setPhaseStatuses] = useState<PhaseStatus[]>([
    'pending', // Phase 1
    'pending', // Phase 2
    'pending', // Phase 3
    'pending', // Phase 4
  ]);

  const terminalRef = useRef<HTMLDivElement>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll terminal on new log lines
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logLines]);

  // Clean up reader and heartbeat on unmount
  useEffect(() => {
    return () => {
      if (readerRef.current) {
        readerRef.current.cancel().catch(() => { });
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
    };
  }, []);

  // Run the pipeline once the modal opens
  useEffect(() => {
    if (isOpen) {
      startPipeline();
    }
  }, [isOpen]);

  const startPipeline = async () => {
    // Reset states
    setLogLines([{ type: 'system', text: 'Initializing pipeline process...' }]);
    setPhaseStatuses(['pending', 'pending', 'pending', 'pending']);
    setIsRunning(true);
    setIsCompleted(false);
    setExitCode(null);

    // Clear any existing heartbeat
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    try {
      let runUrl = '/api/run-pipeline';
      let pingUrl = '/api/dashboard'; // Fallback to Next.js route which pings backend
      try {
        const urlRes = await fetch('/api/backend-url');
        if (urlRes.ok) {
          const config = await urlRes.json();
          if (config.backendUrl) {
            const cleanUrl = config.backendUrl.replace(/\/$/, '');
            runUrl = `${cleanUrl}/api/run-pipeline`;
            pingUrl = `${cleanUrl}/`;
          }
        }
      } catch (err) {
        console.warn('Failed to fetch backend url config, using local fallback:', err);
      }

      const response = await fetch(runUrl, { method: 'POST' });

      if (!response.body) {
        throw new Error('ReadableStream not supported by browser or backend API');
      }

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || `Server responded with status ${response.status}`);
      }

      // Start UI-to-Backend heartbeat ping to prevent Render free tier inactivity spin-down
      heartbeatIntervalRef.current = setInterval(async () => {
        try {
          await fetch(pingUrl, { method: 'GET', cache: 'no-store' });
          console.log(`Heartbeat ping sent to backend: ${pingUrl}`);
        } catch (pingErr) {
          console.warn('Heartbeat ping failed:', pingErr);
        }
      }, 60000); // Ping every 60 seconds

      const reader = response.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let buffer = '';
      let closedReceived = false;

      // Initialize Phase 1 as running
      setPhaseStatuses(['running', 'pending', 'pending', 'pending']);
      setLogLines((prev) => [...prev, { type: 'system', text: 'Pipeline started successfully.' }]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete last chunk in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          if (trimmed.startsWith(':')) continue; // Ignore SSE comments/pings
          try {
            const parsed = JSON.parse(trimmed);

            // Check process close
            if (parsed.type === 'close') {
              closedReceived = true;
              const code = parsed.code;
              setExitCode(code);
              setIsRunning(false);
              setIsCompleted(true);

              if (code === 0) {
                // All success
                setPhaseStatuses(['success', 'success', 'success', 'success']);
                setLogLines((prev) => [
                  ...prev,
                  { type: 'system', text: 'Pipeline finished successfully with exit code 0.' },
                ]);
                onComplete();
              } else {
                // Fail current running phase
                setPhaseStatuses((prev) => {
                  const updated = [...prev];
                  const activeIdx = updated.findIndex((s) => s === 'running');
                  if (activeIdx !== -1) {
                    updated[activeIdx] = 'error';
                  } else {
                    const firstPending = updated.indexOf('pending');
                    if (firstPending !== -1) updated[firstPending] = 'error';
                  }
                  return updated;
                });
                setLogLines((prev) => [
                  ...prev,
                  { type: 'error', text: `Pipeline script failed with exit code ${code}.` },
                ]);
              }
              break;
            }

            // Standard log lines
            if (parsed.type === 'stdout' || parsed.type === 'stderr') {
              const text = parsed.text;

              // Add to logs
              setLogLines((prev) => [
                ...prev,
                { type: parsed.type as 'stdout' | 'stderr', text },
              ]);

              // Update Phase States based on logs content
              if (text.includes('Executing Phase 1:')) {
                setPhaseStatuses(['running', 'pending', 'pending', 'pending']);
              } else if (text.includes('Executing Phase 2:')) {
                setPhaseStatuses(['success', 'running', 'pending', 'pending']);
              } else if (text.includes('Executing Phase 3:')) {
                setPhaseStatuses(['success', 'success', 'running', 'pending']);
              } else if (text.includes('Executing Phase 4:')) {
                setPhaseStatuses(['success', 'success', 'success', 'running']);
              } else if (text.includes('E2E pipeline execution completed')) {
                setPhaseStatuses(['success', 'success', 'success', 'success']);
              }
            } else if (parsed.type === 'error') {
              setLogLines((prev) => [...prev, { type: 'error', text: parsed.text }]);
            }

          } catch (err) {
            // If it can't parse JSON, print as raw stdout text
            setLogLines((prev) => [...prev, { type: 'stdout', text: line }]);
          }
        }
      }

      if (!closedReceived) {
        // Stream finished but we never got the 'close' event (e.g. backend container slept or went offline)
        setIsRunning(false);
        setIsCompleted(true);
        setExitCode(-1);
        setPhaseStatuses((prev) => {
          const updated = [...prev];
          const activeIdx = updated.findIndex((s) => s === 'running');
          if (activeIdx !== -1) {
            updated[activeIdx] = 'error';
          } else {
            const firstPending = updated.indexOf('pending');
            if (firstPending !== -1) updated[firstPending] = 'error';
          }
          return updated;
        });
        setLogLines((prev) => [
          ...prev,
          { type: 'error', text: 'Connection to backend was closed unexpectedly.' },
        ]);
      }
    } catch (error: any) {
      setIsRunning(false);
      setIsCompleted(true);
      setPhaseStatuses((prev) => {
        const updated = [...prev];
        const activeIdx = updated.findIndex((s) => s === 'running');
        if (activeIdx !== -1) {
          updated[activeIdx] = 'error';
        }
        return updated;
      });
      setLogLines((prev) => [
        ...prev,
        { type: 'error', text: `Failed to execute pipeline: ${error.message}` },
      ]);
    } finally {
      readerRef.current = null;
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
    }
  };

  if (!isOpen) return null;

  const phases = [
    { num: '1', title: 'Ingestion & Scrubbing', desc: 'Fetches raw data & cleans PII' },
    { num: '2', title: 'Theme & Metric Parsing', desc: 'LLM annotates reviews & ratings' },
    { num: '3', title: 'Analytical Discovery', desc: 'Clusters themes & summarizes' },
    { num: '4', title: 'Pulse Report & Export', desc: 'Generates report & JSON payload' },
  ];

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.titleSection}>
            <div className={
              isRunning
                ? styles.indicatorRunning
                : exitCode === 0
                  ? styles.indicatorSuccess
                  : exitCode !== null
                    ? styles.indicatorError
                    : styles.indicator
            } />
            <h2 className={styles.title}>
              {isRunning ? 'Running E2E Orchestration Pipeline' : isCompleted && exitCode === 0 ? 'Pipeline Executed Successfully' : 'Pipeline Execution Stopped'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className={styles.closeButton}
            disabled={isRunning}
            aria-label="Close"
          >
            <svg style={{ width: '20px', height: '20px', fill: 'currentColor' }} viewBox="0 0 24 24">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className={styles.body}>
          {/* Progress Sidebar */}
          <div className={styles.sidebar}>
            {phases.map((p, idx) => {
              const status = phaseStatuses[idx];
              let iconContent: React.ReactNode = p.num;
              let iconClass = styles.phaseIcon;

              if (status === 'running') {
                iconClass = `${styles.phaseIcon} ${styles.phaseIconRunning}`;
                iconContent = (
                  <svg style={{ width: '12px', height: '12px', fill: 'none', stroke: 'currentColor', strokeWidth: 2 }} viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" strokeDasharray="30" strokeDashoffset="10" />
                  </svg>
                );
              } else if (status === 'success') {
                iconClass = `${styles.phaseIcon} ${styles.phaseIconSuccess}`;
                iconContent = (
                  <svg style={{ width: '12px', height: '12px', fill: 'currentColor' }} viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                  </svg>
                );
              } else if (status === 'error') {
                iconClass = `${styles.phaseIcon} ${styles.phaseIconError}`;
                iconContent = (
                  <svg style={{ width: '12px', height: '12px', fill: 'currentColor' }} viewBox="0 0 24 24">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                  </svg>
                );
              }

              return (
                <div
                  key={p.num}
                  className={`${styles.phaseItem} ${status === 'running' ? styles.phaseItemActive : ''} ${status === 'success' ? styles.phaseItemCompleted : ''}`}
                >
                  <div className={iconClass}>{iconContent}</div>
                  <div className={styles.phaseText}>
                    <span className={styles.phaseTitle}>{p.title}</span>
                    <span className={styles.phaseDesc}>{p.desc}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Terminal Screen */}
          <div ref={terminalRef} className={styles.terminal}>
            {logLines.map((line, idx) => {
              let lineClass = styles.logStdout;
              if (line.type === 'stderr') lineClass = styles.logStderr;
              else if (line.type === 'error') lineClass = styles.logError;
              else if (line.type === 'system') lineClass = styles.logSystem;

              return (
                <div key={idx} className={`${styles.logLine} ${lineClass}`}>
                  {line.text}
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <div className={styles.statusText}>
            {isRunning ? (
              <span>Running... This can take 30 seconds to 15+ mins depending on LLM response times.</span>
            ) : isCompleted ? (
              exitCode === 0 ? (
                <span style={{ color: 'var(--primary)' }}>Pipeline completed successfully! Dashboard data updated.</span>
              ) : (
                <span style={{ color: '#e91429' }}>Pipeline failed. Please check the logs.</span>
              )
            ) : (
              <span>Ready to run pipeline.</span>
            )}
          </div>
          <div>
            <button
              onClick={onClose}
              className={styles.actionButton}
              disabled={isRunning}
            >
              {exitCode === 0 ? 'View Updated Dashboard' : 'Close Console'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
