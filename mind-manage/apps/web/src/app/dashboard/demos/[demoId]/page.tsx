type DemoDetailPageProps = {
  params: Promise<{ demoId: string }>;
};

export default async function DemoDetailPage({ params }: DemoDetailPageProps) {
  const { demoId } = await params;

  return (
    <main className="shell">
      <section className="panel">
        <div className="kicker">Demo Preview</div>
        <h1>Demo #{demoId}</h1>
        <p>This route is reserved for generated previews that can be shared with the target business.</p>
      </section>
    </main>
  );
}
