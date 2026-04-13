import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { postChatStream } from "./api/chat";
import { apiDomainsToLocal, fetchDomains } from "./api/domains";
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

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

const STORAGE_SIDEBAR_COLLAPSED = "punkrecords_sidebar_collapsed";

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

function IconAgent() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M9 9h.01M15 9h.01M9 15c1.5 1 4.5 1 6 0" />
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
  agent: <IconAgent />,
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
  const messagesRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  /** 流式请求中止（切换领域时打断） */
  const streamAbortRef = useRef<AbortController | null>(null);
  /** 离线演示回复的定时器（切换领域时清除） */
  const demoTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setDomainId(loadSavedDomainId());
  }, []);

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

  useEffect(() => {
    if (!useLiveApi) return;
    let cancelled = false;
    fetchDomains(API_BASE_URL)
      .then((res) => {
        if (cancelled) return;
        const { domains, defaultDomainId } = apiDomainsToLocal(res);
        setDomainsList(domains);
        setDomainId((prev) =>
          domains.some((d) => d.id === prev) ? prev : defaultDomainId,
        );
      })
      .catch(() => {
        if (!cancelled) setDomainsList(DOMAINS);
      });
    return () => {
      cancelled = true;
    };
  }, []);

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

  const currentDomain = useMemo(
    () => domainsList.find((d) => d.id === domainId) ?? domainsList[0],
    [domainId, domainsList],
  );

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((c) => !c);
  }, []);

  const addFiles = useCallback((files: FileList | File[]) => {
    const list = Array.from(files).filter(Boolean);
    if (!list.length) return;
    setPendingFiles((prev) => [...prev, ...list]);
  }, []);

  const send = useCallback(async () => {
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
    const nameSnapshot = currentDomain.name;

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
  }, [draft, pendingFiles, domainId, currentDomain.name]);

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

  return (
    <div className="app">
      <div
        className={`layout${narrowScreen ? " layout--narrow" : ""}${narrowScreen && sidebarCollapsed ? " layout--narrow-rail" : ""}${hasMessages ? " layout--chat-active" : ""}`}
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
              src="/punkrecords_logo.png"
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
                onClick={() => setNavActive(item.id)}
              >
                <span className="sidebar-nav-icon">{NAV_ICONS[item.id]}</span>
                <span className="sidebar-nav-label">{item.label}</span>
              </button>
            ))}
          </nav>
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
            <span className="main-topbar-title">班克记录</span>
          </header>

          <div
            className={`main-inner${hasMessages ? " main-inner--active-chat" : " main-inner--empty"}`}
          >
            <h2 className="hero-heading">
              <span className="hero-greeting">{timeGreeting}</span>
              ，今天想了解点什么？
            </h2>

            <div
              className="domain-pills"
              role="radiogroup"
              aria-label="选择知识区域"
            >
              {domainsList.map((d) => (
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
              当前区域：<strong>{currentDomain.name}</strong>
              <span className="context-hint-dot">·</span>
              {currentDomain.description}
            </p>

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
          </div>
        </section>
      </div>
    </div>
  );
}
