import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const maxDuration = 60;

export async function GET() {
  // ── 1. Local-dev primary path: ../data/processed/annotated_reviews.json ──
  const envDataPath = process.env.ANNOTATED_REVIEWS_PATH || '../data/processed/annotated_reviews.json';
  const localPath = path.resolve(process.cwd(), envDataPath);
  
  let rawData: string | null = null;

  if (fs.existsSync(localPath)) {
    try {
      rawData = fs.readFileSync(localPath, 'utf-8');
    } catch (e: any) {
      console.error('Failed to read local annotated reviews:', e.message);
    }
  }

  // ── 2. Vercel-compatible fallback: frontend/public/annotated_reviews.json ──
  if (!rawData) {
    const publicPath = path.join(process.cwd(), 'public', 'annotated_reviews.json');
    if (fs.existsSync(publicPath)) {
      try {
        rawData = fs.readFileSync(publicPath, 'utf-8');
      } catch (e: any) {
        console.error('Failed to read public/annotated_reviews.json:', e.message);
      }
    }
  }

  if (!rawData) {
    return NextResponse.json(
      {
        error: 'Annotated reviews data not available.',
        details: `Could not locate data file. Checked: (1) Local path: ${localPath}, (2) Public path: ${path.join(process.cwd(), 'public', 'annotated_reviews.json')}`
      },
      { status: 404 }
    );
  }

  try {
    const allReviews = JSON.parse(rawData);
    if (!Array.isArray(allReviews)) {
      throw new Error('Data is not a JSON array');
    }

    // Get up to 50 items (take the first 50 as a sample representation)
    const sampledReviews = allReviews.slice(0, 50).map((r: any) => ({
      text: r.text || '',
      sentiment: r.sentiment || 'neutral',
      rating: typeof r.rating === 'number' ? r.rating : null,
      source: r.source || 'unknown',
      date: r.date || ''
    }));

    return NextResponse.json(sampledReviews, {
      headers: { 'Cache-Control': 'no-store' }
    });
  } catch (err: any) {
    console.error('Failed to parse annotated reviews JSON:', err.message);
    return NextResponse.json(
      { error: 'Failed to process annotated reviews.', details: err.message },
      { status: 500 }
    );
  }
}
