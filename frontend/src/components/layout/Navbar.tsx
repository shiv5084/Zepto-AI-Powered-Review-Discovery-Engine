'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import styles from '../../styles/navbar.module.css';
import ConsoleModal from './ConsoleModal';

interface NavbarProps {
  weekEnding?: string;
}

export default function Navbar({ weekEnding = 'N/A' }: NavbarProps) {
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  const handleRunPipeline = () => {
    setIsConsoleOpen(true);
  };

  const handlePipelineComplete = () => {
    // Refresh the router to refetch Server Component data (re-reads dashboard_data.json)
    router.refresh();
  };

  const isDashboard = pathname === '/dashboard' || pathname === '/' || pathname === '';

  return (
    <>
      <nav className={styles.navbar}>
        <div className={styles.logoContainer}>
          <div className={styles.logoIcon}>
            <svg viewBox="0 0 24 24" style={{ width: '24px', height: '24px', fill: 'currentColor' }}>
              <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.9 2 1.99 2 2-.9 2-2-.9-2-2-2z"/>
            </svg>
          </div>
          <div>
            <h1 className={styles.title}>Zepto PRDE</h1>
            <span className={styles.subtitle}>Cross-Category Discovery</span>
          </div>
        </div>

        <div className={styles.metaInfo}>
          <div className={styles.weekLabel}>
            Week Ending: <span className={styles.weekValue}>{weekEnding}</span>
          </div>
          <button 
            onClick={handleRunPipeline} 
            className={styles.runButton}
            disabled={isConsoleOpen}
          >
            {isConsoleOpen ? (
              <>
                <span style={{
                  display: 'inline-block',
                  width: '12px',
                  height: '12px',
                  border: '2px solid #000',
                  borderTop: '2px solid transparent',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
                Running...
              </>
            ) : (
              <>
                <svg style={{ width: '14px', height: '14px', fill: 'currentColor' }} viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
                Run Pipeline
              </>
            )}
          </button>
        </div>

        <div className={styles.mobileNav}>
          <Link href="/dashboard" className={`${styles.mobileLink} ${isDashboard ? styles.activeMobileLink : ''}`}>
            Dashboard
          </Link>
          <Link href="/pulse-note" className={`${styles.mobileLink} ${pathname === '/pulse-note' ? styles.activeMobileLink : ''}`}>
            Pulse Note
          </Link>
          <Link href="/opportunities" className={`${styles.mobileLink} ${pathname === '/opportunities' ? styles.activeMobileLink : ''}`}>
            Opportunities
          </Link>
          <Link href="/voice-of-customer" className={`${styles.mobileLink} ${pathname === '/voice-of-customer' ? styles.activeMobileLink : ''}`}>
            VOC
          </Link>
        </div>

        <style jsx global>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </nav>

      <ConsoleModal 
        isOpen={isConsoleOpen} 
        onClose={() => setIsConsoleOpen(false)} 
        onComplete={handlePipelineComplete}
      />
    </>
  );
}

