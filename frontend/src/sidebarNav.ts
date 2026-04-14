/** 侧栏导航项（占位，后续接路由或面板） */

export type SidebarNavId = "home" | "settings";

export const SIDEBAR_NAV: {
  id: SidebarNavId;
  label: string;
}[] = [
  { id: "home", label: "主页" },
  { id: "settings", label: "设置" },
];
