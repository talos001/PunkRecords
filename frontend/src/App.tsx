import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  authLogin,
  authLogout,
  authRefresh,
  authRegister,
  authResetPassword,
  fetchBootstrap,
  putMaterialsPath,
  type Bootstrap,
} from "./api/auth";
import { ApiHttpError, postChatStream } from "./api/chat";
import {
  apiDomainsToLocal,
  createDomain,
  deleteDomain,
  fetchDomains,
  updateDomain,
} from "./api/domains";
import {
  fetchDomainSettings,
  fetchLlmSettings,
  patchDomainSettings,
  patchLlmSettings,
  type DomainSettings,
  type LlmSettings,
  type PatchDomainSettingsPayload,
  type PatchLlmSettingsPayload,
} from "./api/settings";
import {
  PYTHAGORAS_BUBBLE_LABEL,
  PYTHAGORAS_THINKING,
} from "./brand";
import { API_BASE_URL, useLiveApi } from "./config";
import {
  DOMAINS,
  DEFAULT_DOMAIN_ID,
  loadSavedDomainId,
  saveDomainId,
  type Domain,
} from "./domains";
import { SIDEBAR_NAV, type SidebarNavId } from "./sidebarNav";
import { getTimeGreeting } from "./timeGreeting";

type Role = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  /** 流式生成中（首字到达前显示等待提示） */
  streaming?: boolean;
};

type AuthState = "anonymous" | "authenticated_unconfigured" | "authenticated_ready";
type PendingAction = "send" | "settings";
type SettingsTab = "model" | "domain";

type ModelDraft = {
  llm_provider: string;
  llm_model: string;
  llm_base_url: string;
  llm_api_key: string;
};

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

const STORAGE_SIDEBAR_COLLAPSED = "punkrecords_sidebar_collapsed";
const STORAGE_REFRESH_TOKEN = "punkrecords_refresh_token";

/** 无记录时默认收起，与桌面「折叠」语义一致 */
function loadSidebarCollapsed(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_SIDEBAR_COLLAPSED);
    if (raw === "0") return false;
    if (raw === "1") return true;
    return true;
  } catch {
    return true;
  }
}

function saveSidebarCollapsed(collapsed: boolean): void {
  try {
    localStorage.setItem(STORAGE_SIDEBAR_COLLAPSED, collapsed ? "1" : "0");
  } catch {
    /* ignore */
  }
}

const NARROW_BREAKPOINT_PX = 768;

function useNarrowScreen(): boolean {
  const [narrow, setNarrow] = useState(() =>
    typeof window !== "undefined"
      ? window.matchMedia(`(max-width: ${NARROW_BREAKPOINT_PX}px)`).matches
      : false,
  );

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${NARROW_BREAKPOINT_PX}px)`);
    const onChange = () => setNarrow(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return narrow;
}

function IconPaperclip() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M21.44 11.05 12.25 20.24a5.98 5.98 0 1 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2.67 2.67 0 0 1-3.77-3.77l8.49-8.48" />
    </svg>
  );
}

function IconSend() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

/** 侧栏收起时：汉堡菜单，表示可展开 */
function IconSidebarExpand() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

/** 侧栏展开时：左窄右宽分栏，表示可收起为窄条 */
function IconSidebarCollapseToggle() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect x="3" y="4" width="5" height="16" rx="1.5" />
      <rect x="11" y="4" width="10" height="16" rx="1.5" />
    </svg>
  );
}

function IconHome() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <path d="M9 22V12h6v10" />
    </svg>
  );
}

function IconSettings() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

const NAV_ICONS: Record<SidebarNavId, ReactNode> = {
  home: <IconHome />,
  settings: <IconSettings />,
};

export function App() {
  const narrowScreen = useNarrowScreen();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() =>
    loadSidebarCollapsed(),
  );
  const [navActive, setNavActive] = useState<SidebarNavId>("home");
  const [domainsList, setDomainsList] = useState<Domain[]>(DOMAINS);
  const [domainId, setDomainId] = useState<string>(DEFAULT_DOMAIN_ID);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [sending, setSending] = useState(false);
  const [authState, setAuthState] = useState<AuthState>("anonymous");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register" | "reset">(
    "login",
  );
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [showPathModal, setShowPathModal] = useState(false);
  const [pathMode, setPathMode] = useState<"use_default" | "custom">("use_default");
  const [customPath, setCustomPath] = useState("");
  const [pathError, setPathError] = useState("");
  const [pathSubmitting, setPathSubmitting] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [creatingDomain, setCreatingDomain] = useState(false);
  const [domainMutating, setDomainMutating] = useState(false);
  const [newDomainName, setNewDomainName] = useState("");
  const [newDomainDescription, setNewDomainDescription] = useState("");
  const [newDomainEmoji, setNewDomainEmoji] = useState("📁");
  const [editingDomainId, setEditingDomainId] = useState("");
  const [editingDomainName, setEditingDomainName] = useState("");
  const [editingDomainDescription, setEditingDomainDescription] = useState("");
  const [editingDomainEmoji, setEditingDomainEmoji] = useState("📁");
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("model");
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsError, setSettingsError] = useState("");
  const [settingsSuccess, setSettingsSuccess] = useState("");
  const [modelSaving, setModelSaving] = useState(false);
  const [domainSaving, setDomainSaving] = useState(false);
  const [modelSnapshot, setModelSnapshot] = useState<LlmSettings | null>(null);
  const [domainSnapshot, setDomainSnapshot] = useState<DomainSettings | null>(null);
  const [modelDraft, setModelDraft] = useState<ModelDraft>({
    llm_provider: "fake",
    llm_model: "",
    llm_base_url: "",
    llm_api_key: "",
  });
  const [globalMaterialsPath, setGlobalMaterialsPath] = useState("");
  const messagesRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  /** 流式请求中止（切换领域时打断） */
  const streamAbortRef = useRef<AbortController | null>(null);
  /** 离线演示回复的定时器（切换领域时清除） */
  const demoTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const restoredRef = useRef(false);

  useEffect(() => {
    setDomainId(loadSavedDomainId());
    try {
      const saved = localStorage.getItem(STORAGE_REFRESH_TOKEN);
      if (saved) setRefreshToken(saved);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (!useLiveApi || !refreshToken || restoredRef.current) return;
    restoredRef.current = true;
    let cancelled = false;
    authRefresh({ baseUrl: API_BASE_URL, refreshToken })
      .then((tokens) => {
        if (cancelled) return;
        setAccessToken(tokens.access_token);
        setRefreshToken(tokens.refresh_token);
      })
      .catch(() => {
        if (cancelled) return;
        setAuthState("anonymous");
        setAccessToken(null);
        setRefreshToken(null);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshToken]);

  useEffect(() => {
    if (!useLiveApi || !accessToken) return;
    let cancelled = false;
    fetchBootstrap({ baseUrl: API_BASE_URL, accessToken })
      .then((data) => {
        if (cancelled) return;
        setBootstrap(data);
        const nextState =
          data.vault_config_status === "configured"
            ? "authenticated_ready"
            : "authenticated_unconfigured";
        setAuthState(nextState);
      })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiHttpError && e.status === 401) {
          setAuthState("anonymous");
          setAccessToken(null);
          setRefreshToken(null);
          return;
        }
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    setSettingsLoading(true);
    setSettingsError("");
    const loadFromServer = useLiveApi
      ? Promise.all([
          fetchLlmSettings({ baseUrl: API_BASE_URL, accessToken }),
          fetchDomainSettings({ baseUrl: API_BASE_URL, accessToken }),
        ])
      : Promise.resolve<[LlmSettings, DomainSettings]>([
          {
            llm_provider: "fake",
            llm_model: "",
            llm_base_url: "",
            masked_llm_api_key: "",
          },
          { materials_vault_path: "", domain_material_paths: {} },
        ]);
    loadFromServer
      .then(([llmData, domainData]) => {
        if (cancelled) return;
        setModelSnapshot(llmData);
        setDomainSnapshot(domainData);
        setModelDraft({
          llm_provider: llmData.llm_provider ?? "fake",
          llm_model: llmData.llm_model ?? "",
          llm_base_url: llmData.llm_base_url ?? "",
          llm_api_key: "",
        });
        setGlobalMaterialsPath(domainData.materials_vault_path ?? "");
      })
      .catch((e) => {
        if (cancelled) return;
        setSettingsError(e instanceof Error ? e.message : "加载设置失败");
      })
      .finally(() => {
        if (!cancelled) setSettingsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken]);

  useEffect(() => {
    try {
      if (refreshToken) {
        localStorage.setItem(STORAGE_REFRESH_TOKEN, refreshToken);
      } else {
        localStorage.removeItem(STORAGE_REFRESH_TOKEN);
      }
    } catch {
      /* ignore */
    }
  }, [refreshToken]);

  /** 切换知识区域：清空对话，回到空状态，并中止进行中的发送 */
  useEffect(() => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    if (demoTimeoutRef.current !== null) {
      clearTimeout(demoTimeoutRef.current);
      demoTimeoutRef.current = null;
    }
    setMessages([]);
    setDraft("");
    setPendingFiles([]);
    setSending(false);
  }, [domainId]);

  const refreshDomains = useCallback(
    async (preferredDomainId?: string) => {
      const res = await fetchDomains(API_BASE_URL);
      const { domains, defaultDomainId } = apiDomainsToLocal(res);
      const activeDomainIds = new Set(
        domains.filter((d) => d.status === "active").map((d) => d.id),
      );
      const nextDomainId =
        (preferredDomainId && activeDomainIds.has(preferredDomainId)
          ? preferredDomainId
          : undefined) ??
        (activeDomainIds.has(domainId) ? domainId : undefined) ??
        (activeDomainIds.has(defaultDomainId) ? defaultDomainId : undefined) ??
        domains.find((d) => d.status === "active")?.id ??
        domains[0]?.id ??
        DEFAULT_DOMAIN_ID;
      setDomainsList(domains);
      setDomainId(nextDomainId);
      return domains;
    },
    [domainId],
  );

  useEffect(() => {
    if (!useLiveApi) return;
    let cancelled = false;
    refreshDomains()
      .then(() => {
        if (cancelled) return;
      })
      .catch(() => {
        if (!cancelled) setDomainsList(DOMAINS);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshDomains]);

  useEffect(() => {
    saveDomainId(domainId);
  }, [domainId]);

  useEffect(() => {
    saveSidebarCollapsed(sidebarCollapsed);
  }, [sidebarCollapsed]);

  useEffect(() => {
    if (!narrowScreen || sidebarCollapsed) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSidebarCollapsed(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [narrowScreen, sidebarCollapsed]);

  useEffect(() => {
    const el = messagesRef.current;
    if (!el) return;
    requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    });
  }, [messages]);

  useEffect(() => {
    if (authState === "anonymous") {
      setShowAuthModal(Boolean(pendingAction));
      setShowPathModal(false);
      setUserMenuOpen(false);
      return;
    }
    if (authState === "authenticated_unconfigured") {
      setShowAuthModal(false);
      setShowPathModal(true);
      return;
    }
    setShowAuthModal(false);
    setShowPathModal(false);
  }, [authState, pendingAction]);

  useEffect(() => {
    if (!userMenuOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (!userMenuRef.current?.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    window.addEventListener("mousedown", onPointerDown);
    return () => window.removeEventListener("mousedown", onPointerDown);
  }, [userMenuOpen]);

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setRefreshToken(null);
    setBootstrap(null);
    setAuthState("anonymous");
    setUserMenuOpen(false);
  }, []);

  const handleLogout = useCallback(async () => {
    if (accessToken) {
      try {
        await authLogout({ baseUrl: API_BASE_URL, accessToken });
      } catch {
        /* ignore */
      }
    }
    clearSession();
  }, [accessToken, clearSession]);

  const ensureReady = useCallback((action: PendingAction): boolean => {
    if (!useLiveApi) return true;
    if (authState === "anonymous") {
      setPendingAction(action);
      setShowAuthModal(true);
      return false;
    }
    if (authState === "authenticated_unconfigured") {
      setPendingAction(action);
      setShowPathModal(true);
      return false;
    }
    return true;
  }, [authState]);

  const runPendingAction = useCallback(() => {
    if (pendingAction === "send") {
      void send();
    } else if (pendingAction === "settings") {
      setNavActive("settings");
    }
    setPendingAction(null);
  }, [pendingAction]);

  useEffect(() => {
    if (authState !== "authenticated_ready" || !pendingAction) return;
    runPendingAction();
  }, [authState, pendingAction, runPendingAction]);

  const currentDomain = useMemo(
    () => domainsList.find((d) => d.id === domainId) ?? domainsList[0],
    [domainId, domainsList],
  );
  const safeCurrentDomain = useMemo(
    () =>
      currentDomain ?? {
        id: DEFAULT_DOMAIN_ID,
        name: "未配置领域",
        description: "暂无可用领域，请先在领域管理中创建或恢复领域。",
        emoji: "📁",
        variant: "coral" as const,
        status: "active" as const,
      },
    [currentDomain],
  );
  const activeDomains = useMemo(
    () => domainsList.filter((d) => d.status === "active"),
    [domainsList],
  );

  useEffect(() => {
    if (!domainsList.length) return;
    const target =
      domainsList.find((d) => d.id === editingDomainId) ?? domainsList[0];
    if (!target) return;
    setEditingDomainId(target.id);
    setEditingDomainName(target.name);
    setEditingDomainDescription(target.description);
    setEditingDomainEmoji(target.emoji || "📁");
  }, [domainsList, editingDomainId]);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((c) => !c);
  }, []);

  const addFiles = useCallback((files: FileList | File[]) => {
    const list = Array.from(files).filter(Boolean);
    if (!list.length) return;
    setPendingFiles((prev) => [...prev, ...list]);
  }, []);

  const send = useCallback(async () => {
    if (!ensureReady("send")) return;
    const text = draft.trim();
    const hasFiles = pendingFiles.length > 0;
    if (!text && !hasFiles) return;

    let userContent = text;
    if (hasFiles) {
      const names = pendingFiles.map((f) => f.name).join("、");
      const fileNote = `〔随消息附带文件：${names}〕`;
      userContent = text ? `${text}\n\n${fileNote}` : fileNote;
    }

    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: userContent,
    };

    const filesSnapshot = [...pendingFiles];
    const domainSnapshot = domainId;
    const nameSnapshot = safeCurrentDomain.name;

    setMessages((m) => [...m, userMsg]);
    setDraft("");
    setPendingFiles([]);

    if (useLiveApi) {
      setSending(true);
      let assistantMsgId = uid();
      setMessages((m) => [
        ...m,
        {
          id: assistantMsgId,
          role: "assistant",
          content: "",
          streaming: true,
        },
      ]);
      const ac = new AbortController();
      streamAbortRef.current?.abort();
      streamAbortRef.current = ac;
      try {
        await postChatStream({
          baseUrl: API_BASE_URL,
          domainId: domainSnapshot,
          text,
          files: filesSnapshot,
          signal: ac.signal,
          accessToken: accessToken ?? undefined,
          onEvent: (ev) => {
            // 不要用服务端 start.id 替换本条消息的 id：setState 异步，紧随其后的 delta
            // 会用新 id 去匹配，而树里可能仍是旧 id，导致永远不拼接正文、一直停在思考提示。
            if (ev.type === "start") {
              return;
            }
            if (ev.type === "delta") {
              setMessages((m) =>
                m.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        content: msg.content + ev.text,
                        streaming: true,
                      }
                    : msg,
                ),
              );
              return;
            }
            if (ev.type === "done") {
              setMessages((m) =>
                m.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, streaming: false }
                    : msg,
                ),
              );
              return;
            }
            if (ev.type === "error") {
              setMessages((m) =>
                m.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        content: `发送失败：${ev.message}`,
                        streaming: false,
                      }
                    : msg,
                ),
              );
            }
          },
        });
      } catch (e) {
        if (
          (e instanceof DOMException && e.name === "AbortError") ||
          (e instanceof Error && e.name === "AbortError")
        ) {
          return;
        }
        if (e instanceof ApiHttpError) {
          if (e.status === 401) {
            clearSession();
            setPendingAction("send");
            return;
          }
          if (e.status === 428) {
            setAuthState("authenticated_unconfigured");
            setPendingAction("send");
            return;
          }
        }
        const msg = e instanceof Error ? e.message : "发送失败";
        setMessages((m) =>
          m.map((x) =>
            x.id === assistantMsgId
              ? { ...x, content: `发送失败：${msg}`, streaming: false }
              : x,
          ),
        );
      } finally {
        setSending(false);
        if (streamAbortRef.current === ac) streamAbortRef.current = null;
      }
      return;
    }

    demoTimeoutRef.current = setTimeout(() => {
      demoTimeoutRef.current = null;
      setMessages((m) => [
        ...m,
        {
          id: uid(),
          role: "assistant",
          content:
            `我是毕达哥拉斯（Pythagoras），贝加庞克的智慧分身。已收到你在「${nameSnapshot}」下的消息。（当前为前端离线演示；接入后端后将由我做知识整理与回答。）`,
        },
      ]);
    }, 400);
  }, [
    accessToken,
    clearSession,
    safeCurrentDomain.name,
    domainId,
    draft,
    ensureReady,
    pendingFiles,
  ]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!sending) void send();
    }
  };

  const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.files;
    if (items?.length) {
      e.preventDefault();
      addFiles(items);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  const hasMessages = messages.length > 0;
  const timeGreeting = useMemo(() => getTimeGreeting(), []);
  const isHomeView = navActive === "home";
  const mainTopbarTitle = navActive === "settings" ? "设置" : "班克记录";
  const modelDirty = useMemo(() => {
    if (!modelSnapshot) return false;
    return (
      modelDraft.llm_provider !== (modelSnapshot.llm_provider ?? "fake") ||
      modelDraft.llm_model !== (modelSnapshot.llm_model ?? "") ||
      modelDraft.llm_base_url !== (modelSnapshot.llm_base_url ?? "") ||
      modelDraft.llm_api_key.trim().length > 0
    );
  }, [modelDraft, modelSnapshot]);
  const domainPathDirty = useMemo(
    () => globalMaterialsPath.trim() !== (domainSnapshot?.materials_vault_path ?? ""),
    [globalMaterialsPath, domainSnapshot],
  );

  const updateModelSnapshot = useCallback((next: LlmSettings) => {
    setModelSnapshot(next);
    setModelDraft((prev) => ({
      llm_provider: next.llm_provider ?? prev.llm_provider,
      llm_model: next.llm_model ?? prev.llm_model,
      llm_base_url: next.llm_base_url ?? prev.llm_base_url,
      llm_api_key: "",
    }));
  }, []);

  const updateDomainSnapshot = useCallback((next: DomainSettings) => {
    setDomainSnapshot(next);
    setGlobalMaterialsPath(next.materials_vault_path ?? "");
  }, []);

  const saveModelSettings = useCallback(async () => {
    if (!accessToken) return;
    if (!modelDraft.llm_provider.trim() || !modelDraft.llm_model.trim()) {
      setSettingsError("Provider 与模型名称为必填项");
      return;
    }
    if (
      modelDraft.llm_base_url.trim() &&
      !/^https?:\/\/.+/i.test(modelDraft.llm_base_url.trim())
    ) {
      setSettingsError("Base URL 需为合法 http(s) 地址");
      return;
    }
    const body: PatchLlmSettingsPayload = {
      llm_provider: modelDraft.llm_provider.trim(),
      llm_model: modelDraft.llm_model.trim(),
      llm_base_url: modelDraft.llm_base_url.trim(),
    };
    if (modelDraft.llm_api_key.trim()) body.llm_api_key = modelDraft.llm_api_key.trim();
    setModelSaving(true);
    setSettingsError("");
    setSettingsSuccess("");
    try {
      if (useLiveApi) {
        const next = await patchLlmSettings({ baseUrl: API_BASE_URL, accessToken, body });
        updateModelSnapshot(next);
      } else {
        updateModelSnapshot({
          llm_provider: body.llm_provider ?? modelDraft.llm_provider,
          llm_model: body.llm_model ?? modelDraft.llm_model,
          llm_base_url: body.llm_base_url ?? modelDraft.llm_base_url,
          masked_llm_api_key: modelDraft.llm_api_key ? "********" : modelSnapshot?.masked_llm_api_key ?? "",
        });
      }
      setSettingsSuccess("模型配置已保存。");
    } catch (e) {
      setSettingsError(e instanceof Error ? e.message : "模型配置保存失败");
    } finally {
      setModelSaving(false);
    }
  }, [accessToken, modelDraft, modelSnapshot, updateModelSnapshot]);

  const saveDomainPathSettings = useCallback(async () => {
    if (!accessToken) return;
    const body: PatchDomainSettingsPayload = {
      materials_vault_path: globalMaterialsPath.trim(),
    };
    setDomainSaving(true);
    setSettingsError("");
    setSettingsSuccess("");
    try {
      if (useLiveApi) {
        const next = await patchDomainSettings({ baseUrl: API_BASE_URL, accessToken, body });
        updateDomainSnapshot(next);
      } else {
        updateDomainSnapshot({
          materials_vault_path: body.materials_vault_path ?? "",
          domain_material_paths: domainSnapshot?.domain_material_paths ?? {},
        });
      }
      setSettingsSuccess("领域管理与路径配置已保存。");
    } catch (e) {
      setSettingsError(e instanceof Error ? e.message : "路径配置保存失败");
    } finally {
      setDomainSaving(false);
    }
  }, [
    accessToken,
    globalMaterialsPath,
    domainSnapshot,
    updateDomainSnapshot,
  ]);

  return (
    <div className="app">
      <div
        className={`layout${narrowScreen ? " layout--narrow" : ""}${narrowScreen && sidebarCollapsed ? " layout--narrow-rail" : ""}${isHomeView && hasMessages ? " layout--chat-active" : ""}`}
      >
        {narrowScreen && !sidebarCollapsed && (
          <button
            type="button"
            className="sidebar-backdrop"
            aria-label="关闭侧栏"
            onClick={toggleSidebar}
          />
        )}
        <aside
          id="app-sidebar"
          className={`sidebar${sidebarCollapsed ? " sidebar--collapsed" : ""}`}
          aria-label="主导航"
        >
          <div className="sidebar-brand">
            <img
              className="brand-logo"
              src="/punkrecords_logo.svg"
              alt="PunkRecords 班克记录"
            />
          </div>

          <nav className="sidebar-nav" aria-label="功能">
            {SIDEBAR_NAV.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`sidebar-nav-item${navActive === item.id ? " sidebar-nav-item--active" : ""}`}
                title={item.label}
                onClick={() => {
                  if (item.id === "settings" && !ensureReady("settings")) return;
                  setUserMenuOpen(false);
                  setNavActive(item.id);
                }}
              >
                <span className="sidebar-nav-icon">{NAV_ICONS[item.id]}</span>
                <span className="sidebar-nav-label">{item.label}</span>
              </button>
            ))}
          </nav>
          {useLiveApi && authState !== "anonymous" && (
            <div className="sidebar-user" ref={userMenuRef}>
              <button
                type="button"
                className="sidebar-user-trigger"
                onClick={() => setUserMenuOpen((v) => !v)}
                title={bootstrap?.user.username ?? "用户"}
              >
                <span className="sidebar-user-avatar">
                  {(bootstrap?.user.username ?? "用").slice(0, 1).toUpperCase()}
                </span>
                <span className="sidebar-user-name">
                  {bootstrap?.user.username ?? "用户"}
                </span>
              </button>
              {userMenuOpen && (
                <div className="sidebar-user-menu">
                  <button
                    type="button"
                    className="sidebar-user-menu-item"
                    onClick={() => {
                      setNavActive("home");
                      setUserMenuOpen(false);
                    }}
                  >
                    主页
                  </button>
                  <button
                    type="button"
                    className="sidebar-user-menu-item"
                    onClick={() => {
                      if (!ensureReady("settings")) return;
                      setNavActive("settings");
                      setUserMenuOpen(false);
                    }}
                  >
                    设置
                  </button>
                  <button
                    type="button"
                    className="sidebar-user-menu-item sidebar-user-menu-item--danger"
                    onClick={() => void handleLogout()}
                  >
                    退出登录
                  </button>
                </div>
              )}
            </div>
          )}
        </aside>

        <section className="main-panel" aria-label="对话">
          <header className="main-topbar">
            <button
              type="button"
              className="main-topbar-toggle"
              onClick={toggleSidebar}
              aria-expanded={!sidebarCollapsed}
              aria-controls="app-sidebar"
              aria-label={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
            >
              {sidebarCollapsed ? (
                <IconSidebarExpand />
              ) : (
                <IconSidebarCollapseToggle />
              )}
            </button>
            <span className="main-topbar-title">{mainTopbarTitle}</span>
          </header>

          <div
            className={`main-inner${isHomeView ? (hasMessages ? " main-inner--active-chat" : " main-inner--empty") : " main-inner--panel"}`}
          >
            {isHomeView && (
              <>
                <h2 className="hero-heading">
                  <span className="hero-greeting">{timeGreeting}</span>
                  ，今天想了解点什么？
                </h2>

                <div
                  className="domain-pills"
                  role="radiogroup"
                  aria-label="选择知识区域"
                >
                  {activeDomains.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      role="radio"
                      aria-checked={d.id === domainId}
                      className={`domain-pill${d.id === domainId ? " domain-pill--active" : ""}`}
                      onClick={() => setDomainId(d.id)}
                    >
                      <span className="domain-pill-emoji" aria-hidden>
                        {d.emoji}
                      </span>
                      <span className="domain-pill-name">{d.name}</span>
                    </button>
                  ))}
                </div>

                <p className="context-hint">
                  当前区域：<strong>{safeCurrentDomain.name}</strong>
                  <span className="context-hint-dot">·</span>
                  {safeCurrentDomain.description}
                </p>
              </>
            )}

            {navActive === "settings" && (
              <section className="domain-manager settings-panel" aria-label="设置">
                <div className="domain-manager-header">
                  <h3>设置</h3>
                  <button
                    type="button"
                    className="domain-manager-back"
                    onClick={() => setNavActive("home")}
                  >
                    返回主页
                  </button>
                </div>
                <div className="settings-tabs" role="tablist" aria-label="设置标签">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={settingsTab === "model"}
                    className={`settings-tab${settingsTab === "model" ? " settings-tab--active" : ""}`}
                    onClick={() => {
                      setSettingsTab("model");
                      setSettingsError("");
                      setSettingsSuccess("");
                    }}
                  >
                    模型配置
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={settingsTab === "domain"}
                    className={`settings-tab${settingsTab === "domain" ? " settings-tab--active" : ""}`}
                    onClick={() => {
                      setSettingsTab("domain");
                      setSettingsError("");
                      setSettingsSuccess("");
                    }}
                  >
                    领域管理
                  </button>
                </div>
                {settingsError && <p className="domain-manager-error">{settingsError}</p>}
                {settingsSuccess && (
                  <p className="domain-manager-success">{settingsSuccess}</p>
                )}
                {settingsLoading && <p className="domain-manager-hint">设置加载中...</p>}

                {settingsTab === "model" && (
                  <div className="settings-card">
                    <p className="domain-manager-hint">
                      在此配置模型 Provider、模型名称和访问地址。密钥留空表示不变更。
                    </p>
                    <div className="domain-form-grid">
                      <label className="settings-field">
                        <span>Provider</span>
                        <select
                          className="domain-input settings-provider-input"
                          value={modelDraft.llm_provider}
                          onChange={(e) =>
                            setModelDraft((prev) => ({ ...prev, llm_provider: e.target.value }))
                          }
                        >
                          {["fake", "anthropic", "openai", "ollama"].map((provider) => (
                            <option key={provider} value={provider}>
                              {provider}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="settings-field">
                        <span>模型名称</span>
                        <input
                          className="domain-input settings-model-input"
                          placeholder="如 claude-3-5-sonnet"
                          value={modelDraft.llm_model}
                          onChange={(e) =>
                            setModelDraft((prev) => ({ ...prev, llm_model: e.target.value }))
                          }
                        />
                      </label>
                      <label className="settings-field domain-input--full">
                        <span>Base URL（可选）</span>
                        <input
                          className="domain-input"
                          placeholder="https://api.example.com/v1"
                          value={modelDraft.llm_base_url}
                          onChange={(e) =>
                            setModelDraft((prev) => ({ ...prev, llm_base_url: e.target.value }))
                          }
                        />
                      </label>
                      <label className="settings-field domain-input--full">
                        <span>API Key（可选）</span>
                        <input
                          className="domain-input"
                          type="password"
                          placeholder={
                            modelSnapshot?.masked_llm_api_key
                              ? "已配置，留空表示不修改"
                              : "输入后保存"
                          }
                          value={modelDraft.llm_api_key}
                          onChange={(e) =>
                            setModelDraft((prev) => ({ ...prev, llm_api_key: e.target.value }))
                          }
                        />
                      </label>
                    </div>
                    <div className="domain-action-row">
                      <button
                        type="button"
                        className="domain-action-primary"
                        disabled={modelSaving || !modelDirty}
                        onClick={() => void saveModelSettings()}
                      >
                        {modelSaving ? "保存中..." : "保存模型配置"}
                      </button>
                    </div>
                  </div>
                )}

                {settingsTab === "domain" && (
                  <>
                    <div className="settings-card">
                      <p className="domain-manager-hint">
                        全局路径为默认材料库位置。领域路径由后端根据全局路径自动生成，此处仅回显。
                      </p>
                      <label className="settings-field domain-input--full">
                        <span>全局材料库路径</span>
                        <input
                          className="domain-input"
                          placeholder="如 /data/punkrecords/materials"
                          value={globalMaterialsPath}
                          onChange={(e) => setGlobalMaterialsPath(e.target.value)}
                        />
                      </label>
                    </div>
                    <div className="settings-card">
                      <div className="domain-form-header">
                        <strong>各领域路径覆盖</strong>
                      </div>
                      <div className="domain-path-list">
                        {domainsList.map((d) => (
                          <label key={d.id} className="domain-path-row">
                            <span className="domain-path-label">
                              <span>{d.emoji}</span>
                              <span>{d.name}</span>
                              {d.status === "archived" && (
                                <span className="domain-path-tag">已归档</span>
                              )}
                            </span>
                            <span className="domain-path-value">
                              {(domainSnapshot?.domain_material_paths ?? {})[d.id] ?? "未生成"}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                <form
                  className="domain-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!ensureReady("settings")) return;
                    if (!accessToken || !newDomainName.trim()) return;
                    setDomainMutating(true);
                    setSettingsError("");
                    setSettingsSuccess("");
                    void createDomain({
                      baseUrl: API_BASE_URL,
                      accessToken,
                      body: {
                        name: newDomainName.trim(),
                        description: newDomainDescription.trim(),
                        emoji: newDomainEmoji.trim() || "📁",
                      },
                    })
                      .then(async (res) => {
                        const createdId = res.domain.id;
                        const domains = await refreshDomains(createdId);
                        const created = domains.find((d) => d.id === createdId);
                        if (created) {
                          setEditingDomainId(created.id);
                          setEditingDomainName(created.name);
                          setEditingDomainDescription(created.description);
                          setEditingDomainEmoji(created.emoji || "📁");
                        }
                      })
                      .then(() => {
                        setNewDomainName("");
                        setNewDomainDescription("");
                        setNewDomainEmoji("📁");
                        setCreatingDomain(false);
                        setSettingsSuccess("领域已创建并选中。");
                      })
                      .catch((e: unknown) => {
                        setSettingsError(
                          e instanceof Error ? e.message : "新增领域失败",
                        );
                      })
                      .finally(() => {
                        setDomainMutating(false);
                      });
                  }}
                >
                  <div className="domain-form-header">
                    <strong>新增领域</strong>
                    <button
                      type="button"
                      className="domain-manager-toggle"
                      onClick={() => setCreatingDomain((v) => !v)}
                    >
                      {creatingDomain ? "收起" : "展开"}
                    </button>
                  </div>
                  {creatingDomain && (
                    <div className="domain-form-grid">
                      <input
                        className="domain-input"
                        placeholder="领域名称（必填）"
                        value={newDomainName}
                        onChange={(e) => setNewDomainName(e.target.value)}
                      />
                      <input
                        className="domain-input"
                        placeholder="Emoji（如 📚）"
                        value={newDomainEmoji}
                        onChange={(e) => setNewDomainEmoji(e.target.value)}
                      />
                      <input
                        className="domain-input domain-input--full"
                        placeholder="领域描述"
                        value={newDomainDescription}
                        onChange={(e) => setNewDomainDescription(e.target.value)}
                      />
                      <button
                        type="submit"
                        className="domain-action-primary"
                        disabled={domainMutating || !newDomainName.trim()}
                      >
                        {domainMutating ? "提交中..." : "新增并选中"}
                      </button>
                    </div>
                  )}
                </form>

                <div className="domain-form">
                  <div className="domain-form-header">
                    <strong>编辑领域</strong>
                  </div>
                  <div className="domain-form-grid">
                    <select
                      className="domain-input"
                      value={editingDomainId}
                      onChange={(e) => {
                        const target = domainsList.find(
                          (d) => d.id === e.target.value,
                        );
                        if (!target) return;
                        setEditingDomainId(target.id);
                        setEditingDomainName(target.name);
                        setEditingDomainDescription(target.description);
                        setEditingDomainEmoji(target.emoji || "📁");
                      }}
                    >
                      {domainsList.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} {d.status === "archived" ? "（已归档）" : ""}
                        </option>
                      ))}
                    </select>
                    <input
                      className="domain-input"
                      placeholder="Emoji（如 📚）"
                      value={editingDomainEmoji}
                      onChange={(e) => setEditingDomainEmoji(e.target.value)}
                    />
                    <input
                      className="domain-input domain-input--full"
                      placeholder="领域名称"
                      value={editingDomainName}
                      onChange={(e) => setEditingDomainName(e.target.value)}
                    />
                    <input
                      className="domain-input domain-input--full"
                      placeholder="领域描述"
                      value={editingDomainDescription}
                      onChange={(e) => setEditingDomainDescription(e.target.value)}
                    />
                    <div className="domain-action-row">
                      <button
                        type="button"
                        className="domain-action-primary"
                        disabled={domainMutating || !editingDomainId}
                        onClick={() => {
                          if (!ensureReady("settings")) return;
                          if (!accessToken || !editingDomainId) return;
                          setDomainMutating(true);
                          setSettingsError("");
                          setSettingsSuccess("");
                          void updateDomain({
                            baseUrl: API_BASE_URL,
                            accessToken,
                            domainId: editingDomainId,
                            body: {
                              name: editingDomainName.trim(),
                              description: editingDomainDescription.trim(),
                              emoji: editingDomainEmoji.trim() || "📁",
                            },
                          })
                            .then(() => refreshDomains(editingDomainId))
                            .then(() => {
                              setSettingsSuccess("领域基础信息已更新。");
                            })
                            .catch((e: unknown) => {
                              setSettingsError(
                                e instanceof Error ? e.message : "更新领域失败",
                              );
                            })
                            .finally(() => {
                              setDomainMutating(false);
                            });
                        }}
                      >
                        {domainMutating ? "处理中..." : "保存编辑"}
                      </button>
                      <button
                        type="button"
                        className="domain-action-danger"
                        disabled={domainMutating || !editingDomainId}
                        onClick={() => {
                          if (!ensureReady("settings")) return;
                          if (!accessToken || !editingDomainId) return;
                          setDomainMutating(true);
                          setSettingsError("");
                          setSettingsSuccess("");
                          void deleteDomain({
                            baseUrl: API_BASE_URL,
                            accessToken,
                            domainId: editingDomainId,
                          })
                            .then(async () => {
                              await refreshDomains();
                              setSettingsSuccess("领域已删除。");
                            })
                            .catch(async (e: unknown) => {
                              if (
                                e instanceof ApiHttpError &&
                                e.status === 409 &&
                                e.code === "DOMAIN_NOT_EMPTY"
                              ) {
                                await updateDomain({
                                  baseUrl: API_BASE_URL,
                                  accessToken,
                                  domainId: editingDomainId,
                                  body: { status: "archived" },
                                });
                                await refreshDomains();
                                setSettingsSuccess(
                                  "领域包含内容，已自动改为归档状态。",
                                );
                                return;
                              }
                              throw e;
                            })
                            .catch((e: unknown) => {
                              setSettingsError(
                                e instanceof Error ? e.message : "归档领域失败",
                              );
                            })
                            .finally(() => {
                              setDomainMutating(false);
                            });
                        }}
                      >
                        归档 / 删除
                      </button>
                    </div>
                  </div>
                </div>
                <div className="domain-action-row">
                  <button
                    type="button"
                    className="domain-action-primary"
                    disabled={domainSaving || !domainPathDirty}
                    onClick={() => void saveDomainPathSettings()}
                  >
                    {domainSaving ? "保存中..." : "保存领域与路径配置"}
                  </button>
                </div>
                  </>
                )}
              </section>
            )}

            {isHomeView && (
              <>
                <main className="chat">
                  <div className="messages" ref={messagesRef}>
                    {messages.length === 0 && (
                      <div className="empty">
                        <p>
                          在下方输入框打字、粘贴链接，或将文件拖入输入区；也可点击回形针添加文件。
                        </p>
                      </div>
                    )}
                    {messages.map((msg) => (
                      <article
                        key={msg.id}
                        className={`bubble bubble--${msg.role}`}
                      >
                        <div className="bubble-meta">
                          {msg.role === "user" ? "你" : PYTHAGORAS_BUBBLE_LABEL}
                        </div>
                        <div className="bubble-body">
                          {msg.content}
                          {msg.role === "assistant" &&
                            msg.streaming &&
                            !msg.content && (
                              <span className="bubble-wait" aria-live="polite">
                                {PYTHAGORAS_THINKING}
                              </span>
                            )}
                        </div>
                      </article>
                    ))}
                  </div>
                </main>

                <footer
                  className="composer-wrap"
                  ref={composerRef}
                  onDragOver={onDragOver}
                  onDrop={onDrop}
                >
                  {pendingFiles.length > 0 && (
                    <p className="composer-hint" aria-live="polite">
                      将随下一条消息发送：{pendingFiles.map((f) => f.name).join("、")}
                    </p>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="visually-hidden"
                    accept=".md,.markdown,.pdf,application/pdf,text/markdown"
                    multiple
                    onChange={(e) => {
                      const fl = e.target.files;
                      if (fl) addFiles(fl);
                      e.target.value = "";
                    }}
                  />
                  <div className="composer-shell">
                    <button
                      type="button"
                      className="btn-attach"
                      aria-label="添加文件"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <IconPaperclip />
                    </button>
                    <textarea
                      className="input-text"
                      rows={1}
                      placeholder="输入问题、粘贴链接或拖入文件…（Enter 发送，Shift+Enter 换行）"
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={onKeyDown}
                      onPaste={onPaste}
                    />
                    <button
                      type="button"
                      className="btn-send"
                      aria-label="发送"
                      disabled={sending}
                      onClick={() => void send()}
                    >
                      <IconSend />
                    </button>
                  </div>
                </footer>
              </>
            )}
          </div>
        </section>
      </div>
      {showAuthModal && (
        <div className="modal-mask" role="dialog" aria-modal>
          <div className="modal-card">
            <button
              type="button"
              className="modal-close"
              aria-label="关闭"
              onClick={() => {
                setShowAuthModal(false);
                setPendingAction(null);
                setAuthError("");
                setPassword("");
                setConfirmPassword("");
              }}
            >
              ×
            </button>
            <h3>
              {authMode === "login"
                ? "请先登录"
                : authMode === "register"
                  ? "创建账号"
                  : "重置密码"}
            </h3>
            <input
              className="modal-input"
              placeholder="用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              className="modal-input"
              type="password"
              placeholder={authMode === "reset" ? "新密码" : "密码"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {(authMode === "register" || authMode === "reset") && (
              <input
                className="modal-input"
                type="password"
                placeholder="确认密码"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            )}
            {authError && <p className="modal-error">{authError}</p>}
            <button
              type="button"
              className="modal-primary"
              disabled={authLoading}
              onClick={async () => {
                if (
                  (authMode === "register" || authMode === "reset") &&
                  password !== confirmPassword
                ) {
                  setAuthError("两次输入的密码不一致");
                  return;
                }
                setAuthLoading(true);
                setAuthError("");
                try {
                  if (authMode === "reset") {
                    await authResetPassword({
                      baseUrl: API_BASE_URL,
                      username,
                      newPassword: password,
                    });
                    setAuthMode("login");
                    setAuthError("密码已重置，请使用新密码登录");
                    setPassword("");
                    setConfirmPassword("");
                    return;
                  }
                  const tokens =
                    authMode === "login"
                      ? await authLogin({
                          baseUrl: API_BASE_URL,
                          username,
                          password,
                        })
                      : await authRegister({
                          baseUrl: API_BASE_URL,
                          username,
                          password,
                        });
                  setAccessToken(tokens.access_token);
                  setRefreshToken(tokens.refresh_token);
                } catch (e) {
                  setAuthError(e instanceof Error ? e.message : "登录失败");
                } finally {
                  setAuthLoading(false);
                }
              }}
            >
              {authLoading
                ? "提交中..."
                : authMode === "login"
                  ? "登录"
                  : authMode === "register"
                    ? "注册并登录"
                    : "重置密码"}
            </button>
            <button
              type="button"
              className="modal-secondary"
              onClick={() => {
                setAuthMode((m) => (m === "login" ? "register" : "login"));
                setAuthError("");
                setPassword("");
                setConfirmPassword("");
              }}
            >
              {authMode === "login" ? "没有账号？去注册" : "已有账号？去登录"}
            </button>
            <button
              type="button"
              className="modal-secondary"
              onClick={() => {
                setAuthMode("reset");
                setAuthError("");
                setPassword("");
                setConfirmPassword("");
              }}
            >
              忘记密码？
            </button>
          </div>
        </div>
      )}
      {showPathModal && bootstrap && (
        <div className="modal-mask" role="dialog" aria-modal>
          <div className="modal-card">
            <h3>确认材料库保存位置</h3>
            <p className="modal-subtitle">
              当前生效路径：{pathMode === "custom" ? customPath || "（请输入）" : bootstrap.effective_materials_path}
            </p>
            <label className="modal-radio">
              <input
                type="radio"
                checked={pathMode === "use_default"}
                onChange={() => setPathMode("use_default")}
              />
              使用默认路径
            </label>
            <label className="modal-radio">
              <input
                type="radio"
                checked={pathMode === "custom"}
                onChange={() => setPathMode("custom")}
              />
              使用自定义路径
            </label>
            {pathMode === "custom" && (
              <input
                className="modal-input"
                placeholder="请输入自定义目录路径"
                value={customPath}
                onChange={(e) => setCustomPath(e.target.value)}
              />
            )}
            {pathError && <p className="modal-error">{pathError}</p>}
            <button
              type="button"
              className="modal-primary"
              disabled={pathSubmitting || !accessToken}
              onClick={async () => {
                if (!accessToken) return;
                setPathSubmitting(true);
                setPathError("");
                const effective =
                  pathMode === "custom"
                    ? customPath.trim()
                    : bootstrap.effective_materials_path;
                try {
                  await putMaterialsPath({
                    baseUrl: API_BASE_URL,
                    accessToken,
                    mode: pathMode,
                    customPath: pathMode === "custom" ? customPath.trim() : undefined,
                    confirmEffectivePath: effective,
                  });
                  setAuthState("authenticated_ready");
                  runPendingAction();
                } catch (e) {
                  setPathError(e instanceof Error ? e.message : "保存失败");
                } finally {
                  setPathSubmitting(false);
                }
              }}
            >
              {pathSubmitting ? "保存中..." : "确认并继续"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
