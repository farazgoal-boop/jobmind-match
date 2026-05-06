'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { MetricCard } from '@/components/dashboard/metric-card';
import { getDashboardSummary, type DashboardSummary } from '@/lib/api-client';
import { dashboardModules } from '@/lib/constants';

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    getDashboardSummary().then(setSummary).catch(() => setSummary(null));
  }, []);

  return (
    <main className="shell">
      <section className="hero">
        <div className="panel">
          <div className="kicker">Executive Dashboard</div>
          <h1>Find software pain points before competitors do.</h1>
          <p>
            This dashboard is designed for discovering leads, scanning websites, estimating revenue leakage,
            generating demos, and automating outreach across multiple channels.
          </p>
          <div className="badge-row">
            <span className="badge">Opportunity scoring</span>
            <span className="badge">Reusable demos</span>
            <span className="badge">Lead pipeline</span>
          </div>
        </div>
        <div className="panel grid metrics">
          <MetricCard label="Businesses discovered" value={String(summary?.businessesDiscovered ?? '--')} note="Across all tracked prospects" />
          <MetricCard label="High-opportunity sites" value={String(summary?.highOpportunitySites ?? '--')} note="Opportunity score 70 or above" />
          <MetricCard label="Meetings booked" value={String(summary?.meetingsBooked ?? '--')} note="Live pipeline count" />
          <MetricCard label="Projected value" value={summary ? `$${summary.projectedValue}` : '--'} note={`${summary?.closedDeals ?? 0} closed-won deals so far`} />
        </div>
      </section>

      <section className="panel">
        <div className="kicker">Modules</div>
        <div className="nav-grid">
          {dashboardModules.map((item) => (
            <Link className="nav-card" key={item.href} href={item.href}>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
