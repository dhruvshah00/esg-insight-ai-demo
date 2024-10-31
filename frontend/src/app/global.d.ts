export {};

declare global {
  interface Window {
    socket: WebSocket;
  }
}