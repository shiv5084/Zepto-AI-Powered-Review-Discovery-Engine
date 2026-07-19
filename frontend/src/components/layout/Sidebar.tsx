'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import styles from '../../styles/sidebar.module.css';

export default function Sidebar() {
  const pathname = usePathname();

  const handleScrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      const navbarHeight = 70; // var(--navbar-height)
      const elementPosition = element.getBoundingClientRect().top + window.scrollY;
      const offsetPosition = elementPosition - navbarHeight - 20; // 20px padding

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  };

  const isDashboard = pathname === '/dashboard' || pathname === '/';

  return (
    <aside className={styles.sidebar}>
      {/* Navigation section */}
      <div className={styles.section}>
        <span className={styles.sectionTitle}>Navigation</span>
        
        <Link 
          href="/dashboard" 
          className={`${styles.navLink} ${isDashboard ? styles.navLinkActive : ''}`}
        >
          <svg style={{ width: '18px', height: '18px', fill: 'currentColor' }} viewBox="0 0 24 24">
            <path d="M4 13h6c.55 0 1-.45 1-1V4c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v8c0 .55.45 1 1 1zm0 8h6c.55 0 1-.45 1-1v-4c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1zm10 0h6c.55 0 1-.45 1-1v-8c0-.55-.45-1-1-1h-6c-.55 0-1 .45-1 1v8c0 .55.45 1 1 1zM14 4v4c0 .55.45 1 1 1h6c.55 0 1-.45 1-1V4c0-.55-.45-1-1-1h-6c-.55 0-1 .45-1 1z"/>
          </svg>
          Dashboard
        </Link>

        <Link 
          href="/pulse-note" 
          className={`${styles.navLink} ${pathname === '/pulse-note' ? styles.navLinkActive : ''}`}
        >
          <svg style={{ width: '18px', height: '18px', fill: 'currentColor' }} viewBox="0 0 24 24">
            <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
          </svg>
          Pulse Note
        </Link>

        <Link 
          href="/opportunities" 
          className={`${styles.navLink} ${pathname === '/opportunities' ? styles.navLinkActive : ''}`}
        >
          <svg style={{ width: '18px', height: '18px', fill: 'currentColor' }} viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H7c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.04-.42 1.99-1.07 2.75z"/>
          </svg>
          Opportunities
        </Link>

        <Link 
          href="/voice-of-customer" 
          className={`${styles.navLink} ${pathname === '/voice-of-customer' ? styles.navLinkActive : ''}`}
        >
          <svg style={{ width: '18px', height: '18px', fill: 'currentColor' }} viewBox="0 0 24 24">
            <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/>
          </svg>
          Voice of Customer
        </Link>
      </div>

      {/* Jump section (only visible on dashboard page) */}
      {isDashboard && (
        <div className={styles.section}>
          <span className={styles.sectionTitle}>Jump to Section</span>
          <div className={styles.jumpLinks}>
            <div onClick={() => handleScrollToSection('repeat-purchase-drivers')} className={styles.jumpLink}>
              1. Repeat-Purchasing
            </div>
            <div onClick={() => handleScrollToSection('exploration-barriers')} className={styles.jumpLink}>
              2. Exploration Barriers
            </div>
            <div onClick={() => handleScrollToSection('discovery-methods')} className={styles.jumpLink}>
              3. Discovery Methods
            </div>
            <div onClick={() => handleScrollToSection('habit-drivers')} className={styles.jumpLink}>
              4. Habit-Driven
            </div>
            <div onClick={() => handleScrollToSection('information-needs')} className={styles.jumpLink}>
              5. Information Gaps
            </div>
            <div onClick={() => handleScrollToSection('frustrations')} className={styles.jumpLink}>
              6. User Frustrations
            </div>
            <div onClick={() => handleScrollToSection('segments')} className={styles.jumpLink}>
              7. User Segments
            </div>
            <div onClick={() => handleScrollToSection('unmet-needs')} className={styles.jumpLink}>
              8. Unmet Needs
            </div>
            <div onClick={() => handleScrollToSection('opportunities-list')} className={styles.jumpLink}>
              9. Opportunities
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
