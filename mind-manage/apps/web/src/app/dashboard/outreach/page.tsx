'use client';

import { useEffect, useRef, useState } from 'react';
import { ErrorBanner } from '@/components/error-banner';
import { listBusinesses, quickGenerateOutreach, sendOutreach, type BusinessListItem } from '@/lib/api-client';

export default function OutreachPage() {
  const [businesses, setBusinesses] = useState<BusinessListItem[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lockRef = useRef(false);

  async function loadBusinesses() {
    setBusinesses(await listBusinesses());
  }

  useEffect(() => {
    loadBusinesses().catch(() => setBusinesses([]));
  }, []);

  async function handleAutoGenerate(businessId: string) {
    if (lockRef.current) return;
    lockRef.current = true;
    setBusyId(businessId);
    setError(null);

    try {
      await quickGenerateOutreach(businessId);
      await loadBusinesses();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate outreach.');
    } finally {
      lockRef.current = false;
      setBusyId(null);
    }
  }

  async function handleSend(messageId: string) {
    if (lockRef.current) return;
    lockRef.current = true;
    setBusyId(messageId);
    setError(null);

    try {
      await sendOutreach(messageId);
      await loadBusinesses();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send outreach.');
    } finally {
      lockRef.current = false;
      setBusyId(null);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Outreach Automation</div>
        <h1>Generate personalized sales messages</h1>
        <p>Prepare channel-specific messaging, route it through n8n workflows, and keep status synced to the lead dashboard.</p>
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
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
                  <button
                    className="button secondary"
                    disabled={busyId !== null}
                    onClick={() => handleAutoGenerate(business.id)}
                    type="button"
                  >
                    {busyId === business.id ? 'Generating...' : 'Auto Generate'}
                  </button>
                  {business.latestOutreach && (
                    <button
                      className="button"
                      disabled={busyId !== null}
                      onClick={() => handleSend(business.latestOutreach!.id)}
                      type="button"
                    >
                      {busyId === business.latestOutreach.id ? 'Sending...' : 'Send'}
                    </button>
                  )}
                </div>
              </div>
              <div className="badge-row">
                <span className="badge">{business.latestOutreach?.channel || 'email'}</span>
                <span className="badge">{business.latestOutreach?.status || 'draft'}</span>
              </div>
              <p style={{ marginTop: 12 }}>{business.latestOutreach?.messageBody || 'Click Auto Generate to scan, analyse, and draft an outreach email in one step.'}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
