import { prisma } from './prisma.js';

const SYSTEM_USER_EMAIL = 'ops@mindmanage.local';

export async function getSystemUserId() {
  const user = await prisma.user.upsert({
    where: { email: SYSTEM_USER_EMAIL },
    update: {
      name: 'Mind Manage Ops',
      role: 'admin'
    },
    create: {
      name: 'Mind Manage Ops',
      email: SYSTEM_USER_EMAIL,
      passwordHash: 'local-dev-only',
      role: 'admin'
    }
  });

  return user.id;
}