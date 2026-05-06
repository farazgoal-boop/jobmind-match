import type { Request, Response } from 'express';
import { getRouteParam } from '../lib/http.js';
import { prisma } from '../lib/prisma.js';
import { buildDemo } from '../services/demos/demo-generator.js';

export async function generateDemo(request: Request, response: Response) {
  const businessId = getRouteParam(request.params.businessId);
  const business = await prisma.business.findUnique({ where: { id: businessId } });
  const recommendation = await prisma.solutionRecommendation.findFirst({
    where: { businessId },
    orderBy: { createdAt: 'desc' }
  });

  if (!business || !recommendation) {
    response.status(404).json({ ok: false, message: 'Business or recommendation not found.' });
    return;
  }

  const generated = buildDemo({
    businessName: business.name,
    niche: business.niche,
    city: business.city,
    recommendationTitle: recommendation.title,
    modules: Array.isArray(recommendation.recommendedModules) ? recommendation.recommendedModules.map(String) : []
  });

  const demo = await prisma.demo.create({
    data: {
      businessId: business.id,
      templateName: generated.templateName,
      demoUrl: generated.demoUrl,
      headline: generated.headline,
      content: generated.content
    }
  });

  response.status(201).json({ ok: true, businessId, demo });
}

export async function getDemo(request: Request, response: Response) {
  const demoId = getRouteParam(request.params.demoId);
  const demo = await prisma.demo.findUnique({ where: { id: demoId } });

  if (!demo) {
    response.status(404).json({ ok: false, message: 'Demo not found.' });
    return;
  }

  response.json(demo);
}

export async function latestDemo(request: Request, response: Response) {
  const businessId = getRouteParam(request.params.businessId);
  const demo = await prisma.demo.findFirst({
    where: { businessId },
    orderBy: { createdAt: 'desc' }
  });

  if (!demo) {
    response.status(404).json({ ok: false, message: 'No demo found for this business.' });
    return;
  }

  response.json(demo);
}
