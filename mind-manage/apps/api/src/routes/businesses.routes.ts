import { Router } from 'express';
import { discoverBusinesses, listBusinesses } from '../controllers/businesses.controller.js';

export const businessesRouter = Router();

businessesRouter.get('/', listBusinesses);
businessesRouter.post('/discover', discoverBusinesses);
