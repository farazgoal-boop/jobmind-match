type ScanIssueShape = {
  issueType: string;
  description: string;
  revenueLossNote?: string | null;
  recommendationKey?: string | null;
};

type RecommendationInput = {
  businessName: string;
  niche: string;
  city: string;
  opportunityScore: number;
  issues: ScanIssueShape[];
};

export function buildRecommendation(input: RecommendationInput) {
  const recommendedModules = Array.from(
    new Set(input.issues.map((issue) => issue.recommendationKey).filter(Boolean))
  ) as string[];

  const summary = `Build a ${input.niche.toLowerCase()} conversion system for ${input.businessName} in ${input.city}, focused on ${input.issues
    .slice(0, 2)
    .map((issue) => issue.issueType.replaceAll('_', ' '))
    .join(' and ')}.`;

  const pricingHint =
    input.opportunityScore >= 80
      ? '$2,500 setup + $350/month optimization'
      : '$1,500 setup + $200/month support';

  const aiReasoning = input.issues
    .map((issue) => `${issue.description} ${issue.revenueLossNote ?? ''}`.trim())
    .join(' ');

  return {
    title: `${input.niche} Growth Stack`,
    summary,
    recommendedModules: recommendedModules.length > 0 ? recommendedModules : ['lead-capture', 'crm-sync'],
    pricingHint,
    aiReasoning
  };
}