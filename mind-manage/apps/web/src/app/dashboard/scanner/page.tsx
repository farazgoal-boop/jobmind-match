'use client';

import { useEffect, useState } from 'react';
import { listBusinesses, runScan, type BusinessListItem } from '@/lib/api-client';

export default function ScannerPage() {
  const [businesses, setBusinesses] = useState<BusinessListItem[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function loadBusinesses() {
    setBusinesses(await listBusinesses());
  }

  useEffect(() => {
    loadBusinesses().catch(() => setBusinesses([]));
  }, []);

  async function handleScan(businessId: string) {
    setBusyId(businessId);

    try {
      await runScan(businessId);
      await loadBusinesses();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Website Scanner</div>
        <h1>Potential revenue loss detected</h1>
        <p>Scanner output combines deterministic checks and AI summarization to explain missed lead capture and workflow gaps.</p>
      </section>
      <section className="panel" style={{ marginTop: 20 }}>
        <div className="stack">
          {businesses.map((business) => (
            <article className="nav-card" key={business.id}>
              <div className="row-between">
                <div>
                  <h3>{business.name}</h3>
                  <p>{business.niche} in {business.city}</p>
                </div>
                <button className="button secondary" disabled={busyId === business.id} onClick={() => handleScan(business.id)} type="button">
                  {busyId === business.id ? 'Scanning...' : 'Rescan'}
                </button>
              </div>
              <div className="badge-row">
                <span className="badge">Opportunity: {business.latestScan?.opportunityScore ?? '--'}</span>
                <span className="badge">Lead capture: {business.latestScan?.leadCaptureScore ?? '--'}</span>
                <span className="badge">Response: {business.latestScan?.responseScore ?? '--'}</span>
              </div>
              <ul className="issue-list">
                {(business.latestScan?.issues ?? []).map((issue) => (
                  <li key={issue.id || issue.issueType}>
                    <strong>{issue.issueType.replaceAll('_', ' ')}</strong>: {issue.description}
                  </li>
                ))}
                {!business.latestScan && <li>No scan yet. Run the scanner to generate issues.</li>}
              </ul>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
