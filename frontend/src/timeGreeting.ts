/**
 * 根据本地时间返回简短问候（用于主区标题前缀）。
 * 分段可按产品再微调。
 */
export function getTimeGreeting(date = new Date()): string {
  const h = date.getHours();
  if (h >= 0 && h < 5) return "凌晨好";
  if (h < 9) return "早上好";
  if (h < 12) return "上午好";
  if (h < 18) return "下午好";
  return "晚上好";
}
