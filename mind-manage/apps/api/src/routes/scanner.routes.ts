import { Router } from 'express';
import { latestScan, runScanner } from '../controllers/scanner.controller.js';

export const scannerRouter = Router();

scannerRouter.post('/run/:businessId', runScanner);
scannerRouter.get('/:businessId/latest', latestScan);
