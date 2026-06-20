import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { ClientMessage, Difficulty, ServerMessage } from '../core/websocket.types';
import { WS_URL as ENV_WS_URL } from '../../environments/environment';

const WS_HOST = ENV_WS_URL.replace('/ws/pvp', '');

@Injectable({
  providedIn: 'root',
})
export class WebsocketService {
  private socket: WebSocket | null = null;

  private readonly messages$ = new Subject<ServerMessage>();
  private readonly connectionStatus$ = new Subject<boolean>();

  connect(mode: 'pvp' | 'pve' = 'pvp', difficulty?: Difficulty): void {
    if (this.socket) return;

    let url = `${WS_HOST}/ws/${mode}`;
    if (mode === 'pve' && difficulty) {
      url += `?difficulty=${difficulty}`;
    }

    console.log(`[WS] Conectando a ${url}...`);

    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log('[WS] Conectado');
      this.connectionStatus$.next(true);
    };

    this.socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as ServerMessage;
        console.log(`[WS] [${msg.type}]`, msg);
        this.messages$.next(msg);
      } catch (err) {
        console.error('[WS] Error parseando mensaje', err);
      }
    };

    this.socket.onclose = () => {
      console.log('[WS] Desconectado');
      this.socket = null;
      this.connectionStatus$.next(false);
    };

    this.socket.onerror = () => {
      console.error('[WS] Error WebSocket');
      this.connectionStatus$.next(false);
    };
  }

  send(message: ClientMessage): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
      console.log('[WS]', message);
    }
  }

  messages(): Observable<ServerMessage> {
    return this.messages$.asObservable();
  }

  connectionStatus(): Observable<boolean> {
    return this.connectionStatus$.asObservable();
  }

  disconnect(): void {
    this.socket?.close();
    this.socket = null;
  }
}
