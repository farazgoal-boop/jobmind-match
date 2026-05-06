import cors from 'cors';
import express from 'express';
import { authRouter } from './routes/auth.routes.js';
import { businessesRouter } from './routes/businesses.routes.js';
import { scannerRouter } from './routes/scanner.routes.js';
import { recommendationsRouter } from './routes/recommendations.routes.js';
import { demosRouter } from './routes/demos.routes.js';
import { outreachRouter } from './routes/outreach.routes.js';
import { leadsRouter } from './routes/leads.routes.js';
import { dashboardRouter } from './routes/dashboard.routes.js';

export function createApp() {
  const app = express();

  app.use(cors());
  app.use(express.json({ limit: '2mb' }));

  app.get('/api/health', (_request, response) => {
    response.json({ ok: true });
  });

  app.use('/api/auth', authRouter);
  app.use('/api/businesses', businessesRouter);
  app.use('/api/scanner', scannerRouter);
  app.use('/api/recommendations', recommendationsRouter);
  app.use('/api/demos', demosRouter);
  app.use('/api/outreach', outreachRouter);
  app.use('/api/leads', leadsRouter);
  app.use('/api/dashboard', dashboardRouter);

  return app;
}
