import { Router } from 'express';
import { listLeads, updateLeadStatus } from '../controllers/leads.controller.js';

export const leadsRouter = Router();

leadsRouter.get('/', listLeads);
leadsRouter.patch('/:id/status', updateLeadStatus);
