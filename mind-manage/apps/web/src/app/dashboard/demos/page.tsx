'use client';

import { useEffect, useState } from 'react';
import { ErrorBanner } from '@/components/error-banner';
import { generateDemo, listBusinesses, type BusinessListItem } from '@/lib/api-client';

export default function DemosPage() {
  const [businesses, setBusinesses] = useState<BusinessListItem[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadBusinesses() {
    setBusinesses(await listBusinesses());
  }

  useEffect(() => {
    loadBusinesses().catch(() => setBusinesses([]));
  }, []);

  async function handleGenerate(businessId: string) {
    setBusyId(businessId);
    setError(null);

    try {
      await generateDemo(businessId);
      await loadBusinesses();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate demo.');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Instant Demo Generator</div>
        <h1>Reusable niche templates</h1>
        <p>Generate tailored demo pages that show how the client business can improve with your software.</p>
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
      </section>
      <section className="panel" style={{ marginTop: 20 }}>
        <div className="stack">
          {businesses.map((business) => (
            <article className="nav-card" key={business.id}>
              <div className="row-between">
                <div>
                  <h3>{business.name}</h3>
                  <p>{business.latestDemo?.headline || 'No demo generated yet.'}</p>
                </div>
                <button className="button secondary" disabled={busyId === business.id} onClick={() => handleGenerate(business.id)} type="button">
                  {busyId === business.id ? 'Generating...' : 'Generate demo'}
                </button>
              </div>
              <div className="badge-row">
                <span className="badge">{business.latestDemo?.templateName || 'Template pending'}</span>
                {business.latestDemo?.demoUrl && <span className="badge">{business.latestDemo.demoUrl}</span>}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
