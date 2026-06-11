/** WebSocket client for real-time task progress from backend.

Usage:
  import { useWebSocket } from '@/api/websocket'
  const ws = useWebSocket()
  ws.on('transfer.progress', (data) => { ... })
  // onUnmounted(() => ws.disconnect())
 */

type WsCallback = (data: any) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private handlers = new Map<string, Set<WsCallback>>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private url: string = ''
  private shouldReconnect = true

  /** Connect to the WebSocket endpoint. Auto-reconnects on close. */
  connect(url?: string) {
    this.url = url || `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`
    this.shouldReconnect = true
    this._connect()
  }

  private _connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          const eventName = msg.event || 'message'
          const data = msg.data || msg
          this._emit(eventName, data)
        } catch {
          this._emit('message', event.data)
        }
      }

      this.ws.onclose = () => {
        this._emit('disconnected', {})
        // Auto-reconnect after 3 seconds
        if (this.shouldReconnect) {
          this.reconnectTimer = setTimeout(() => this._connect(), 3000)
        }
      }

      this.ws.onerror = () => {
        // onclose will fire after onerror, so reconnect is handled there
      }

      this.ws.onopen = () => {
        this._emit('connected', {})
      }
    } catch {
      // Connection failed, retry
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => this._connect(), 5000)
      }
    }
  }

  /** Disconnect and stop reconnecting. */
  disconnect() {
    this.shouldReconnect = false
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /** Register an event handler. */
  on(event: string, callback: WsCallback) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set())
    }
    this.handlers.get(event)!.add(callback)
    return () => this.off(event, callback)
  }

  /** Remove an event handler. */
  off(event: string, callback: WsCallback) {
    this.handlers.get(event)?.delete(callback)
  }

  private _emit(event: string, data: any) {
    this.handlers.get(event)?.forEach((cb) => {
      try { cb(data) } catch { /* ignore handler error */ }
    })
    // Also emit to wildcard 'all'
    this.handlers.get('all')?.forEach((cb) => {
      try { cb({ event, data }) } catch { /* ignore */ }
    })
  }
}

let _instance: WebSocketClient | null = null

/** Get or create the singleton WebSocket client. */
export function useWebSocket(): WebSocketClient {
  if (!_instance) {
    _instance = new WebSocketClient()
  }
  return _instance
}

/** Get a WebSocket client for task status updates (SPEC /ws/task/status). */
export function useTaskWebSocket(): WebSocketClient {
  const client = new WebSocketClient()
  client.connect(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/task/status`)
  return client
}

/** Get a WebSocket client for real-time log streaming (SPEC /ws/log/realtime). */
export function useLogWebSocket(): WebSocketClient {
  const client = new WebSocketClient()
  client.connect(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/log/realtime`)
  return client
}
