'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { dashboardModules } from '@/lib/constants';

export function SiteNav() {
  const pathname = usePathname();

  return (
    <nav className="site-nav">
      <div className="site-nav-inner">
        <Link href="/dashboard" className="site-nav-brand">
          Mind Manage
        </Link>
        <div className="site-nav-links">
          {dashboardModules.map((item) => (
            <Link key={item.href} href={item.href} className={pathname === item.href ? 'active' : ''}>
              {item.title}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
