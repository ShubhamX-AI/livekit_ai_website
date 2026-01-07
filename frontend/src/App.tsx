import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import BankingPage from './pages/BankingPage';
import { LiveKitRoom, RoomAudioRenderer, StartAudio } from '@livekit/components-react';
import VoiceAssistant from './components4_bank/VoiceAssistant';
import { useEffect, useState } from 'react';

// Safely access environment variables with fallback
const LIVEKIT_URL = import.meta.env?.VITE_LIVEKIT_URL || '';

// Legacy agent component wrapper (for web/invoice/restaurant agents)
function LegacyAgentPage({ agentType }: { agentType: 'web' | 'invoice' | 'restaurant' | 'translation' }) {
  const [token, setToken] = useState<string>('');

  useEffect(() => {
    // Check sessionStorage for token
    const storedToken = sessionStorage.getItem('livekit_token');
    const storedAgent = sessionStorage.getItem('agent_type');

    if (storedToken && storedAgent === agentType) {
      setToken(storedToken);
    }
  }, [agentType]);

  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p>Loading...</p>
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
        alert(err.message);
        setToken('');
        sessionStorage.removeItem('livekit_token');
        sessionStorage.removeItem('agent_type');
      }}
      onDisconnected={() => {
        setToken('');
        sessionStorage.removeItem('livekit_token');
        sessionStorage.removeItem('agent_type');
        window.location.href = '/';
      }}
    >
      <VoiceAssistant />
      <RoomAudioRenderer />
      <StartAudio label="Click to allow audio playback" />
    </LiveKitRoom>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/bank" element={<BankingPage />} />
      <Route path="/web" element={<LegacyAgentPage agentType="web" />} />
      <Route path="/invoice" element={<LegacyAgentPage agentType="invoice" />} />
      <Route path="/restaurant" element={<LegacyAgentPage agentType="restaurant" />} />
      <Route path="/translation" element={<LegacyAgentPage agentType="translation" />} />
    </Routes>
  );
}