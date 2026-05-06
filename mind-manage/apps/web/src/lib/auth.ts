export type SessionUser = {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'sales';
};

export async function getSessionUser(): Promise<SessionUser | null> {
  return null;
}
