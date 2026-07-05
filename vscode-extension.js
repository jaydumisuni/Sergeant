const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");

const ACTIONS = [
  {
    label: "Review Workspace",
    description: "Full repository verdict",
    detail: "Runs PASS / NEEDS WORK / BLOCK review on the current workspace.",
    command: "sergeant.reviewWorkspace",
    args: () => ["review", workspaceRoot(), "--pretty"],
    title: "Sergeant workspace review",
  },
  {
    label: "App Bridge Review",
    description: "App contract review",
    detail: "Runs the app-facing Sergeant review contract.",
    command: "sergeant.appReviewWorkspace",
    args: () => ["app-review", workspaceRoot(), "--pretty"],
    title: "Sergeant app bridge review",
  },
  {
    label: "Proof Suite",
    description: "End-to-end proof",
    detail: "Exercises the local proof pipeline without external reviewer dependency.",
    command: "sergeant.proofSuite",
    args: () => ["proof-suite", workspaceRoot(), "--pretty"],
    title: "Sergeant proof suite",
  },
  {
    label: "Final Proof",
    description: "Release gate",
    detail: "Runs final PASS plus verification proof.",
    command: "sergeant.finalProof",
    args: () => ["final-proof", workspaceRoot(), "--pretty"],
    title: "Sergeant final proof",
  },
  {
    label: "Verify Standard",
    description: "Evidence check",
    detail: "Checks required Sergeant verification evidence.",
    command: "sergeant.verifyStandard",
    args: () => ["verify-standard", workspaceRoot(), "--pretty"],
    title: "Sergeant standard verification",
  },
  {
    label: "Battle Tests",
    description: "Benchmark fixtures",
    detail: "Validates public pull-request benchmark fixtures.",
    command: "sergeant.battleTests",
    args: () => ["battle-tests", workspaceRoot(), "--pretty"],
    title: "Sergeant battle tests",
  },
  {
    label: "IDE Contract",
    description: "Integration contract",
    detail: "Shows the VS Code, PyCharm, JetBrains, and AI handoff contract.",
    command: "sergeant.ideBenchContract",
    args: () => ["ide-bench-contract", "--pretty"],
    title: "Sergeant IDE Bench contract",
  },
];

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

class SergeantActionProvider {
  getTreeItem(item) {
    const treeItem = new vscode.TreeItem(item.label, vscode.TreeItemCollapsibleState.None);
    treeItem.description = item.description;
    treeItem.tooltip = item.detail;
    treeItem.command = {
      command: item.command,
      title: item.label,
    };
    treeItem.iconPath = new vscode.ThemeIcon("shield");
    return treeItem;
  }

  getChildren() {
    return ACTIONS;
  }
}

function activate(context) {
  const provider = new SergeantActionProvider();
  context.subscriptions.push(vscode.window.registerTreeDataProvider("sergeant.actions", provider));

  for (const action of ACTIONS) {
    context.subscriptions.push(
      vscode.commands.registerCommand(action.command, () => {
        runSergeant(action.args(), action.title);
      })
    );
  }
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};
