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

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type Bootstrap = {
  user: { id: string; username: string };
  vault_config_status: "configured" | "unconfigured";
  effective_materials_path: string;
  source: "user_override" | "global_default";
};

export async function authRegister(params: {
  baseUrl: string;
  username: string;
  password: string;
}): Promise<AuthTokens> {
  const res = await fetch(`${params.baseUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: params.username,
      password: params.password,
    }),
  });
  return parseJson<AuthTokens>(res);
}

export async function authLogin(params: {
  baseUrl: string;
  username: string;
  password: string;
}): Promise<AuthTokens> {
  const res = await fetch(`${params.baseUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: params.username,
      password: params.password,
    }),
  });
  return parseJson<AuthTokens>(res);
}

export async function authRefresh(params: {
  baseUrl: string;
  refreshToken: string;
}): Promise<AuthTokens> {
  const res = await fetch(`${params.baseUrl}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: params.refreshToken }),
  });
  return parseJson<AuthTokens>(res);
}

export async function authResetPassword(params: {
  baseUrl: string;
  username: string;
  newPassword: string;
}): Promise<void> {
  const res = await fetch(`${params.baseUrl}/api/v1/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: params.username,
      new_password: params.newPassword,
    }),
  });
  await parseJson<{ ok: boolean }>(res);
}

export async function authLogout(params: {
  baseUrl: string;
  accessToken: string;
}): Promise<void> {
  const res = await fetch(`${params.baseUrl}/api/v1/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${params.accessToken}` },
  });
  await parseJson<{ ok: boolean }>(res);
}

export async function fetchBootstrap(params: {
  baseUrl: string;
  accessToken: string;
}): Promise<Bootstrap> {
  const res = await fetch(`${params.baseUrl}/api/v1/me/bootstrap`, {
    headers: { Authorization: `Bearer ${params.accessToken}` },
  });
  return parseJson<Bootstrap>(res);
}

export async function putMaterialsPath(params: {
  baseUrl: string;
  accessToken: string;
  mode: "custom" | "use_default";
  customPath?: string;
  confirmEffectivePath: string;
}): Promise<{ effective_materials_path: string; vault_config_status: string }> {
  const res = await fetch(`${params.baseUrl}/api/v1/me/materials-path`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${params.accessToken}`,
    },
    body: JSON.stringify({
      mode: params.mode,
      custom_path: params.customPath,
      confirm_effective_path: params.confirmEffectivePath,
    }),
  });
  return parseJson<{ effective_materials_path: string; vault_config_status: string }>(
    res,
  );
}

