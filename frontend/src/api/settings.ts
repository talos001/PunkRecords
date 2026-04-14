import { ApiHttpError } from "./chat";

type ErrorBody = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
};

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

export type LlmSettings = {
  llm_provider: string;
  llm_model: string;
  llm_base_url: string;
  masked_llm_api_key: string;
};

export type DomainSettings = {
  materials_vault_path: string;
  domain_material_paths: Record<string, string>;
};

export type PatchLlmSettingsPayload = Partial<{
  llm_provider: string;
  llm_model: string;
  llm_base_url: string;
  llm_api_key: string;
}>;

export type PatchDomainSettingsPayload = Partial<{
  materials_vault_path: string;
  domain_material_paths: Record<string, string>;
}>;

export async function fetchLlmSettings(params: {
  baseUrl: string;
  accessToken: string;
}): Promise<LlmSettings> {
  const res = await fetch(`${params.baseUrl}/api/v1/settings/llm`, {
    headers: { Authorization: `Bearer ${params.accessToken}` },
  });
  return parseJson<LlmSettings>(res);
}

export async function patchLlmSettings(params: {
  baseUrl: string;
  accessToken: string;
  body: PatchLlmSettingsPayload;
}): Promise<LlmSettings> {
  const res = await fetch(`${params.baseUrl}/api/v1/settings/llm`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${params.accessToken}`,
    },
    body: JSON.stringify(params.body),
  });
  return parseJson<LlmSettings>(res);
}

export async function fetchDomainSettings(params: {
  baseUrl: string;
  accessToken: string;
}): Promise<DomainSettings> {
  const res = await fetch(`${params.baseUrl}/api/v1/settings/domains`, {
    headers: { Authorization: `Bearer ${params.accessToken}` },
  });
  return parseJson<DomainSettings>(res);
}

export async function patchDomainSettings(params: {
  baseUrl: string;
  accessToken: string;
  body: PatchDomainSettingsPayload;
}): Promise<DomainSettings> {
  const res = await fetch(`${params.baseUrl}/api/v1/settings/domains`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${params.accessToken}`,
    },
    body: JSON.stringify(params.body),
  });
  return parseJson<DomainSettings>(res);
}
