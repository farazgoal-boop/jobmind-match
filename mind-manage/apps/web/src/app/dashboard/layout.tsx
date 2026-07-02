import { SiteNav } from '@/components/dashboard/site-nav';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <SiteNav />
      {children}
    </>
  );
}
