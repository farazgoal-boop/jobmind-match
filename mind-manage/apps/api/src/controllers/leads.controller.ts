import type { Request, Response } from 'express';
import { LeadStatus } from '@prisma/client';
import { z } from 'zod';
import { getRouteParam } from '../lib/http.js';
import { prisma } from '../lib/prisma.js';

const updateLeadStatusSchema = z.object({
  status: z.nativeEnum(LeadStatus)
});

export async function listLeads(_request: Request, response: Response) {
  const items = await prisma.leadPipeline.findMany({
    orderBy: [{ priority: 'desc' }, { updatedAt: 'desc' }],
    include: {
      business: {
        include: {
          scans: { take: 1, orderBy: { createdAt: 'desc' }, include: { issues: true } },
          recommendations: { take: 1, orderBy: { createdAt: 'desc' } },
          outreachMessages: { take: 1, orderBy: { createdAt: 'desc' } }
        }
      }
    }
  });

  response.json({
    items: items.map((item: (typeof items)[number]) => ({
      id: item.id,
      businessId: item.businessId,
      currentStatus: item.currentStatus,
      priority: item.priority,
      interestScore: item.interestScore,
      nextFollowUpAt: item.nextFollowUpAt,
      business: {
        id: item.business.id,
        name: item.business.name,
        niche: item.business.niche,
        city: item.business.city,
        latestScan: item.business.scans[0] ?? null,
        latestRecommendation: item.business.recommendations[0] ?? null,
        latestOutreach: item.business.outreachMessages[0] ?? null
      }
    })),
    total: items.length
  });
}

export async function updateLeadStatus(request: Request, response: Response) {
  const payload = updateLeadStatusSchema.parse(request.body);
  const leadId = getRouteParam(request.params.id);
  const lead = await prisma.leadPipeline.update({
    where: { id: leadId },
    data: {
      currentStatus: payload.status,
      lastContactedAt: payload.status === LeadStatus.contacted ? new Date() : undefined,
      nextFollowUpAt:
        payload.status === LeadStatus.contacted || payload.status === LeadStatus.replied ? new Date(Date.now() + 3 * 24 * 60 * 60 * 1000) : undefined
    }
  });

  response.json({ ok: true, leadId: lead.id, status: lead.currentStatus });
}
