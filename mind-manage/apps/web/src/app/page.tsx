import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero">
        <div className="panel">
          <div className="kicker">Mind Manage</div>
          <h1>Business Problem Scanner + Instant Demo Generator</h1>
          <p>
            A sales operating system for discovering businesses, scanning websites,
            generating solution recommendations, building instant demos, and moving leads through outreach.
          </p>
          <div className="badge-row">
            <span className="badge">Next.js</span>
            <span className="badge">Express</span>
            <span className="badge">PostgreSQL</span>
            <span className="badge">OpenAI</span>
            <span className="badge">n8n</span>
            <span className="badge">Playwright</span>
          </div>
        </div>
        <div className="panel">
          <div className="kicker">Quick Start</div>
          <h2>Professional Sales Workflow</h2>
          <p>Start with discovery, then scan, recommend, generate demo, and contact the lead with context-aware outreach.</p>
          <div style={{ marginTop: 20 }}>
            <Link className="cta" href="/dashboard">Open dashboard shell</Link>
          </div>
        </div>
      </section>
    </main>
  );
}
