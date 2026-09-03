/** Minimal subset of Home Assistant's frontend `HomeAssistant` interface: callWS and connection.subscribeMessage. */
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
