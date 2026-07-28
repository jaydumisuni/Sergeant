const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const { collectFindings, escapeHtml, summarizePayload } = require("./results");

// Stable setting IDs are retained so existing installations keep their config.
const LLM_SETTING_KEYS = {
  policy: "llmPolicy",
  provider: "llmProvider",
  baseUrl: "llmBaseUrl",
  model: "llmModel",
  protocol: "llmProtocol",
  council: "llmCouncil",
  maxRounds: "cplMaxRounds",
  maxMembers: "cplMaxCouncilMembers",
};

class SergeantCommandCenterProvider {
  constructor(context, options) {
    this.context = context;
    this.options = options;
    this.sidebarView = null;
    this.fullPanel = null;
    this.startedAt = 0;
    this.state = {
      status: "Standing By",
      running: "",
      runningTitle: "",
      last: null,
      history: context.globalState.get("sergeant.commandCenter.history", []),
    };
  }

  resolveWebviewView(webviewView) {
    this.sidebarView = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.file(path.join(this.context.extensionPath, "resources"))],
    };
    webviewView.webview.html = this.renderCompact(webviewView.webview);
    webviewView.webview.onDidReceiveMessage((message) => this.handleMessage(message));
  }

  openFullCommandCenter() {
    if (this.fullPanel) {
      this.fullPanel.reveal(vscode.ViewColumn.One);
      this.postState();
      return;
    }
    this.fullPanel = vscode.window.createWebviewPanel(
      "sergeant.commandCenter",
      "Sergeant Review Center",
      vscode.ViewColumn.One,
      { enableScripts: true, retainContextWhenHidden: true },
    );
    this.fullPanel.webview.html = this.renderFull();
    this.fullPanel.webview.onDidReceiveMessage((message) => this.handleMessage(message));
    this.fullPanel.onDidDispose(() => { this.fullPanel = null; });
  }

  setRunning(actionId, title) {
    this.startedAt = Date.now();
    this.state = { ...this.state, status: "Running", running: actionId || title, runningTitle: title, notice: "", error: false };
    this.postState();
  }

  setIdle(message = "") {
    this.state = { ...this.state, status: "Standing By", running: "", runningTitle: "", notice: message, error: Boolean(message) };
    this.postState();
  }

  async setResult(result) {
    const summary = summarizePayload(result.payload, result.exitCode);
    const durationSeconds = this.startedAt ? Math.max(1, Math.round((Date.now() - this.startedAt) / 1000)) : 0;
    const latest = {
      title: result.title,
      summary,
      findings: collectFindings(result.payload).slice(0, 20),
      finishedAt: result.finishedAt,
      justFinished: true,
    };
    const historyItem = {
      id: `#${String(Date.now()).slice(-6)}`,
      date: new Date(result.finishedAt).toLocaleString(),
      result: summary.verdict,
      mission: result.title,
      title: result.title,
      verdict: summary.verdict,
      duration: durationSeconds ? `${durationSeconds}s` : "—",
      finishedAt: result.finishedAt,
    };
    const history = [historyItem, ...this.state.history].slice(0, 50);
    this.state = {
      ...this.state,
      status: result.exitCode === 0 ? "Complete" : "Needs Attention",
      running: "",
      runningTitle: "",
      last: latest,
      history,
      notice: result.exitCode === 0 ? "Review completed. Evidence is available in the last report." : `Review exited with code ${result.exitCode}.`,
      error: result.exitCode !== 0,
    };
    await this.context.globalState.update("sergeant.commandCenter.history", history);
    await this.postState();
    this.state.last.justFinished = false;
  }

  semanticSettings() {
    const configuration = vscode.workspace.getConfiguration("sergeant");
    return Object.fromEntries(
      Object.entries(LLM_SETTING_KEYS).map(([publicKey, settingKey]) => [publicKey, configuration.get(settingKey)]),
    );
  }

  async buildState() {
    const editor = vscode.window.activeTextEditor;
    const activeFile = editor ? path.relative(this.options.workspaceRoot(), editor.document.uri.fsPath) || editor.document.uri.fsPath : "";
    const git = await this.options.gitContext();
    return {
      ...this.state,
      platform: "VS Code",
      workspace: this.options.workspaceName(),
      workspaces: (vscode.workspace.workspaceFolders || []).map((folder) => folder.name),
      root: this.options.workspaceRoot(),
      activeFile,
      branch: git.branch,
      changedFilesCount: git.changedFilesCount,
      changedFiles: git.changedFiles,
      settings: this.semanticSettings(),
    };
  }

  async postState() {
    const message = { type: "sergeantState", state: await this.buildState() };
    this.sidebarView?.webview.postMessage(message);
    this.fullPanel?.webview.postMessage(message);
  }

  async saveSemanticSettings(settings) {
    const configuration = vscode.workspace.getConfiguration("sergeant");
    for (const [publicKey, settingKey] of Object.entries(LLM_SETTING_KEYS)) {
      if (!Object.prototype.hasOwnProperty.call(settings || {}, publicKey)) continue;
      const value = ["maxRounds", "maxMembers"].includes(publicKey)
        ? Number(settings[publicKey])
        : String(settings[publicKey] ?? "");
      await configuration.update(settingKey, value, vscode.ConfigurationTarget.Global);
    }
  }

  async handleMessage(message) {
    try {
      if (message?.type === "run") await this.options.runAction(message.action);
      else if (message?.type === "openFull") this.openFullCommandCenter();
      else if (message?.type === "openLast") await this.options.openLast();
      else if (message?.type === "copyLast") await this.options.copyLast();
      else if (message?.type === "exportLast") await this.options.exportLast();
      else if (message?.type === "selectWorkspace") {
        this.options.selectWorkspace(String(message.workspace || ""));
        await this.postState();
      } else if (message?.type === "saveSettings") {
        await this.saveSemanticSettings(message.settings || {});
        await this.postState();
      } else if (message?.type === "refresh" || message?.type === "ready") await this.postState();
    } catch (error) {
      this.setIdle(error.message || String(error));
      vscode.window.showErrorMessage(error.message || String(error));
    }
  }

  renderCompact(webview) {
    const iconUri = webview.asWebviewUri(vscode.Uri.file(path.join(this.context.extensionPath, "resources", "srg-logo-and-icon.png")));
    const primaryIds = new Set(["reviewWorkspace", "reviewCurrentFile", "reviewChangedFiles", "finalProof"]);
    const actionButtons = this.options.actions
      .filter((action) => primaryIds.has(action.id))
      .map((action) => `<button class="action ${action.id === "reviewWorkspace" ? "primary" : ""}" data-run="${escapeHtml(action.id)}"><span>${escapeHtml(action.label)}</span><small>${escapeHtml(action.description)}</small></button>`)
      .join("");
    return `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>:root{--bg:#070912;--panel:#101522;--panel2:#0b0f19;--line:#334155;--text:#f8fafc;--muted:#9ca3af;--blue:#38bdf8;--purple:#a855f7}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:var(--vscode-font-family);font-size:13px}.app{min-height:100vh}.hero{padding:16px 13px;border-bottom:1px solid var(--line);background:linear-gradient(135deg,rgba(56,189,248,.14),rgba(168,85,247,.16))}.brand{display:flex;gap:10px;align-items:center}.brand img{width:44px;height:44px;border-radius:8px}h1{margin:0;font-size:19px}.muted,small{color:var(--muted)}.status{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:12px}.tile,.panel{border:1px solid var(--line);background:var(--panel);border-radius:8px;padding:10px}.tile b{display:block}.tile span{font-size:10px;color:var(--muted);text-transform:uppercase}.content{padding:10px}.panel{margin-bottom:8px}.grid{display:grid;gap:7px}.action,.open{border:1px solid var(--line);background:var(--panel2);color:var(--text);border-radius:7px;padding:9px;cursor:pointer;width:100%}.action{text-align:left}.action span{display:block;font-weight:700}.action.primary{border-color:var(--purple);background:rgba(168,85,247,.22)}.open{margin-top:10px;border-color:var(--blue);background:linear-gradient(135deg,rgba(56,189,248,.2),rgba(168,85,247,.28));font-weight:800}</style></head><body><div class="app"><header class="hero"><div class="brand"><img src="${iconUri}" alt="Sergeant"><div><h1>Sergeant</h1><div class="muted">Model-free engineering review</div></div></div><div class="status"><div class="tile"><b id="statusText">Standing By</b><span>Status</span></div><div class="tile"><b id="lastText">No report</b><span>Last verdict</span></div></div><button class="open" id="openFull">Open Review Center</button></header><main class="content"><section class="panel"><b>Review</b><p class="muted">Choose a focused review. Optional model reasoning stays disabled unless you enable it in advanced settings.</p><div class="grid">${actionButtons}</div></section><section class="panel"><b>Last report</b><p class="muted" id="reportTitle">No report yet.</p><button class="action" id="openLast"><span>Open Last Report</span><small>Inspect evidence and verdict</small></button></section></main></div><script>const vscode=acquireVsCodeApi();document.querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>vscode.postMessage({type:'run',action:b.dataset.run}));document.getElementById('openFull').onclick=()=>vscode.postMessage({type:'openFull'});document.getElementById('openLast').onclick=()=>vscode.postMessage({type:'openLast'});window.addEventListener('message',event=>{const m=event.data;if(!['state','sergeantState'].includes(m.type))return;const s=m.state||{};document.getElementById('statusText').textContent=s.running?'Running':(s.status||'Standing By');document.getElementById('lastText').textContent=s.last?s.last.summary.verdict:'No report';document.getElementById('reportTitle').textContent=s.last?(s.last.title+': '+s.last.summary.verdict):'No report yet.';});vscode.postMessage({type:'ready'});</script></body></html>`;
  }

  renderFull() {
    const resourceRoot = path.join(this.context.extensionPath, "resources");
    const html = fs.readFileSync(path.join(resourceRoot, "sergeant-command-center-v2.html"), "utf8");
    const css = fs.readFileSync(path.join(resourceRoot, "sergeant-command-center-v2.css"), "utf8");
    const responsiveCss = fs.readFileSync(path.join(resourceRoot, "sergeant-command-center-v2-responsive.css"), "utf8");
    const script = fs.readFileSync(path.join(resourceRoot, "sergeant-command-center-v2.js"), "utf8");
    const bootstrap = `<script>const __sergeantVsCode=acquireVsCodeApi();window.sergeantHostSend=(payload)=>{const value=typeof payload==='string'?JSON.parse(payload):payload;__sergeantVsCode.postMessage(value);};</script>`;
    return html
      .replace("/* SERGEANT_CSS */", css)
      .replace("/* SERGEANT_RESPONSIVE_CSS */", responsiveCss)
      .replace("// SERGEANT_JS", script)
      .replace("<!-- SERGEANT_HOST_BOOTSTRAP -->", bootstrap);
  }
}

module.exports = { SergeantCommandCenterProvider, LLM_SETTING_KEYS };
