type BusinessShape = {
  name: string;
  niche: string;
  city: string;
  website?: string | null;
  email?: string | null;
  phone?: string | null;
};

export type GeneratedIssue = {
  issueType: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  revenueLossNote: string;
  recommendationKey: string;
};

export type GeneratedScan = {
  scannerVersion: string;
  homepageUrl?: string;
  loadTimeMs: number;
  contactFormFound: boolean;
  whatsappFound: boolean;
  bookingFound: boolean;
  crmHintFound: boolean;
  chatbotFound: boolean;
  leadCaptureScore: number;
  responseScore: number;
  opportunityScore: number;
  issues: GeneratedIssue[];
};

function titleCase(value: string) {
  return value
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(' ');
}

export function buildMockScan(business: BusinessShape): GeneratedScan {
  const niche = business.niche.toLowerCase();
  const issueSet: GeneratedIssue[] = [];

  const hasWebsite = Boolean(business.website);
  const hasDirectContact = Boolean(business.phone || business.email);
  const bookingRequired = /(clinic|doctor|salon|spa|dental|consult)/.test(niche);
  const crmLikely = /(real estate|property|agency|elevator|b2b|services)/.test(niche);
  const chatbotLikely = /(education|school|clinic|real estate|agency)/.test(niche);

  if (!hasWebsite) {
    issueSet.push({
      issueType: 'missing_website',
      severity: 'high',
      description: `${titleCase(business.name)} does not have a visible landing page for inbound traffic.`,
      revenueLossNote: 'Prospects have no focused conversion path, so paid traffic and referrals leak.',
      recommendationKey: 'landing-page'
    });
  }

  if (!hasDirectContact) {
    issueSet.push({
      issueType: 'weak_contact_capture',
      severity: 'high',
      description: 'No obvious contact channel is captured for fast follow-up.',
      revenueLossNote: 'Hot leads leave when they cannot contact the business instantly.',
      recommendationKey: 'lead-capture'
    });
  }

  if (bookingRequired) {
    issueSet.push({
      issueType: 'no_booking_flow',
      severity: 'high',
      description: 'The business needs appointment scheduling, but no self-serve booking flow is present.',
      revenueLossNote: 'Manual scheduling slows conversion and increases drop-off.',
      recommendationKey: 'booking-automation'
    });
  }

  if (crmLikely) {
    issueSet.push({
      issueType: 'crm_gap',
      severity: 'medium',
      description: 'Lead tracking and assignment look manual rather than CRM-driven.',
      revenueLossNote: 'Untracked leads reduce follow-up quality and sales velocity.',
      recommendationKey: 'crm-sync'
    });
  }

  if (chatbotLikely) {
    issueSet.push({
      issueType: 'after_hours_gap',
      severity: 'medium',
      description: 'No conversational layer is present to qualify after-hours or mobile-first visitors.',
      revenueLossNote: 'Inbound interest outside working hours goes cold before the team replies.',
      recommendationKey: 'chatbot'
    });
  }

  const contactFormFound = hasWebsite && hasDirectContact;
  const whatsappFound = Boolean(business.phone);
  const bookingFound = false;
  const crmHintFound = false;
  const chatbotFound = false;
  const leadCaptureScore = Math.max(15, 100 - issueSet.length * 17 - (hasWebsite ? 0 : 12));
  const responseScore = Math.max(20, 100 - issueSet.length * 14 - (hasDirectContact ? 0 : 18));
  const opportunityScore = Math.min(94, 45 + issueSet.length * 11 + (bookingRequired ? 8 : 0) + (crmLikely ? 6 : 0));

  return {
    scannerVersion: 'local-v1',
    homepageUrl: business.website ?? undefined,
    loadTimeMs: hasWebsite ? 1800 + issueSet.length * 220 : 0,
    contactFormFound,
    whatsappFound,
    bookingFound,
    crmHintFound,
    chatbotFound,
    leadCaptureScore,
    responseScore,
    opportunityScore,
    issues: issueSet
  };
}