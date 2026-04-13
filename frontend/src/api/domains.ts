import type { Domain, DomainVariant } from "../domains";
import { ApiHttpError } from "./chat";

type ErrorBody = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
};

export type DomainApiItem = {
  id: string;
  name: string;
  description: string;
  emoji?: string;
  variant?: string;
  enabled?: boolean;
  is_archived?: boolean;
  archived_at?: string | null;
};

export type DomainsApiResponse = {
  domains: DomainApiItem[];
  default_domain_id: string;
};

export type DomainCreateRequest = {
  name: string;
  description?: string;
  emoji?: string;
  variant?: DomainVariant;
};

export type DomainUpdateRequest = {
  name?: string;
  description?: string;
  emoji?: string;
  variant?: DomainVariant;
  enabled?: boolean;
  status?: "active" | "archived";
};

export type DomainCreateApiResponse = {
  domain: DomainApiItem;
};

export type DomainUpdateApiResponse = {
  domain: DomainApiItem;
};

export type DomainDeleteApiResponse = {
  ok: boolean;
};

const DOMAIN_VARIANTS: DomainVariant[] = [
  "coral",
  "indigo",
  "mint",
  "amber",
  "rose",
];

async function parseJson<T>(res: Response): Promise<T> {
  const data = (await res.json().catch(() => ({}))) as T | ErrorBody;
  if (!res.ok) {
    const err = data as ErrorBody;
    throw new ApiHttpError(
      res.status,
      err.error?.code ?? "http_error",
      err.error?.message ?? res.statusText,
      err.error?.details,
    );
  }
  return data as T;
}

function toDomainVariant(v?: string): DomainVariant {
  if (v && DOMAIN_VARIANTS.includes(v as DomainVariant)) {
    return v as DomainVariant;
  }
  return "coral";
}

function toLocalDomain(d: DomainApiItem): Domain {
  const isArchived = d.is_archived ?? d.enabled === false;
  return {
    id: d.id,
    name: d.name,
    description: d.description,
    emoji: d.emoji ?? "📁",
    variant: toDomainVariant(d.variant),
    status: isArchived ? "archived" : "active",
  };
}

export async function fetchDomains(baseUrl: string): Promise<DomainsApiResponse> {
  const r = await fetch(`${baseUrl}/api/v1/domains`);
  return parseJson<DomainsApiResponse>(r);
}

export async function createDomain(params: {
  baseUrl: string;
  accessToken: string;
  body: DomainCreateRequest;
}): Promise<DomainCreateApiResponse> {
  const r = await fetch(`${params.baseUrl}/api/v1/domains`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${params.accessToken}`,
    },
    body: JSON.stringify(params.body),
  });
  return parseJson<DomainCreateApiResponse>(r);
}

export async function updateDomain(params: {
  baseUrl: string;
  accessToken: string;
  domainId: string;
  body: DomainUpdateRequest;
}): Promise<DomainUpdateApiResponse> {
  const requestBody: DomainUpdateRequest = { ...params.body };
  // UI 侧统一使用 status 语义，后端若仅识别 enabled 则在此兼容映射。
  if (requestBody.status) {
    requestBody.enabled = requestBody.status === "active";
    delete requestBody.status;
  }
  const r = await fetch(`${params.baseUrl}/api/v1/domains/${params.domainId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${params.accessToken}`,
    },
    body: JSON.stringify(requestBody),
  });
  return parseJson<DomainUpdateApiResponse>(r);
}

export async function deleteDomain(params: {
  baseUrl: string;
  accessToken: string;
  domainId: string;
}): Promise<DomainDeleteApiResponse> {
  const r = await fetch(`${params.baseUrl}/api/v1/domains/${params.domainId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${params.accessToken}`,
    },
  });
  return parseJson<DomainDeleteApiResponse>(r);
}

export function apiDomainsToLocal(
  res: DomainsApiResponse,
): { domains: Domain[]; defaultDomainId: string } {
  const domains: Domain[] = res.domains.map(toLocalDomain);
  return { domains, defaultDomainId: res.default_domain_id };
}
