'use client';

import { useEffect, useRef, useState } from 'react';
import { generateRecommendation, listBusinesses, type BusinessListItem } from '@/lib/api-client';

export default function RecommendationsPage() {
  const [businesses, setBusinesses] = useState<BusinessListItem[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const lockRef = useRef(false);

  async function loadBusinesses() {
    setBusinesses(await listBusinesses());
  }

  useEffect(() => {
    loadBusinesses().catch(() => setBusinesses([]));
  }, []);

  async function handleGenerate(businessId: string) {
    if (lockRef.current) return;
    lockRef.current = true;
    setBusyId(businessId);

    try {
      await generateRecommendation(businessId);
      await loadBusinesses();
    } finally {
      lockRef.current = false;
      setBusyId(null);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">AI Recommendations</div>
        <h1>Translate findings into productized offers</h1>
        <p>Package scan output into solution recommendations, pricing direction, and implementation angle for each lead.</p>
      </section>
      <section className="panel" style={{ marginTop: 20 }}>
        <div className="nav-grid">
          {businesses.map((business) => (
            <article className="nav-card" key={business.id}>
              <div className="row-between">
                <div>
                  <h3>{business.name}</h3>
                  <p>{business.niche} in {business.city}</p>
                </div>
                <button className="button secondary" disabled={busyId !== null} onClick={() => handleGenerate(business.id)} type="button">
                  {busyId === business.id ? 'Generating...' : 'Generate'}
                </button>
              </div>
              <p style={{ marginTop: 12 }}>{business.latestRecommendation?.summary || 'No recommendation yet. Generate one from the latest scan.'}</p>
              <div className="badge-row">
                {business.latestRecommendation?.recommendedModules?.map((module) => (
                  <span className="badge" key={module}>{module}</span>
                ))}
                {business.latestRecommendation?.pricingHint && <span className="badge">{business.latestRecommendation.pricingHint}</span>}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
