import type { Request, Response } from 'express';
import { LeadStatus } from '@prisma/client';
import { getRouteParam } from '../lib/http.js';
import { prisma } from '../lib/prisma.js';
import { buildMockScan } from '../services/scanner/mock-scan.js';

export async function runScanner(request: Request, response: Response) {
  const businessId = getRouteParam(request.params.businessId);
  const business = await prisma.business.findUnique({ where: { id: businessId } });

  if (!business) {
    response.status(404).json({ ok: false, message: 'Business not found.' });
    return;
  }

  const generated = buildMockScan(business);
  const scan = await prisma.websiteScan.create({
    data: {
      businessId: business.id,
      scannerVersion: generated.scannerVersion,
      homepageUrl: generated.homepageUrl,
      loadTimeMs: generated.loadTimeMs,
      contactFormFound: generated.contactFormFound,
      whatsappFound: generated.whatsappFound,
      bookingFound: generated.bookingFound,
      crmHintFound: generated.crmHintFound,
      chatbotFound: generated.chatbotFound,
      leadCaptureScore: generated.leadCaptureScore,
      responseScore: generated.responseScore,
      opportunityScore: generated.opportunityScore,
      issues: {
        create: generated.issues
      }
    },
    include: {
      issues: true
    }
  });

  await prisma.leadPipeline.updateMany({
    where: { businessId: business.id },
    data: {
      currentStatus: LeadStatus.scanned,
      interestScore: generated.opportunityScore,
      priority: generated.opportunityScore >= 80 ? 5 : 3
    }
  });

  response.status(201).json({
    ok: true,
    businessId,
    status: 'scan_completed',
    scan
  });
}

export async function latestScan(request: Request, response: Response) {
  const businessId = getRouteParam(request.params.businessId);
  const scan = await prisma.websiteScan.findFirst({
    where: { businessId },
    orderBy: { createdAt: 'desc' },
    include: { issues: true, business: true }
  });

  if (!scan) {
    response.status(404).json({ ok: false, message: 'No scan found for this business.' });
    return;
  }

  response.json(scan);
}
