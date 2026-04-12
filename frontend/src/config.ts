/** API 根 URL，不含尾斜杠。开发时可在 `.env.local` 中设置 `VITE_API_BASE_URL`。 */
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL as string | undefined
)?.replace(/\/$/, "") ?? "";

export const useLiveApi = Boolean(API_BASE_URL);
