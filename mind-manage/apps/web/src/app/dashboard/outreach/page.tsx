'use client';

import { useEffect, useState } from 'react';
import { generateOutreach, listBusinesses, sendOutreach, type BusinessListItem } from '@/lib/api-client';

export default function OutreachPage() {
  const [businesses, setBusinesses] = useState<BusinessListItem[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function loadBusinesses() {
    setBusinesses(await listBusinesses());
  }

  useEffect(() => {
    loadBusinesses().catch(() => setBusinesses([]));
  }, []);

  async function handleGenerate(businessId: string) {
    setBusyId(businessId);

    try {
      await generateOutreach(businessId);
      await loadBusinesses();
    } finally {
      setBusyId(null);
    }
  }

  async function handleSend(messageId: string) {
    setBusyId(messageId);

    try {
      await sendOutreach(messageId);
      await loadBusinesses();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Outreach Automation</div>
        <h1>Generate personalized sales messages</h1>
        <p>Prepare channel-specific messaging, route it through n8n workflows, and keep status synced to the lead dashboard.</p>
      </section>
      <section className="panel" style={{ marginTop: 20 }}>
        <div className="stack">
          {businesses.map((business) => (
            <article className="nav-card" key={business.id}>
              <div className="row-between">
                <div>
                  <h3>{business.name}</h3>
                  <p>{business.latestOutreach?.subject || 'No outreach draft yet.'}</p>
                </div>
                <div className="inline-actions">
                  <button className="button secondary" disabled={busyId === business.id} onClick={() => handleGenerate(business.id)} type="button">
                    {busyId === business.id ? 'Generating...' : 'Generate'}
                  </button>
                  {business.latestOutreach && (
                    <button className="button" disabled={busyId === business.latestOutreach.id} onClick={() => handleSend(business.latestOutreach!.id)} type="button">
                      Send
                    </button>
                  )}
                </div>
              </div>
              <div className="badge-row">
                <span className="badge">{business.latestOutreach?.channel || 'email'}</span>
                <span className="badge">{business.latestOutreach?.status || 'draft'}</span>
              </div>
              <p style={{ marginTop: 12 }}>{business.latestOutreach?.messageBody || 'Drafts appear here once generated from the recommendation.'}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
