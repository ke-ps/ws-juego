import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { ClientMessage, ServerMessage } from '../core/websocket.types';

@Injectable({
  providedIn: 'root',
})
export class WebsocketService {
  private readonly WS_URL = 'ws://localhost:8000/ws/pvp';
  private socket: WebSocket | null = null;

  private readonly messages$ = new Subject<ServerMessage>();
  private readonly connectionStatus$ = new Subject<boolean>();

  connect(): void {
    if (this.socket) return;

    console.log(`[WS] 🔌 Conectando a ${this.WS_URL}...`);

    this.socket = new WebSocket(this.WS_URL);

    this.socket.onopen = () => {
      console.log('[WS] ✅ Conectado');
      this.connectionStatus$.next(true);
    };

    this.socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as ServerMessage;
        console.log(`[WS] 📨 [${msg.type}]`, msg);
        this.messages$.next(msg);
      } catch (err) {
        console.error('[WS] ❌ Error parseando mensaje', err);
      }
    };

    this.socket.onclose = (event) => {
      console.log(
        `[WS] 🔌 Desconectado (code: ${event.code}, reason: ${event.reason || 'none'})`
      );
      this.socket = null;
      this.connectionStatus$.next(false);
    };

    this.socket.onerror = () => {
      console.error('[WS] ❌ Error WebSocket');
      this.connectionStatus$.next(false);
    };
  }

  send(message: ClientMessage): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
      console.log('[WS] 📤', message);
    }
  }

  messages(): Observable<ServerMessage> {
    return this.messages$.asObservable(); // 👈 FIX
  }

  connectionStatus(): Observable<boolean> {
    return this.connectionStatus$.asObservable();
  }

  disconnect(): void {
    this.socket?.close();
    this.socket = null;
  }
}