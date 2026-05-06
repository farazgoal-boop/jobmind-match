import type { Request, Response } from 'express';

export function register(_request: Request, response: Response) {
  response.status(201).json({ ok: true, message: 'Register endpoint scaffolded.' });
}

export function login(_request: Request, response: Response) {
  response.json({ ok: true, token: 'replace-with-jwt' });
}

export function me(_request: Request, response: Response) {
  response.json({ id: 'demo-user', name: 'Mind Manage Operator', role: 'admin' });
}
