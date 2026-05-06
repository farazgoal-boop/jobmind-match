type DemoInput = {
  businessName: string;
  niche: string;
  city: string;
  recommendationTitle: string;
  modules: string[];
};

export function buildDemo(input: DemoInput) {
  return {
    templateName: `${input.niche} instant demo`,
    headline: `${input.businessName}: a ${input.niche.toLowerCase()} growth workflow for ${input.city}`,
    demoUrl: `/demo/${input.businessName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
    content: {
      hero: `Show ${input.businessName} how ${input.recommendationTitle.toLowerCase()} can convert more leads.`,
      modules: input.modules,
      sections: [
        'Lead capture redesign',
        'Booking or callback automation',
        'Pipeline visibility for the sales team'
      ]
    }
  };
}