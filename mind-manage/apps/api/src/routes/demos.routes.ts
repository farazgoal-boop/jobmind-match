import { Router } from 'express';
import { generateDemo, getDemo, latestDemo } from '../controllers/demos.controller.js';

export const demosRouter = Router();

demosRouter.post('/generate/:businessId', generateDemo);
demosRouter.get('/latest/:businessId', latestDemo);
demosRouter.get('/:demoId', getDemo);
