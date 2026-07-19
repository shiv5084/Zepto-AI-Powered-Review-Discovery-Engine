import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  // ── 1. Try the Render FastAPI backend (production primary path) ───────────
  const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  try {
    const res = await fetch(`${backendUrl}/api/dashboard`, {
      cache: 'no-store'
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {
    console.warn('FastAPI backend unreachable. Trying filesystem fallbacks.');
  }

  // ── 2. Local-dev fallback: ../data/dashboard_data.json (relative to frontend/) ──
  // Works when running `npm run dev` locally where process.cwd() = frontend/
  const envDataPath = process.env.DASHBOARD_DATA_PATH || '../data/dashboard_data.json';
  const localPath = path.resolve(process.cwd(), envDataPath);
  if (fs.existsSync(localPath)) {
    try {
      const raw = fs.readFileSync(localPath, 'utf-8');
      const data = JSON.parse(raw);
      return NextResponse.json(data, { headers: { 'Cache-Control': 'no-store' } });
    } catch (e: any) {
      console.error('Failed to read local fallback file:', e.message);
    }
  }

  // ── 3. Vercel-compatible fallback: frontend/public/dashboard_data.json ────
  // On Vercel, process.cwd() = /var/task  and public/ files are at /var/task/public/
  // This is the correct location when BACKEND_URL is not configured.
  const publicPath = path.join(process.cwd(), 'public', 'dashboard_data.json');
  if (fs.existsSync(publicPath)) {
    try {
      const raw = fs.readFileSync(publicPath, 'utf-8');
      const data = JSON.parse(raw);
      return NextResponse.json(data, { headers: { 'Cache-Control': 'no-store' } });
    } catch (e: any) {
      console.error('Failed to read public/dashboard_data.json:', e.message);
    }
  }

  // ── 4. All paths failed ───────────────────────────────────────────────────
  return NextResponse.json(
    {
      error: 'Dashboard data not available.',
      details: 'All sources failed: Render backend unreachable, public/dashboard_data.json missing, and local fallback missing.',
      hint: 'Set BACKEND_URL in Vercel environment variables pointing to your Render service URL.'
    },
    { status: 404 }
  );
}
