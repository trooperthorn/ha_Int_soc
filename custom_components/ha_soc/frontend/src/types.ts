/**
 * Minimal subset of Home Assistant's frontend `HomeAssistant` interface —
 * just enough surface for this panel (callWS + connection.subscribeMessage).
 * There is no officially published typed package for custom-panel authors,
 * so integrations either vendor a full copy of frontend's types.ts (Alarmo's
 * approach) or, like here, declare only what they actually touch.
 */
export interface Connection {
  subscribeMessage<T>(
    callback: (result: T) => void,
    message: Record<string, unknown>
  ): Promise<() => Promise<void>>;
}

export interface HomeAssistant {
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  connection: Connection;
  themes?: { darkMode?: boolean };
  language?: string;
  user?: { is_admin?: boolean; name?: string };
}

export interface PanelInfo {
  config?: Record<string, unknown>;
  url_path: string;
}
