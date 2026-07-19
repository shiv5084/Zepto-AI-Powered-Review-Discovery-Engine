import fs from 'fs';
import path from 'path';
import { DashboardData } from './types';

export async function fetchDashboard(): Promise<DashboardData> {
  if (typeof window === 'undefined') {
    // ── Server-side path resolution ───────────────────────────────────────
    // On Vercel: process.cwd() = /var/task
    //   public/ files are bundled at /var/task/public/  ← check here first
    //   ../data/ does NOT exist on Vercel               ← local dev only

    // ① Try the Render FastAPI backend first (production primary path)
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
    try {
      const res = await fetch(`${backendUrl}/api/dashboard`, {
        cache: 'no-store'
      });
      if (res.ok) {
        return await res.json() as DashboardData;
      }
    } catch (err: any) {
      if (err.message && err.message.includes('Dynamic server usage')) {
        throw err;
      }
      console.warn('fetchDashboard server-side: FastAPI backend unreachable. Trying filesystem fallbacks. Error:', err.message);
    }

    // ② Local dev fallback: ../data/dashboard_data.json (relative to frontend/)
    const dataPath = process.env.DASHBOARD_DATA_PATH || '../data/dashboard_data.json';
    const localPath = path.resolve(process.cwd(), dataPath);
    if (fs.existsSync(localPath)) {
      const raw = fs.readFileSync(localPath, 'utf-8');
      return JSON.parse(raw) as DashboardData;
    }

    // ③ Vercel-compatible: public/dashboard_data.json
    const publicPath = path.join(process.cwd(), 'public', 'dashboard_data.json');
    if (fs.existsSync(publicPath)) {
      const raw = fs.readFileSync(publicPath, 'utf-8');
      return JSON.parse(raw) as DashboardData;
    }

    // ④ None of the locations have the file
    throw new Error(
      `Dashboard data not found. Checked:\n  (1) FastAPI Backend at ${backendUrl}\n  (2) Local path ${localPath}\n  (3) Public fallback ${publicPath}`
    );
  } else {
    // Client-side: call the Next.js API route which has its own fallback chain
    const res = await fetch('/api/dashboard');
    if (!res.ok) {
      throw new Error('Failed to fetch dashboard data from /api/dashboard');
    }
    return res.json() as Promise<DashboardData>;
  }
}
