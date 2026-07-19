'use client';

import React, { useEffect, useState } from 'react';
import styles from '../../styles/dashboard.module.css';

interface Review {
  text: string;
  sentiment: string;
  rating: number | null;
  source: string;
  date: string;
}

export default function VoiceOfCustomerPage() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [filteredReviews, setFilteredReviews] = useState<Review[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadReviews() {
      try {
        const res = await fetch('/api/voc', { cache: 'no-store' });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `HTTP error! Status: ${res.status}`);
        }
        const json = await res.json();
        setReviews(json);
        setFilteredReviews(json);
      } catch (err: any) {
        console.error('Error loading voice of customer reviews:', err);
        setErrorMsg(err.message || 'Unknown error occurred while fetching reviews.');
      } finally {
        setLoading(false);
      }
    }
    loadReviews();
  }, []);

  // Filter reviews when search term or sentiment filter changes
  useEffect(() => {
    let result = reviews;

    if (searchTerm.trim() !== '') {
      const term = searchTerm.toLowerCase();
      result = result.filter(r => r.text.toLowerCase().includes(term));
    }

    if (sentimentFilter !== 'all') {
      result = result.filter(r => r.sentiment === sentimentFilter);
    }

    setFilteredReviews(result);
  }, [searchTerm, sentimentFilter, reviews]);

  const getSentimentBadgeStyle = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case 'positive':
        return {
          background: 'rgba(6, 214, 160, 0.12)',
          color: '#06D6A0',
          border: '1px solid rgba(6, 214, 160, 0.3)'
        };
      case 'negative':
        return {
          background: 'rgba(239, 71, 111, 0.12)',
          color: '#EF476F',
          border: '1px solid rgba(239, 71, 111, 0.3)'
        };
      default:
        return {
          background: 'rgba(255, 183, 3, 0.12)',
          color: '#FFB703',
          border: '1px solid rgba(255, 183, 3, 0.3)'
        };
    }
  };

  const getSourceIcon = (source: string) => {
    switch (source.toLowerCase()) {
      case 'google_play':
        return '🤖 Google Play';
      case 'app_store':
        return '🍎 App Store';
      case 'reddit':
        return '💬 Reddit';
      case 'twitter':
      case 'x':
        return '🐦 X/Twitter';
      default:
        return '⭐ Trustpilot';
    }
  };

  const renderStars = (rating: number | null) => {
    if (rating === null) return null;
    return '★'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating));
  };

  if (loading) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>🔄</div>
          <p>Loading Voice of Customer review feed...</p>
        </div>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>⚠️</div>
          <p>Error loading reviews: {errorMsg}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.dashboardContainer}>
      <div className={styles.headerSection}>
        <h1 className={styles.pageTitle}>Voice of Customer</h1>
        <p className={styles.pageSubtitle}>
          A direct feed of 50 sampled user reviews with sentiment tagging and rating metrics from Zepto.
        </p>
      </div>

      {/* Filter and Search Bar Container */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '1.25rem',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '1rem',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {/* Search Input */}
        <div style={{ flex: 1, minWidth: '280px', position: 'relative' }}>
          <input
            type="text"
            placeholder="Search review content..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '0.6rem 1rem',
              color: '#fff',
              fontSize: '0.9rem',
              outline: 'none'
            }}
          />
        </div>

        {/* Sentiment Select Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Sentiment:</span>
          <select
            value={sentimentFilter}
            onChange={(e) => setSentimentFilter(e.target.value)}
            style={{
              background: 'var(--bg-base)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '0.6rem 1rem',
              color: '#fff',
              fontSize: '0.9rem',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="all">All Sentiments</option>
            <option value="positive">Positive</option>
            <option value="neutral">Neutral</option>
            <option value="negative">Negative</option>
          </select>
        </div>
      </div>

      {/* Reviews Feed List */}
      {filteredReviews.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {filteredReviews.map((item, index) => (
            <div
              key={index}
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
                transition: 'transform 0.2s ease, border-color 0.2s ease'
              }}
            >
              {/* Card Meta Info Header */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '0.5rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <span style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    background: 'rgba(255, 255, 255, 0.05)',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '4px',
                    color: 'var(--text-muted)'
                  }}>
                    {getSourceIcon(item.source)}
                  </span>
                  {item.rating !== null && (
                    <span style={{ color: '#FFB703', fontSize: '0.85rem', letterSpacing: '0.05em' }}>
                      {renderStars(item.rating)}
                    </span>
                  )}
                  {item.date && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {item.date}
                    </span>
                  )}
                </div>

                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  padding: '0.2rem 0.6rem',
                  borderRadius: '4px',
                  letterSpacing: '0.05em',
                  ...getSentimentBadgeStyle(item.sentiment)
                }}>
                  {item.sentiment}
                </span>
              </div>

              {/* Review Text content */}
              <p style={{
                fontSize: '0.95rem',
                lineHeight: '1.6',
                color: 'var(--text-main)',
                margin: 0
              }}>
                {item.text}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <div className={styles.emptyStateIcon}>🔍</div>
          <p>No reviews match your filters.</p>
        </div>
      )}
    </div>
  );
}
