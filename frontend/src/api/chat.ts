export type ChatResponseBody = {
  message: {
    id: string;
    role: string;
    content: string;
    created_at: string;
  };
  job_ids: string[];
};

export type StreamEvent =
  | { type: "start"; id: string; created_at: string }
  | { type: "delta"; text: string }
  | { type: "done"; id: string; job_ids: string[] }
  | { type: "error"; message: string };

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

/** SSE（text/event-stream）：流式增量 + start/done/error 事件 */
export async function postChatStream(params: {
  baseUrl: string;
  domainId: string;
  text: string;
  files: File[];
  onEvent: (ev: StreamEvent) => void;
  signal?: AbortSignal;
}): Promise<void> {
  const fd = new FormData();
  fd.append("domain_id", params.domainId);
  fd.append("text", params.text);
  for (const f of params.files) {
    fd.append("files", f);
  }
  const r = await fetch(`${params.baseUrl}/api/v1/chat/stream`, {
    method: "POST",
    body: fd,
    signal: params.signal,
  });
  if (!r.ok) {
    const data = (await r.json().catch(() => ({}))) as {
      error?: { message?: string };
    };
    const msg = data.error?.message ?? r.statusText;
    throw new Error(msg || "请求失败");
  }
  if (!r.body) {
    throw new Error("无响应体");
  }
  await parseSSEStream(r.body, params.onEvent);
}

async function parseSSEStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (ev: StreamEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const line = block.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.startsWith("data: ")
        ? line.slice(6)
        : line.slice(5).trim();
      try {
        const obj = JSON.parse(payload) as StreamEvent;
        if (
          obj.type === "start" ||
          obj.type === "delta" ||
          obj.type === "done" ||
          obj.type === "error"
        ) {
          onEvent(obj);
        }
      } catch {
        /* 忽略损坏行 */
      }
    }
  }
}
