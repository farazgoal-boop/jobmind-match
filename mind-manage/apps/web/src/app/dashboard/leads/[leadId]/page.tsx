type LeadDetailPageProps = {
  params: Promise<{ leadId: string }>;
};

export default async function LeadDetailPage({ params }: LeadDetailPageProps) {
  const { leadId } = await params;

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Lead Detail</div>
        <h1>Lead #{leadId}</h1>
        <p>Review scan findings, recommendation summary, generated demo, and outreach history in one place.</p>
      </section>
    </main>
  );
}
