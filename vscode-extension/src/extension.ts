import * as fs from "fs";
import * as net from "net";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

type Endpoint = { version: number; host: string; port: number; token: string };

const decoration = vscode.window.createTextEditorDecorationType({
  backgroundColor: new vscode.ThemeColor("editor.findMatchHighlightBackground"),
  overviewRulerColor: new vscode.ThemeColor("editorError.foreground"),
  overviewRulerLane: vscode.OverviewRulerLane.Right,
});

const previous = new Map<string, Map<string, DiagnosticPayload>>();

type DiagnosticPayload = {
  uri: string;
  version: number;
  severity: number;
  message: string;
  line: number;
  character: number;
  end_line: number;
  end_character: number;
  removed: boolean;
  code?: string;
};

function endpointPath(): string {
  const appData = process.env.APPDATA ?? path.join(os.homedir(), "AppData", "Roaming");
  return path.join(appData, "DebugPet", "ipc.json");
}

function identity(item: DiagnosticPayload): string {
  return [item.severity, item.message, item.line, item.character, item.end_line, item.end_character].join("|");
}

function severityLimit(): number {
  const value = vscode.workspace.getConfiguration("debugpet").get<string>("minimumSeverity", "warning");
  return { error: 1, warning: 2, information: 3, hint: 4 }[value] ?? 2;
}

function send(payload: DiagnosticPayload): void {
  fs.readFile(endpointPath(), "utf8", (error, value) => {
    if (error) { return; }
    let endpoint: Endpoint;
    try { endpoint = JSON.parse(value) as Endpoint; } catch { return; }
    const socket = net.createConnection({ host: endpoint.host, port: endpoint.port }, () => {
      socket.end(JSON.stringify({ version: 1, token: endpoint.token, type: "diagnostic", payload }) + "\n");
    });
    socket.setTimeout(1500, () => socket.destroy());
    socket.on("error", () => socket.destroy());
  });
}

function updateDiagnostics(uri: vscode.Uri, diagnostics: readonly vscode.Diagnostic[]): void {
  const document = vscode.workspace.textDocuments.find((item) => item.uri.toString() === uri.toString());
  const version = document?.version ?? 0;
  const shareCode = vscode.workspace.getConfiguration("debugpet").get<boolean>("shareCode", false);
  const current = new Map<string, DiagnosticPayload>();
  const old = previous.get(uri.toString()) ?? new Map<string, DiagnosticPayload>();

  for (const diagnostic of diagnostics) {
    const severity = diagnostic.severity + 1;
    if (severity > severityLimit()) { continue; }
    const payload: DiagnosticPayload = {
      uri: uri.toString(), version, severity, message: diagnostic.message,
      line: diagnostic.range.start.line, character: diagnostic.range.start.character,
      end_line: diagnostic.range.end.line, end_character: diagnostic.range.end.character,
      removed: false,
    };
    if (shareCode && document) { payload.code = document.getText(diagnostic.range); }
    const key = identity(payload);
    current.set(key, payload);
    if (!old.has(key)) { send(payload); }
  }

  for (const [key, payload] of old) {
    if (!current.has(key)) { send({ ...payload, version, removed: true, code: undefined }); }
  }
  previous.set(uri.toString(), current);

  const active = vscode.window.activeTextEditor;
  if (active?.document.uri.toString() === uri.toString()) {
    active.setDecorations(decoration, diagnostics
      .filter((item) => item.severity + 1 <= severityLimit())
      .map((item) => item.range));
  }
}

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(decoration);
  context.subscriptions.push(vscode.languages.onDidChangeDiagnostics((event) => {
    for (const uri of event.uris) { updateDiagnostics(uri, vscode.languages.getDiagnostics(uri)); }
  }));
  for (const [uri, diagnostics] of vscode.languages.getDiagnostics()) { updateDiagnostics(uri, diagnostics); }
}

export function deactivate(): void { decoration.dispose(); }
