const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");

function pythonPath() {
  return vscode.workspace.getConfiguration("sergeant").get("pythonPath") || "python";
}

function workspaceRoot() {
  const folders = vscode.workspace.workspaceFolders;
  if (folders && folders.length > 0) {
    return folders[0].uri.fsPath;
  }
  return process.cwd();
}

function runSergeant(args, title) {
  const output = vscode.window.createOutputChannel("Sergeant");
  output.show(true);
  output.clear();
  output.appendLine(`$ ${pythonPath()} sergeant.py ${args.join(" ")}`);

  const script = path.join(__dirname, "sergeant.py");
  const child = cp.spawn(pythonPath(), [script, ...args], {
    cwd: workspaceRoot(),
    shell: false,
  });

  child.stdout.on("data", (data) => output.append(data.toString()));
  child.stderr.on("data", (data) => output.append(data.toString()));
  child.on("error", (error) => {
    vscode.window.showErrorMessage(`${title} failed: ${error.message}`);
  });
  child.on("close", (code) => {
    if (code === 0) {
      vscode.window.showInformationMessage(`${title} completed.`);
    } else {
      vscode.window.showErrorMessage(`${title} exited with code ${code}. See Sergeant output.`);
    }
  });
}

class SergeantViewProvider {
  resolveWebviewView(webviewView) {
    webviewView.webview.options = {
      enableScripts: true,
    };
    webviewView.webview.html = dashboardHtml();
    webviewView.webview.onDidReceiveMessage((message) => {
      if (message && typeof message.command === "string") {
        vscode.commands.executeCommand(message.command);
      }
    });
  }
}

function dashboardHtml() {
  const actions = [
    ["Review Workspace", "Full repository review with PASS / NEEDS WORK / BLOCK verdict.", "sergeant.reviewWorkspace"],
    ["App Bridge Review", "Run the app-facing review contract against this workspace.", "sergeant.appReviewWorkspace"],
    ["Proof Suite", "Exercise the local end-to-end proof pipeline.", "sergeant.proofSuite"],
    ["Final Proof", "Run the final PASS plus verification proof gate.", "sergeant.finalProof"],
    ["Verify Standard", "Check required Sergeant verification evidence.", "sergeant.verifyStandard"],
    ["Battle Tests", "Validate public pull-request benchmark fixtures.", "sergeant.battleTests"],
    ["IDE Contract", "Show the VS Code, PyCharm, JetBrains, and AI handoff contract.", "sergeant.ideBenchContract"],
  ];
  const cards = actions.map(([title, description, command]) => `
    <button class="action" data-command="${command}">
      <span class="title">${title}</span>
      <span class="description">${description}</span>
    </button>
  `).join("");

  return `<!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {
          padding: 14px;
          color: var(--vscode-foreground);
          font-family: var(--vscode-font-family);
        }
        .brand {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 14px;
        }
        .mark {
          width: 34px;
          height: 34px;
          border: 1px solid var(--vscode-focusBorder);
          border-radius: 6px;
          display: grid;
          place-items: center;
          font-weight: 700;
          color: var(--vscode-textLink-foreground);
        }
        h2 {
          margin: 0;
          font-size: 15px;
          line-height: 1.2;
        }
        .sub {
          margin: 2px 0 0;
          color: var(--vscode-descriptionForeground);
          font-size: 12px;
        }
        .section {
          margin: 16px 0 8px;
          font-size: 11px;
          color: var(--vscode-descriptionForeground);
          text-transform: uppercase;
          letter-spacing: 0;
        }
        .action {
          width: 100%;
          margin: 0 0 8px;
          padding: 10px;
          text-align: left;
          border: 1px solid var(--vscode-panel-border);
          border-radius: 6px;
          color: var(--vscode-button-secondaryForeground);
          background: var(--vscode-button-secondaryBackground);
          cursor: pointer;
        }
        .action:hover {
          background: var(--vscode-button-secondaryHoverBackground);
        }
        .title {
          display: block;
          font-size: 13px;
          font-weight: 600;
          margin-bottom: 4px;
        }
        .description {
          display: block;
          font-size: 12px;
          line-height: 1.35;
          color: var(--vscode-descriptionForeground);
        }
      </style>
    </head>
    <body>
      <div class="brand">
        <div class="mark">SGT</div>
        <div>
          <h2>Sergeant</h2>
          <p class="sub">Evidence-first engineering review.</p>
        </div>
      </div>
      <div class="section">Review</div>
      ${cards}
      <script>
        const vscode = acquireVsCodeApi();
        document.querySelectorAll("[data-command]").forEach((button) => {
          button.addEventListener("click", () => {
            vscode.postMessage({ command: button.dataset.command });
          });
        });
      </script>
    </body>
    </html>`;
}

function activate(context) {
  const provider = new SergeantViewProvider();
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("sergeant.actions", provider),
    vscode.commands.registerCommand("sergeant.reviewWorkspace", () => {
      runSergeant(["review", workspaceRoot(), "--pretty"], "Sergeant workspace review");
    }),
    vscode.commands.registerCommand("sergeant.appReviewWorkspace", () => {
      runSergeant(["app-review", workspaceRoot(), "--pretty"], "Sergeant app bridge review");
    }),
    vscode.commands.registerCommand("sergeant.proofSuite", () => {
      runSergeant(["proof-suite", workspaceRoot(), "--pretty"], "Sergeant proof suite");
    }),
    vscode.commands.registerCommand("sergeant.finalProof", () => {
      runSergeant(["final-proof", workspaceRoot(), "--pretty"], "Sergeant final proof");
    }),
    vscode.commands.registerCommand("sergeant.verifyStandard", () => {
      runSergeant(["verify-standard", workspaceRoot(), "--pretty"], "Sergeant standard verification");
    }),
    vscode.commands.registerCommand("sergeant.battleTests", () => {
      runSergeant(["battle-tests", workspaceRoot(), "--pretty"], "Sergeant battle tests");
    }),
    vscode.commands.registerCommand("sergeant.ideBenchContract", () => {
      runSergeant(["ide-bench-contract", "--pretty"], "Sergeant IDE Bench contract");
    })
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
