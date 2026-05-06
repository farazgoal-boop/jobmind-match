'use client';

import { FormEvent, useEffect, useState } from 'react';
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

  async function loadBusinesses() {
    setBusinesses(await listBusinesses());
  }

  useEffect(() => {
    loadBusinesses().catch(() => setBusinesses([]));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);

    try {
      await createBusiness(form);
      setForm({ name: '', niche: '', city: '', website: '', phone: '', email: '', source: 'manual' });
      await loadBusinesses();
    } finally {
      setSubmitting(false);
    }
  }

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
        <div className="kicker">Business Discovery</div>
        <h1>Search by niche and city</h1>
        <p>Use Google Maps and directory providers to discover businesses, enrich their contacts, and queue them for scanning.</p>
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
                  <button className="button secondary" disabled={busyId === business.id} onClick={() => handleScan(business.id)} type="button">
                    {busyId === business.id ? 'Scanning...' : 'Run scan'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
