import type { Domain, DomainVariant } from "../domains";

export type DomainsApiResponse = {
  domains: Array<{
    id: string;
    name: string;
    description: string;
    emoji?: string;
    variant?: string;
    enabled?: boolean;
  }>;
  default_domain_id: string;
};

export async function fetchDomains(
  baseUrl: string,
): Promise<DomainsApiResponse> {
  const r = await fetch(`${baseUrl}/api/v1/domains`);
  if (!r.ok) throw new Error(`domains: ${r.status}`);
  return r.json() as Promise<DomainsApiResponse>;
}

export function apiDomainsToLocal(
  res: DomainsApiResponse,
): { domains: Domain[]; defaultDomainId: string } {
  const domains: Domain[] = res.domains
    .filter((d) => d.enabled !== false)
    .map((d) => ({
      id: d.id,
      name: d.name,
      description: d.description,
      emoji: d.emoji ?? "📁",
      variant: (d.variant as DomainVariant) ?? "coral",
    }));
  return { domains, defaultDomainId: res.default_domain_id };
}
