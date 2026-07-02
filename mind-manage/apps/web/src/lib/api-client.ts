const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:4000/api';

export type DashboardSummary = {
  businessesDiscovered: number;
  highOpportunitySites: number;
  meetingsBooked: number;
  closedDeals: number;
  projectedValue: number;
};

export type ScanIssue = {
  id: string;
  issueType: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  revenueLossNote?: string | null;
  recommendationKey?: string | null;
};

export type LatestScan = {
  id: string;
  opportunityScore: number;
  leadCaptureScore: number;
  responseScore: number;
  issues: ScanIssue[];
};

export type Recommendation = {
  id: string;
  title: string;
  summary: string;
  pricingHint?: string | null;
  recommendedModules: string[];
};

export type Demo = {
  id: string;
  templateName: string;
  headline: string;
  demoUrl?: string | null;
};

export type Outreach = {
  id: string;
  channel: string;
  subject?: string | null;
  messageBody: string;
  status: string;
};

export type LeadStatus =
  | 'discovered'
  | 'scanned'
  | 'contacted'
  | 'replied'
  | 'interested'
  | 'meeting_booked'
  | 'proposal_sent'
  | 'closed_won'
  | 'closed_lost';

export type BusinessListItem = {
  id: string;
  name: string;
  niche: string;
  city: string;
  website?: string | null;
  phone?: string | null;
  email?: string | null;
  source?: string | null;
  latestScan?: LatestScan | null;
  latestRecommendation?: Recommendation | null;
  latestDemo?: Demo | null;
  latestOutreach?: Outreach | null;
  lead?: {
    id: string;
    currentStatus: LeadStatus;
    interestScore: number;
    priority: number;
  } | null;
};

export type LeadListItem = {
  id: string;
  businessId: string;
  currentStatus: LeadStatus;
  priority: number;
  interestScore: number;
  business: {
    id: string;
    name: string;
    niche: string;
    city: string;
    latestScan?: LatestScan | null;
    latestRecommendation?: Recommendation | null;
    latestOutreach?: Outreach | null;
  };
};

export type CreateBusinessPayload = {
  name: string;
  niche: string;
  city: string;
  website?: string;
  phone?: string;
  email?: string;
  address?: string;
  source?: string;
};

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {})
    },
    cache: 'no-store'
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.message === 'string') {
        message = body.message;
      }
    } catch {
      // response had no JSON body; keep the default message
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function getDashboardSummary() {
  return apiRequest<DashboardSummary>('/dashboard/summary');
}

export async function listBusinesses() {
  const result = await apiRequest<{ items: BusinessListItem[] }>('/businesses');
  return result.items;
}

export function createBusiness(payload: CreateBusinessPayload) {
  return apiRequest('/businesses/discover', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function runScan(businessId: string) {
  return apiRequest(`/scanner/run/${businessId}`, {
    method: 'POST'
  });
}

export function generateRecommendation(businessId: string) {
  return apiRequest(`/recommendations/generate/${businessId}`, {
    method: 'POST'
  });
}

export function generateDemo(businessId: string) {
  return apiRequest(`/demos/generate/${businessId}`, {
    method: 'POST'
  });
}

export function generateOutreach(businessId: string) {
  return apiRequest(`/outreach/generate/${businessId}`, {
    method: 'POST'
  });
}

export function quickGenerateOutreach(businessId: string) {
  return apiRequest(`/outreach/quick-generate/${businessId}`, {
    method: 'POST'
  });
}

export function sendOutreach(messageId: string) {
  return apiRequest(`/outreach/send/${messageId}`, {
    method: 'POST'
  });
}

export async function listLeads() {
  const result = await apiRequest<{ items: LeadListItem[] }>('/leads');
  return result.items;
}

export function updateLeadStatus(id: string, status: LeadStatus) {
  return apiRequest(`/leads/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status })
  });
}
