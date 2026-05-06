import type { Request, Response } from 'express';
import { LeadStatus } from '@prisma/client';
import { prisma } from '../lib/prisma.js';

function extractProjectedValue(pricingHint: string | null) {
  const match = pricingHint?.match(/(\d[\d,]*)(?:\.\d+)?/);

  if (!match) {
    return 0;
  }

  return Number(match[1].replace(/,/g, '')) || 0;
}

export async function getDashboardSummary(_request: Request, response: Response) {
  const [businessesDiscovered, highOpportunitySites, meetingsBooked, closedDeals, latestRecommendations] =
    await Promise.all([
      prisma.business.count(),
      prisma.websiteScan.count({ where: { opportunityScore: { gte: 70 } } }),
      prisma.leadPipeline.count({ where: { currentStatus: LeadStatus.meeting_booked } }),
      prisma.leadPipeline.count({ where: { currentStatus: LeadStatus.closed_won } }),
      prisma.solutionRecommendation.findMany({ select: { pricingHint: true }, take: 50, orderBy: { createdAt: 'desc' } })
    ]);

  const projectedValue = latestRecommendations.reduce((total: number, item: (typeof latestRecommendations)[number]) => {
    return total + extractProjectedValue(item.pricingHint);
  }, 0);

  response.json({
    businessesDiscovered,
    highOpportunitySites,
    meetingsBooked,
    closedDeals,
    projectedValue
  });
}