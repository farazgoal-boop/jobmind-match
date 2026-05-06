import type { Request, Response } from 'express';
import { z } from 'zod';
import { prisma } from '../lib/prisma.js';
import { getSystemUserId } from '../lib/system-user.js';

const discoverBusinessSchema = z.object({
  name: z.string().min(2),
  niche: z.string().min(2),
  city: z.string().min(2),
  website: z.string().trim().optional().or(z.literal('')),
  phone: z.string().trim().optional().or(z.literal('')),
  email: z.string().trim().optional().or(z.literal('')),
  address: z.string().trim().optional().or(z.literal('')),
  source: z.string().trim().optional().or(z.literal('manual'))
});

export async function listBusinesses(request: Request, response: Response) {
  const search = request.query.search?.toString().trim();
  const niche = request.query.niche?.toString().trim();
  const city = request.query.city?.toString().trim();

  const items = await prisma.business.findMany({
    where: {
      AND: [
        search
          ? {
              OR: [
                { name: { contains: search, mode: 'insensitive' } },
                { niche: { contains: search, mode: 'insensitive' } },
                { city: { contains: search, mode: 'insensitive' } }
              ]
            }
          : {},
        niche ? { niche: { contains: niche, mode: 'insensitive' } } : {},
        city ? { city: { contains: city, mode: 'insensitive' } } : {}
      ]
    },
    orderBy: { createdAt: 'desc' },
    include: {
      scans: { take: 1, orderBy: { createdAt: 'desc' }, include: { issues: true } },
      recommendations: { take: 1, orderBy: { createdAt: 'desc' } },
      demos: { take: 1, orderBy: { createdAt: 'desc' } },
      outreachMessages: { take: 1, orderBy: { createdAt: 'desc' } },
      leadPipeline: true
    }
  });

  response.json({
    items: items.map((item: (typeof items)[number]) => ({
      id: item.id,
      name: item.name,
      niche: item.niche,
      city: item.city,
      website: item.website,
      phone: item.phone,
      email: item.email,
      source: item.source,
      discoveredAt: item.discoveredAt,
      latestScan: item.scans[0] ?? null,
      latestRecommendation: item.recommendations[0] ?? null,
      latestDemo: item.demos[0] ?? null,
      latestOutreach: item.outreachMessages[0] ?? null,
      lead: item.leadPipeline
    })),
    total: items.length
  });
}

export async function discoverBusinesses(request: Request, response: Response) {
  const payload = discoverBusinessSchema.parse(request.body);
  const ownerUserId = await getSystemUserId();

  const business = await prisma.business.create({
    data: {
      ownerUserId,
      name: payload.name,
      niche: payload.niche,
      city: payload.city,
      website: payload.website || null,
      phone: payload.phone || null,
      email: payload.email || null,
      address: payload.address || null,
      source: payload.source || 'manual'
    }
  });

  const lead = await prisma.leadPipeline.create({
    data: {
      ownerUserId,
      businessId: business.id,
      interestScore: 35,
      priority: 1
    }
  });

  response.status(201).json({
    ok: true,
    business,
    lead
  });
}
