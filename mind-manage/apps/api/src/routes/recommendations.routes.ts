import { Router } from 'express';
import { generateRecommendation, latestRecommendation } from '../controllers/recommendations.controller.js';

export const recommendationsRouter = Router();

recommendationsRouter.post('/generate/:businessId', generateRecommendation);
recommendationsRouter.get('/latest/:businessId', latestRecommendation);
