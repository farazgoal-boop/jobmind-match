import Link from 'next/link';

export default function LoginPage() {
  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Authentication</div>
        <h1>Login</h1>
        <p>Use NextAuth or JWT-based auth here. This page is scaffolded for protected dashboard access.</p>
        <div style={{ marginTop: 20 }}>
          <Link className="cta" href="/dashboard">Continue to dashboard</Link>
        </div>
      </section>
    </main>
  );
}
