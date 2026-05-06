import type { Request, Response } from 'express';
import { getRouteParam } from '../lib/http.js';
import { prisma } from '../lib/prisma.js';
import { buildRecommendation } from '../services/ai/recommendation-engine.js';

export async function generateRecommendation(request: Request, response: Response) {
  const businessId = getRouteParam(request.params.businessId);
  const business = await prisma.business.findUnique({ where: { id: businessId } });
  const latestScan = await prisma.websiteScan.findFirst({
    where: { businessId },
    orderBy: { createdAt: 'desc' },
    include: { issues: true }
  });

  if (!business || !latestScan) {
    response.status(404).json({ ok: false, message: 'Business or scan not found.' });
    return;
  }

  const generated = buildRecommendation({
    businessName: business.name,
    niche: business.niche,
    city: business.city,
    opportunityScore: latestScan.opportunityScore,
    issues: latestScan.issues
  });

  const recommendation = await prisma.solutionRecommendation.create({
    data: {
      businessId: business.id,
      title: generated.title,
      summary: generated.summary,
      recommendedModules: generated.recommendedModules,
      pricingHint: generated.pricingHint,
      aiReasoning: generated.aiReasoning
    }
  });

  response.status(201).json({ ok: true, businessId, recommendation });
}

export async function latestRecommendation(request: Request, response: Response) {
  const businessId = getRouteParam(request.params.businessId);
  const recommendation = await prisma.solutionRecommendation.findFirst({
    where: { businessId },
    orderBy: { createdAt: 'desc' }
  });

  if (!recommendation) {
    response.status(404).json({ ok: false, message: 'No recommendation found for this business.' });
    return;
  }

  response.json(recommendation);
}
