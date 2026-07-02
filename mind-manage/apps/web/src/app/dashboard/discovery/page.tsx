'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { ErrorBanner } from '@/components/error-banner';
import { createBusiness, listBusinesses, runScan, type BusinessListItem, type CreateBusinessPayload } from '@/lib/api-client';

export default function DiscoveryPage() {
  const [businesses, setBusinesses] = useState<BusinessListItem[]>([]);
  const [form, setForm] = useState<CreateBusinessPayload>({
    name: '',
    niche: '',
    city: '',
    website: '',
    phone: '',
    email: '',
    source: 'manual'
  });
  const [busyId, setBusyId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lockRef = useRef(false);

  async function loadBusinesses() {
    setBusinesses(await listBusinesses());
  }

  useEffect(() => {
    loadBusinesses().catch(() => setBusinesses([]));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);

    try {
      await createBusiness(form);
      setForm({ name: '', niche: '', city: '', website: '', phone: '', email: '', source: 'manual' });
      await loadBusinesses();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add business.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleScan(businessId: string) {
    if (lockRef.current) return;
    lockRef.current = true;
    setBusyId(businessId);
    setError(null);

    try {
      await runScan(businessId);
      await loadBusinesses();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run scan.');
    } finally {
      lockRef.current = false;
      setBusyId(null);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Business Discovery</div>
        <h1>Search by niche and city</h1>
        <p>Use Google Maps and directory providers to discover businesses, enrich their contacts, and queue them for scanning.</p>
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
        <form className="form-grid" onSubmit={handleSubmit} style={{ marginTop: 20 }}>
          <input className="input" placeholder="Business name" value={form.name ?? ''} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required />
          <input className="input" placeholder="Niche" value={form.niche ?? ''} onChange={(event) => setForm((current) => ({ ...current, niche: event.target.value }))} required />
          <input className="input" placeholder="City" value={form.city ?? ''} onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))} required />
          <input className="input" placeholder="Website" value={form.website ?? ''} onChange={(event) => setForm((current) => ({ ...current, website: event.target.value }))} />
          <input className="input" placeholder="Phone" value={form.phone ?? ''} onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} />
          <input className="input" placeholder="Email" value={form.email ?? ''} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} />
          <div className="form-actions">
            <button className="button" disabled={submitting} type="submit">{submitting ? 'Saving...' : 'Add business'}</button>
          </div>
        </form>
      </section>
      <section className="panel" style={{ marginTop: 20 }}>
        <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Business</th>
              <th>Niche</th>
              <th>City</th>
              <th>Opportunity</th>
              <th>Lead status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {businesses.map((business) => (
              <tr key={business.id}>
                <td>
                  <strong>{business.name}</strong>
                  <div className="subtle">{business.website || business.email || 'No website yet'}</div>
                </td>
                <td>{business.niche}</td>
                <td>{business.city}</td>
                <td>{business.latestScan?.opportunityScore ?? 'Not scanned'}</td>
                <td>{business.lead?.currentStatus ?? 'discovered'}</td>
                <td>
                  <button className="button secondary" disabled={busyId !== null} onClick={() => handleScan(business.id)} type="button">
                    {busyId === business.id ? 'Scanning...' : 'Run scan'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </section>
    </main>
  );
}
