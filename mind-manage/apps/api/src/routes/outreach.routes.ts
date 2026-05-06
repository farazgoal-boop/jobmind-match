import { Router } from 'express';
import { generateOutreach, latestOutreach, sendOutreach } from '../controllers/outreach.controller.js';

export const outreachRouter = Router();

outreachRouter.post('/generate/:businessId', generateOutreach);
outreachRouter.get('/latest/:businessId', latestOutreach);
outreachRouter.post('/send/:messageId', sendOutreach);
