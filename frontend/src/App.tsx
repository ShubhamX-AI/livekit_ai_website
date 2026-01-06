import { useState, useCallback } from 'react';
import { LiveKitRoom, RoomAudioRenderer, StartAudio } from '@livekit/components-react';
import VoiceAssistant from './components4_bank/VoiceAssistant';
// import BankingVoiceAssistant from './components4_bank/BankingVoiceAssistant';
import BankingVoiceAssistant from './components4_bank/BVA';
import { Header } from './components4_bank/Header';
import { AlertCircle, Mic } from 'lucide-react';

// Safely access environment variables with fallback
const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
const LIVEKIT_URL = import.meta.env?.VITE_LIVEKIT_URL || '';
const TOKEN_ENDPOINT = `${BACKEND_URL}/api/getToken`;
console.log("TOKEN_ENDPOINT", TOKEN_ENDPOINT);

export default function App() {
  const [token, setToken] = useState<string>('');
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agent, setAgent] = useState<'web' | 'invoice' | 'restaurant' | 'bank'>('web');

  const connect = useCallback(async (chosenAgent: 'web' | 'invoice' | 'restaurant' | 'bank' = agent) => {
    setConnecting(true);
    setError(null);
    try {
      const userId = `user_${Math.floor(Math.random() * 10000)}`;
      const url = `${TOKEN_ENDPOINT}?name=${userId}&agent=${chosenAgent}`;

      const response = await fetch(url, { mode: 'cors' });
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      
      const accessToken = await response.text();
      
      if (!accessToken || accessToken.trim().length === 0) {
        throw new Error("Received empty token from backend");
      }
      setToken(accessToken);
    } catch (err: any) {
      console.error("Connection failed:", err);
      let msg = "Failed to connect to backend.";
      if (err.message && err.message.includes('Failed to fetch')) {
          msg = `Could not reach server at ${BACKEND_URL}. Ensure your backend is running.`;
      } else if (err.message) {
          msg = err.message;
      }
      setError(msg);
    } finally {
      setConnecting(false);
    }
  }, [agent]);

  if (!token) {
    return (
      <div className="flex flex-col min-h-screen bg-background text-text-main font-sans selection:bg-primary/20">
        <Header status="disconnected"/>

        <main className="flex-1 flex flex-col items-center justify-center p-5 relative overflow-hidden">
          
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />

          <div className="max-w-xl w-full text-center space-y-10 animate-fade-in-up relative z-10">
            
            <div className="space-y-6">
              <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center mx-auto text-primary shadow-[0_8px_30px_rgba(0,0,0,0.06)] border border-border">
                 <Mic size={40} strokeWidth={1.5} />
              </div>
              <div className="space-y-2">
                <h2 className="text-4xl md:text-5xl font-bold text-primary tracking-tight">How can I help you?</h2>
                <p className="text-text-muted text-lg max-w-md mx-auto leading-relaxed">
                  Connect to INT. Intelligence to access real-time voice insights, analysis, and support.
                </p>
              </div>
            </div>

            {error && (
              <div className="max-w-md mx-auto p-4 rounded-xl bg-red-50 border border-red-100 text-red-700 flex items-start gap-3 text-left shadow-sm">
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <p className="text-sm font-medium leading-tight">{error}</p>
              </div>
            )}
            <div className="flex flex-col gap-4 max-w-xs mx-auto">
              <button
                onClick={() => {
                  setAgent('web');
                  connect('web');
                }}
                disabled={connecting}
                className="group relative w-full max-w-xs mx-auto py-4 px-8 bg-primary hover:bg-primary-hover text-white text-lg rounded-full font-semibold transition-all shadow-lg hover:shadow-primary/30 hover:-translate-y-1 flex items-center justify-center gap-3 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
              >
                Indusnet Web Agent
              </button>

              <button
                onClick={() => {
                  setAgent('invoice');
                  connect('invoice');
                }}
                disabled={connecting}
                className="group relative w-full max-w-xs mx-auto py-4 px-8 bg-primary hover:bg-primary-hover text-white text-lg rounded-full font-semibold transition-all shadow-lg hover:shadow-primary/30 hover:-translate-y-1 flex items-center justify-center gap-3 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
              >
                Invoice Agent
              </button>
              
              <button
                onClick={() => {
                  setAgent('restaurant');
                  connect('restaurant');
                }}
                disabled={connecting}
                className="group relative w-full max-w-xs mx-auto py-4 px-8 bg-primary hover:bg-primary-hover text-white text-lg rounded-full font-semibold transition-all shadow-lg hover:shadow-primary/30 hover:-translate-y-1 flex items-center justify-center gap-3 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
              >
                Restaurant Agent
              </button>
              <button
                onClick={() => {
                  setAgent('bank');
                  connect('bank');
                }}
                disabled={connecting}
                className="group relative w-full max-w-xs mx-auto py-4 px-8 bg-primary hover:bg-primary-hover text-white text-lg rounded-full font-semibold transition-all shadow-lg hover:shadow-primary/30 hover:-translate-y-1 flex items-center justify-center gap-3 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
              >
                Banking Agent
              </button>
            </div>

            <div className="pt-8 flex justify-center gap-6 text-sm text-text-muted opacity-70">
              <span className="flex items-center gap-1">Secure Connection</span>
              <span>•</span>
              <span className="flex items-center gap-1">Real-time Audio</span>
            </div>

          </div>
        </main>
      </div>
    );
  }

  return (
    <LiveKitRoom
      video={false}
      audio={true}
      token={token}
      serverUrl={LIVEKIT_URL}
      data-lk-theme="default"
      style={{ height: '100vh', backgroundColor: '#f8f9fa' }}
      onError={(err) => {
        console.error("LiveKit Error:", err);
        setError(err.message);
        setToken('');
      }}
      onDisconnected={() => {
        setToken('');
      }}
    >
      {/* <VoiceAssistant /> */}
      {agent === 'bank' ? <BankingVoiceAssistant /> : <VoiceAssistant />}
      <RoomAudioRenderer />
      <StartAudio label="Click to allow audio playback" />
    </LiveKitRoom>
  );
}