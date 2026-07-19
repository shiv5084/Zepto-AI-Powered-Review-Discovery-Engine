import type { Metadata } from 'next';
import './globals.css';
import Navbar from '../components/layout/Navbar';
import Sidebar from '../components/layout/Sidebar';
import { fetchDashboard } from '../lib/fetchDashboard';

export const metadata: Metadata = {
  title: 'Zepto PRDE — Cross-Category Review Discovery Engine Dashboard',
  description: 'AI-Powered review theme extraction, analysis, and discovery engine dashboard for Zepto.',
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  let weekEnding = 'N/A';
  
  try {
    const data = await fetchDashboard();
    weekEnding = data.week_ending;
  } catch (error: any) {
    if (error.message && error.message.includes('Dynamic server usage')) {
      throw error;
    }
    console.error('Error fetching data in root layout:', error);
  }

  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
      </head>
      <body>
        <Navbar weekEnding={weekEnding} />
        <div className="layoutContainer">
          <div className="layoutSidebar">
            <Sidebar />
          </div>
          <main className="layoutMain">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
