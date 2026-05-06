import { Router } from 'express';
import { getDashboardSummary } from '../controllers/dashboard.controller.js';

export const dashboardRouter = Router();

dashboardRouter.get('/summary', getDashboardSummary);