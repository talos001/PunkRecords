export type ChatResponseBody = {
  message: {
    id: string;
    role: string;
    content: string;
    created_at: string;
  };
  job_ids: string[];
};

export async function postChat(params: {
  baseUrl: string;
  domainId: string;
  text: string;
  files: File[];
}): Promise<ChatResponseBody> {
  const fd = new FormData();
  fd.append("domain_id", params.domainId);
  fd.append("text", params.text);
  for (const f of params.files) {
    fd.append("files", f);
  }
  const r = await fetch(`${params.baseUrl}/api/v1/chat`, {
    method: "POST",
    body: fd,
  });
  const data = (await r.json().catch(() => ({}))) as
    | ChatResponseBody
    | { error?: { message?: string } };
  if (!r.ok) {
    const errBody = data as { error?: { message?: string } };
    const msg = errBody.error?.message ?? r.statusText;
    throw new Error(msg || "请求失败");
  }
  return data as ChatResponseBody;
}
