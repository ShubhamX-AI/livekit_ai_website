import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import BankingPage from './pages/BankingPage';
import InvoicePage from './pages/InvoicePage';
import JharkhandPage from './pages/JharkhandPage';
import { LiveKitRoom, RoomAudioRenderer, StartAudio } from '@livekit/components-react';
import VoiceAssistant from './components2_bank/VoiceAssistant';
import { LockScreen } from './components2_bank/LockScreen';
import { useEffect, useState } from 'react';
import type { AgentType } from './types/agent';

// Safely access environment variables with fallback
const LIVEKIT_URL = import.meta.env?.VITE_LIVEKIT_URL || '';

// Legacy agent component wrapper (for web/invoice/restaurant agents)
function LegacyAgentPage({ agentType }: { agentType: AgentType }) {
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

import BandhanBankingPage from './pages/BandhanBankingPage';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  useEffect(() => {
    // Check if user is already authenticated
    const authStatus = sessionStorage.getItem('authenticated');
    if (authStatus === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleUnlock = () => {
    setIsAuthenticated(true);
  };

  // Show lock screen if not authenticated
  if (!isAuthenticated) {
    return <LockScreen onUnlock={handleUnlock} />;
  }

  // Show main application routes once authenticated
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/bank" element={<BankingPage />} />
      <Route path="/jharkhand" element={<JharkhandPage />} />
      <Route path="/invoice" element={<InvoicePage />} />
      <Route path="/restaurant" element={<LegacyAgentPage agentType="restaurant" />} />
      <Route path="/realestate" element={<LegacyAgentPage agentType="realestate" />} />
      <Route path="/distributor" element={<LegacyAgentPage agentType="distributor" />} />
      <Route path="/bandhan_banking" element={<BandhanBankingPage />} />
    </Routes>
  );
}
