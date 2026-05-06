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

export type LeadSummary = {
  id: string;
  businessId: string;
  status: LeadStatus;
  priority: number;
  interestScore: number;
};
