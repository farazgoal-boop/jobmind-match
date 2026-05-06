import type { Request, Response } from 'express';
import { getRouteParam } from '../lib/http.js';
import { prisma } from '../lib/prisma.js';
import { buildOutreachDraft } from '../services/outreach/outreach-generator.js';

export async function generateOutreach(request: Request, response: Response) {
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

  const generated = buildOutreachDraft({
    businessName: business.name,
    niche: business.niche,
    city: business.city,
    recommendationSummary: recommendation.summary
  });

  const draft = await prisma.outreachMessage.create({
    data: {
      businessId: business.id,
      channel: generated.channel,
      subject: generated.subject,
      messageBody: generated.messageBody,
      personalization: generated.personalization
    }
  });

  response.status(201).json({ ok: true, businessId, draft });
}

export async function sendOutreach(request: Request, response: Response) {
  const messageId = getRouteParam(request.params.messageId);
  const message = await prisma.outreachMessage.update({
    where: { id: messageId },
    data: { status: 'sent', sentAt: new Date() }
  });

  response.json({ ok: true, messageId, status: message.status });
}

export async function latestOutreach(request: Request, response: Response) {
  const businessId = getRouteParam(request.params.businessId);
  const draft = await prisma.outreachMessage.findFirst({
    where: { businessId },
    orderBy: { createdAt: 'desc' }
  });

  if (!draft) {
    response.status(404).json({ ok: false, message: 'No outreach draft found for this business.' });
    return;
  }

  response.json(draft);
}
