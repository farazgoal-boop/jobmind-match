'use client';

import { useEffect, useMemo, useState } from 'react';
import { listLeads, updateLeadStatus, type LeadListItem, type LeadStatus } from '@/lib/api-client';

const statusOptions: LeadStatus[] = ['discovered', 'scanned', 'contacted', 'replied', 'interested', 'meeting_booked', 'proposal_sent', 'closed_won', 'closed_lost'];

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function loadLeads() {
    setLeads(await listLeads());
  }

  useEffect(() => {
    loadLeads().catch(() => setLeads([]));
  }, []);

  const pipeline = useMemo(
    () => [
      { status: 'contacted', count: leads.filter((lead) => lead.currentStatus === 'contacted').length },
      { status: 'interested', count: leads.filter((lead) => lead.currentStatus === 'interested').length },
      { status: 'meeting booked', count: leads.filter((lead) => lead.currentStatus === 'meeting_booked').length },
      { status: 'closed won', count: leads.filter((lead) => lead.currentStatus === 'closed_won').length }
    ],
    [leads]
  );

  async function handleStatusChange(leadId: string, status: LeadStatus) {
    setBusyId(leadId);

    try {
      await updateLeadStatus(leadId, status);
      await loadLeads();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Lead Dashboard</div>
        <h1>Pipeline and deal tracking</h1>
        <p>Monitor every business from discovery to close, with activities, follow-ups, proposals, and revenue outcomes.</p>
      </section>
      <section className="panel grid metrics" style={{ marginTop: 20 }}>
        {pipeline.map((item) => (
          <div className="metric" key={item.status}>
            <span className="subtle">{item.status}</span>
            <strong>{item.count}</strong>
          </div>
        ))}
      </section>
      <section className="panel" style={{ marginTop: 20 }}>
        <table className="table">
          <thead>
            <tr>
              <th>Business</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Interest</th>
              <th>Context</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id}>
                <td>
                  <strong>{lead.business.name}</strong>
                  <div className="subtle">{lead.business.niche} in {lead.business.city}</div>
                </td>
                <td>
                  <select className="input" disabled={busyId === lead.id} value={lead.currentStatus} onChange={(event) => handleStatusChange(lead.id, event.target.value as LeadStatus)}>
                    {statusOptions.map((status) => (
                      <option key={status} value={status}>{status.replaceAll('_', ' ')}</option>
                    ))}
                  </select>
                </td>
                <td>{lead.priority}</td>
                <td>{lead.interestScore}</td>
                <td>{lead.business.latestRecommendation?.pricingHint || lead.business.latestScan?.opportunityScore || 'No scan yet'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
