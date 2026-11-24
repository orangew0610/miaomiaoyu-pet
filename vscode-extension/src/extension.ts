import * as fs from "fs";
import * as net from "net";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

type Endpoint = { version: number; host: string; port: number; token: string };
type DiagnosticPayload = {
  uri: string; version: number; severity: number; message: string;
  line: number; character: number; end_line: number; end_character: number;
  removed: boolean; active: boolean; visible: boolean; locate: boolean;
  document_name: string; code?: string;
};

const diagnosticsDecoration = vscode.window.createTextEditorDecorationType({
  backgroundColor: new vscode.ThemeColor("editor.findMatchHighlightBackground"),
  overviewRulerColor: new vscode.ThemeColor("editorError.foreground"),
  overviewRulerLane: vscode.OverviewRulerLane.Right,
});
const locatorDecoration = vscode.window.createTextEditorDecorationType({
  border: "2px solid #ff00fe",
  backgroundColor: "#ff00fe30",
  borderRadius: "2px",
});
const previous = new Map<string, Map<string, DiagnosticPayload>>();
const output = vscode.window.createOutputChannel("DebugPet");

function endpointPath(): string {
  const appData = process.env.APPDATA ?? path.join(os.homedir(), "AppData", "Roaming");
  return path.join(appData, "DebugPet", "ipc.json");
}

function identity(item: DiagnosticPayload): string {
  return [item.uri, item.severity, item.message, item.line, item.character,
    item.end_line, item.end_character].join("|");
}

function severityLimit(): number {
  const value = vscode.workspace.getConfiguration("debugpet").get<string>("minimumSeverity", "warning");
  return { error: 1, warning: 2, information: 3, hint: 4 }[value] ?? 2;
}

function stateChanged(oldItem: DiagnosticPayload, newItem: DiagnosticPayload): boolean {
  return oldItem.version !== newItem.version || oldItem.active !== newItem.active ||
    oldItem.visible !== newItem.visible || oldItem.locate !== newItem.locate;
}

class Transport implements vscode.Disposable {
  private pending = new Map<string, DiagnosticPayload>();
  private busy = false;
  private retryMilliseconds = 500;
  private endpointSignature = "";
  private watcher: NodeJS.Timeout;
  constructor(private readonly resync: () => void) {
    this.watcher = setInterval(() => void this.checkEndpoint(), 1000);
    void this.checkEndpoint();
  }
  dispose(): void { clearInterval(this.watcher); }

  enqueue(payload: DiagnosticPayload): void {
    const key = identity(payload);
    if (payload.removed) {
      this.pending.delete(key);
      this.pending.set(key + "|removed", payload);
    } else {
      this.pending.set(key, payload);
    }
    void this.pump();
  }

  private async readEndpoint(): Promise<Endpoint | undefined> {
    try {
      const value = await fs.promises.readFile(endpointPath(), "utf8");
      const endpoint = JSON.parse(value) as Endpoint;
      if (endpoint.version !== 1 || !endpoint.token || !endpoint.port) { return undefined; }
      return endpoint;
    } catch { return undefined; }
  }

  private async checkEndpoint(): Promise<void> {
    const endpoint = await this.readEndpoint();
    const signature = endpoint ? `${endpoint.host}:${endpoint.port}:${endpoint.token}` : "";
    if (signature && signature !== this.endpointSignature) {
      this.endpointSignature = signature;
      output.appendLine(`connected endpoint discovered at ${endpoint?.host}:${endpoint?.port}`);
      this.resync();
    }
    void this.pump();
  }

  private deliver(endpoint: Endpoint, payload: DiagnosticPayload): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = net.createConnection({ host: endpoint.host, port: endpoint.port });
      let settled = false;
      const finish = (ok: boolean) => {
        if (settled) { return; }
        settled = true;
        socket.destroy();
        resolve(ok);
      };
      socket.setTimeout(1800, () => finish(false));
      socket.on("connect", () => socket.write(JSON.stringify({
        version: 1, token: endpoint.token, type: "diagnostic", payload,
      }) + "\n"));
      socket.on("data", (data) => finish(data.toString("utf8").includes('"ok":true')));
      socket.on("error", () => finish(false));
      socket.on("close", () => finish(false));
    });
  }

  private async pump(): Promise<void> {
    if (this.busy || this.pending.size === 0) { return; }
    this.busy = true;
    const endpoint = await this.readEndpoint();
    if (!endpoint) {
      this.busy = false;
      setTimeout(() => void this.pump(), this.retryMilliseconds);
      this.retryMilliseconds = Math.min(5000, this.retryMilliseconds * 2);
      return;
    }
    const first = this.pending.entries().next().value as [string, DiagnosticPayload] | undefined;
    if (!first) { this.busy = false; return; }
    const [key, payload] = first;
    const delivered = await this.deliver(endpoint, payload);
    if (delivered) {
      this.pending.delete(key);
      this.retryMilliseconds = 500;
      output.appendLine(
        `delivered ${payload.removed ? "removed" : "diagnostic"} ` +
        `${payload.uri}:${payload.line + 1}:${payload.character + 1} ` +
        `active=${payload.active} visible=${payload.visible} locate=${payload.locate}`
      );
    } else {
      output.appendLine("delivery failed; queued for retry");
      this.retryMilliseconds = Math.min(5000, this.retryMilliseconds * 2);
    }
    this.busy = false;
    setTimeout(() => void this.pump(), delivered ? 0 : this.retryMilliseconds);
  }
}

let transport: Transport;
let lastActiveUri: vscode.Uri | undefined;

function rangeVisible(editor: vscode.TextEditor, range: vscode.Range): boolean {
  return editor.visibleRanges.some((visibleRange) => visibleRange.intersection(range) !== undefined);
}

function updateDiagnostics(uri: vscode.Uri, diagnostics: readonly vscode.Diagnostic[], forceState = false): void {
  const document = vscode.workspace.textDocuments.find((item) => item.uri.toString() === uri.toString());
  const editor = vscode.window.visibleTextEditors.find((item) => item.document.uri.toString() === uri.toString());
  const active = vscode.window.activeTextEditor?.document.uri.toString() === uri.toString();
  const version = document?.version ?? 0;
  const shareCode = vscode.workspace.getConfiguration("debugpet").get<boolean>("shareCode", false);
  const current = new Map<string, DiagnosticPayload>();
  const old = previous.get(uri.toString()) ?? new Map<string, DiagnosticPayload>();
  const accepted = diagnostics.filter((item) => item.severity + 1 <= severityLimit());
  const locateDiagnostic = active && editor
    ? accepted.find((item) => rangeVisible(editor, item.range))
    : undefined;

  if (editor) {
    editor.setDecorations(diagnosticsDecoration, accepted.map((item) => item.range));
    editor.setDecorations(locatorDecoration, locateDiagnostic ? [locateDiagnostic.range] : []);
  }

  for (const diagnostic of accepted) {
    const visible = Boolean(editor && rangeVisible(editor, diagnostic.range));
    const payload: DiagnosticPayload = {
      uri: uri.toString(), version, severity: diagnostic.severity + 1,
      message: diagnostic.message, line: diagnostic.range.start.line,
      character: diagnostic.range.start.character, end_line: diagnostic.range.end.line,
      end_character: diagnostic.range.end.character, removed: false, active, visible,
      locate: diagnostic === locateDiagnostic, document_name: path.basename(uri.fsPath),
    };
    if (shareCode && document) { payload.code = document.getText(diagnostic.range); }
    const key = identity(payload);
    current.set(key, payload);
    if (!old.has(key) || forceState || stateChanged(old.get(key)!, payload)) {
      if (payload.locate) { setTimeout(() => transport.enqueue(payload), 180); }
      else { transport.enqueue(payload); }
    }
  }
  for (const [key, payload] of old) {
    if (!current.has(key)) {
      transport.enqueue({ ...payload, version, removed: true, locate: false, code: undefined });
    }
  }
  previous.set(uri.toString(), current);
}

function refreshVisibleEditors(): void {
  for (const editor of vscode.window.visibleTextEditors) {
    updateDiagnostics(editor.document.uri, vscode.languages.getDiagnostics(editor.document.uri), true);
  }
}

function resyncAll(): void {
  for (const [uri, diagnostics] of vscode.languages.getDiagnostics()) {
    updateDiagnostics(uri, diagnostics, true);
  }
}

export function activate(context: vscode.ExtensionContext): void {
  transport = new Transport(resyncAll);
  lastActiveUri = vscode.window.activeTextEditor?.document.uri;
  context.subscriptions.push(transport, output, diagnosticsDecoration, locatorDecoration);
  context.subscriptions.push(vscode.languages.onDidChangeDiagnostics((event) => {
    for (const uri of event.uris) { updateDiagnostics(uri, vscode.languages.getDiagnostics(uri)); }
  }));
  context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor((editor) => {
    const previousUri = lastActiveUri;
    lastActiveUri = editor?.document.uri;
    if (previousUri) {
      updateDiagnostics(previousUri, vscode.languages.getDiagnostics(previousUri), true);
    }
    if (editor) {
      updateDiagnostics(editor.document.uri, vscode.languages.getDiagnostics(editor.document.uri), true);
    }
  }));
  context.subscriptions.push(vscode.window.onDidChangeTextEditorVisibleRanges(() => refreshVisibleEditors()));
  context.subscriptions.push(vscode.window.onDidChangeWindowState((state) => {
    if (state.focused) { refreshVisibleEditors(); }
  }));
  resyncAll();
}

export function deactivate(): void {
  diagnosticsDecoration.dispose();
  locatorDecoration.dispose();
}
