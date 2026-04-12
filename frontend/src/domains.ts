/** 用户可见「知识区域」；后端用 id 映射 Vault（见 docs/ui_design.md） */

export type DomainVariant =
  | "coral"
  | "indigo"
  | "mint"
  | "amber"
  | "rose";

export type Domain = {
  id: string;
  name: string;
  description: string;
  /** 卡片装饰用，避免下拉列表式的单调感 */
  emoji: string;
  variant: DomainVariant;
};

export const DOMAINS: Domain[] = [
  {
    id: "early-childhood",
    name: "幼儿发展",
    description: "育儿、早教与儿童发展相关",
    emoji: "🌱",
    variant: "coral",
  },
  {
    id: "math",
    name: "数学",
    description: "数学概念、习题与拓展",
    emoji: "🔢",
    variant: "indigo",
  },
  {
    id: "english",
    name: "英语",
    description: "英语学习与阅读材料",
    emoji: "✨",
    variant: "mint",
  },
  {
    id: "chinese",
    name: "语文",
    description: "阅读、写作与语言文字积累",
    emoji: "📖",
    variant: "amber",
  },
  {
    id: "history",
    name: "历史",
    description: "历史事件、人物与脉络梳理",
    emoji: "🏛️",
    variant: "rose",
  },
];

export const DEFAULT_DOMAIN_ID = "early-childhood";

const STORAGE_KEY = "punkrecords_selected_domain";

/** 旧版「通用」已移除，迁移到默认领域 */
const LEGACY_GENERAL_ID = "general";

export function loadSavedDomainId(): string {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === LEGACY_GENERAL_ID) return DEFAULT_DOMAIN_ID;
    if (v && DOMAINS.some((d) => d.id === v)) return v;
  } catch {
    /* ignore */
  }
  return DEFAULT_DOMAIN_ID;
}

export function saveDomainId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* ignore */
  }
}
