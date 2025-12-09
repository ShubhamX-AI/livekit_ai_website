export interface TranscriptionMessage {
  id: string;
  text: string;
  sender: 'agent' | 'user';
  timestamp: number;
  isFinal?: boolean;
}

export type AppState =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'ERROR';