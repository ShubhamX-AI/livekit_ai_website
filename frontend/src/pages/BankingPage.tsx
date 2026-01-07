import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { LiveKitRoom, RoomAudioRenderer, StartAudio, useVoiceAssistant, useLocalParticipant } from '@livekit/components-react';
import { useChatTranscriptions } from '../hooks/useChatTranscriptions';
import { Track } from 'livekit-client';
import { BankingDashboardUI } from '../components2_bank/banking/BankingDashboardUI';
import { AgentCardUI } from '../components2_bank/banking/AgentCardUI';
import { Bot } from 'lucide-react';
import '../components2_bank/banking/VoiceAgentStyles.css';

const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
const LIVEKIT_URL = import.meta.env?.VITE_LIVEKIT_URL || '';
const TOKEN_ENDPOINT = `${BACKEND_URL}/api/getToken`;

type VisualizerState = 'speaking' | 'listening' | 'connected' | 'disconnected';

function mapAgentToVisualizerState(s: string): VisualizerState {
    if (s === 'connecting') return 'connected';
    if (s === 'speaking' || s === 'listening' || s === 'connected' || s === 'disconnected') return s as VisualizerState;
    return 'connected';
}

// Voice Assistant Component (Only rendered when connected)
const VoiceAssistantOverlay: React.FC<{ onDisconnect: () => void }> = ({ onDisconnect }) => {
    const { state, audioTrack: agentTrack } = useVoiceAssistant();
    const { localParticipant, microphoneTrack } = useLocalParticipant();
    const [isMicMuted, setIsMicMuted] = useState(false);
    const [showChat, setShowChat] = useState(false);
    const messages = useChatTranscriptions();

    // Ensure microphone is enabled on mount
    React.useEffect(() => {
        if (localParticipant) {
            localParticipant.setMicrophoneEnabled(true);
        }
    }, [localParticipant]);

    const userTrackRef = useMemo(() => {
        if (!localParticipant) return undefined;
        return {
            participant: localParticipant,
            source: Track.Source.Microphone,
            publication: microphoneTrack,
        };
    }, [localParticipant, microphoneTrack]);

    const agentTrackRef = useMemo(() => {
        if (!agentTrack || !agentTrack.participant || !agentTrack.publication) return undefined;
        return {
            participant: agentTrack.participant,
            source: Track.Source.Unknown,
            publication: agentTrack.publication,
        };
    }, [agentTrack]);

    const isAgentSpeaking = state === 'speaking';
    const activeTrack = isAgentSpeaking ? agentTrackRef : (!isMicMuted ? userTrackRef : undefined);
    const visualizerState = mapAgentToVisualizerState(state as string);

    return (
        <>
            <div className={`fixed bottom-24 md:bottom-6 right-4 md:right-6 z-50 flex flex-col items-end gap-4 max-w-[calc(100vw-2rem)] transition-all duration-300 ${showChat ? 'w-full md:w-auto h-[80vh] md:h-auto' : ''}`}>
                <AgentCardUI
                    state="active"
                    onClose={onDisconnect}
                    onDisconnect={onDisconnect}
                    onToggleMic={() => {
                        if (!localParticipant) return;
                        const newVal = !isMicMuted;
                        localParticipant.setMicrophoneEnabled(!newVal);
                        setIsMicMuted(newVal);
                    }}
                    isMicMuted={isMicMuted}
                    isAgentSpeaking={isAgentSpeaking}
                    visualizerState={visualizerState}
                    trackRef={activeTrack}
                    showChat={showChat}
                    onToggleChat={() => setShowChat(!showChat)}
                    messages={messages}
                />
            </div>
            <RoomAudioRenderer />
            <StartAudio label="Click to allow audio playback" />
        </>
    );
};

export default function BankingPage() {
    const navigate = useNavigate();
    const [token, setToken] = useState<string>('');
    const [connecting, setConnecting] = useState(false);
    const [isCardOpen, setIsCardOpen] = useState(false);

    const handleConnect = useCallback(async () => {
        setConnecting(true);
        try {
            const userId = `user_${Math.floor(Math.random() * 10000)}`;
            const url = `${TOKEN_ENDPOINT}?name=${userId}&agent=bank`;

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
            alert(`Failed to connect: ${err.message}`);
        } finally {
            setConnecting(false);
        }
    }, []);

    const handleDisconnect = useCallback(() => {
        setToken('');
        setIsCardOpen(false);
    }, []);

    const handleBack = useCallback(() => {
        navigate('/');
    }, [navigate]);

    // ALWAYS render LiveKitRoom to prevent unmounting BankingDashboardUI
    // Only connect when we have a token
    return (
        <LiveKitRoom
            video={false}
            audio={true}
            token={token}
            connect={!!token}  // Only connect when token exists
            serverUrl={LIVEKIT_URL}
            data-lk-theme="default"
            style={{ height: '100vh' }}
            onError={(err) => {
                console.error("LiveKit Error:", err);
                alert(`LiveKit error: ${err.message}`);
                setToken('');
            }}
            onDisconnected={handleDisconnect}
        >
            <BankingDashboardUI onBack={handleBack}>
                {/* Conditionally render overlay or button based on connection state */}
                {token ? (
                    // CONNECTED: Show voice assistant overlay
                    <VoiceAssistantOverlay onDisconnect={handleDisconnect} />
                ) : (
                    // DISCONNECTED: Show "Ask Vyom" button
                    <div className="fixed bottom-24 md:bottom-6 right-4 md:right-6 z-50 flex flex-col items-end gap-4">
                        {/* Agent Card (Open) */}
                        {isCardOpen && (
                            <AgentCardUI
                                state={connecting ? 'connecting' : 'standby'}
                                onClose={() => setIsCardOpen(false)}
                                onConnect={handleConnect}
                            />
                        )}

                        {/* Floating Trigger Button (Closed) */}
                        {!isCardOpen && (
                            <button
                                onClick={() => setIsCardOpen(true)}
                                disabled={connecting}
                                className="pointer-events-auto group relative w-16 h-16 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#bfa03a] shadow-[0_4px_20px_rgba(212,175,55,0.4)] flex items-center justify-center transition-transform hover:scale-110 active:scale-95 disabled:scale-100 disabled:opacity-80"
                            >
                                {/* Tooltip */}
                                <div className="absolute right-full mr-4 bg-[#151f32] text-[#D4AF37] px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none border border-[#D4AF37]/20">
                                    Ask Vyom
                                </div>

                                <div className="relative z-10">
                                    <Bot size={32} className="text-[#0B1426]" />
                                </div>

                                {/* Ping animation */}
                                <div className="absolute inset-0 rounded-full bg-[#D4AF37] opacity-50 animate-ping"></div>
                            </button>
                        )}
                    </div>
                )}
            </BankingDashboardUI>
        </LiveKitRoom>
    );
}
