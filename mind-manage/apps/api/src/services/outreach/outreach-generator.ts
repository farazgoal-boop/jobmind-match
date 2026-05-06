type OutreachInput = {
  businessName: string;
  niche: string;
  city: string;
  recommendationSummary: string;
};

export function buildOutreachDraft(input: OutreachInput) {
  return {
    channel: 'email',
    subject: `${input.businessName}: quick idea to improve ${input.niche.toLowerCase()} lead conversion`,
    messageBody: `Hi ${input.businessName} team,\n\nI reviewed your current digital presence in ${input.city} and found a few places where qualified leads may be dropping off. ${input.recommendationSummary}\n\nIf useful, I can share a short custom demo showing what this would look like in practice.\n\nRegards,\nMind Manage`,
    personalization: {
      city: input.city,
      niche: input.niche
    }
  };
}