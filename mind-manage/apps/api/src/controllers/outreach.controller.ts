import type { Request, Response } from 'express';
import { LeadStatus } from '@prisma/client';
import { getRouteParam } from '../lib/http.js';
import { prisma } from '../lib/prisma.js';
import { buildRecommendation } from '../services/ai/recommendation-engine.js';
import { buildMockScan } from '../services/scanner/mock-scan.js';
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

  await prisma.leadPipeline.updateMany({
    where: { businessId: message.businessId, currentStatus: LeadStatus.scanned },
    data: { currentStatus: LeadStatus.contacted }
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

export async function quickGenerateOutreach(request: Request, response: Response) {
  const businessId = getRouteParam(request.params.businessId);
  const business = await prisma.business.findUnique({ where: { id: businessId } });

  if (!business) {
    response.status(404).json({ ok: false, message: 'Business not found.' });
    return;
  }

  const generatedScan = buildMockScan(business);
  const scan = await prisma.websiteScan.create({
    data: {
      businessId: business.id,
      scannerVersion: generatedScan.scannerVersion,
      homepageUrl: generatedScan.homepageUrl,
      loadTimeMs: generatedScan.loadTimeMs,
      contactFormFound: generatedScan.contactFormFound,
      whatsappFound: generatedScan.whatsappFound,
      bookingFound: generatedScan.bookingFound,
      crmHintFound: generatedScan.crmHintFound,
      chatbotFound: generatedScan.chatbotFound,
      leadCaptureScore: generatedScan.leadCaptureScore,
      responseScore: generatedScan.responseScore,
      opportunityScore: generatedScan.opportunityScore,
      issues: { create: generatedScan.issues }
    },
    include: { issues: true }
  });

  await prisma.leadPipeline.updateMany({
    where: {
      businessId: business.id,
      currentStatus: { in: [LeadStatus.discovered, LeadStatus.scanned] }
    },
    data: {
      currentStatus: LeadStatus.scanned,
      interestScore: generatedScan.opportunityScore,
      priority: generatedScan.opportunityScore >= 80 ? 5 : 3
    }
  });

  const generatedRec = buildRecommendation({
    businessName: business.name,
    niche: business.niche,
    city: business.city,
    opportunityScore: scan.opportunityScore,
    issues: scan.issues
  });

  const recommendation = await prisma.solutionRecommendation.create({
    data: {
      businessId: business.id,
      title: generatedRec.title,
      summary: generatedRec.summary,
      recommendedModules: generatedRec.recommendedModules,
      pricingHint: generatedRec.pricingHint,
      aiReasoning: generatedRec.aiReasoning
    }
  });

  const generatedOutreach = buildOutreachDraft({
    businessName: business.name,
    niche: business.niche,
    city: business.city,
    recommendationSummary: recommendation.summary
  });

  const draft = await prisma.outreachMessage.create({
    data: {
      businessId: business.id,
      channel: generatedOutreach.channel,
      subject: generatedOutreach.subject,
      messageBody: generatedOutreach.messageBody,
      personalization: generatedOutreach.personalization
    }
  });

  response.status(201).json({ ok: true, businessId, scan, recommendation, draft });
}
