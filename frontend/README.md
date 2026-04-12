# PunkRecords Web UI

技术栈：**TypeScript · React 18 · Vite 5**。行为与文案遵循仓库根目录 [`docs/ui_design.md`](../docs/ui_design.md)。

## 开发

需要 Node.js 18+（建议 20 LTS）。

```bash
cd frontend
npm install
npm run dev
```

浏览器打开终端提示的本地地址（默认 `http://127.0.0.1:5173`）。

## 构建

```bash
npm run build
```

静态文件输出到 `frontend/dist/`，可由任意静态服务器或后续 Python（如 FastAPI `StaticFiles`）托管。

## 说明

- 当前对话回复为 **前端占位**，后端 API 接入后替换 `App.tsx` 中的发送逻辑。
- 领域列表见 `src/domains.ts`；**默认领域为「幼儿发展」**；记住上次选择（`localStorage`），旧版「通用」会迁移为默认领域。
- Logo 置于 `public/punkrecords_logo.png`，与仓库 `docs/punkrecords_logo.png` 保持一致。
- 左侧栏可折叠（顶栏按钮切换），并含「主页 / 选择 Agent / 设置」占位导航；折叠状态会记住。
