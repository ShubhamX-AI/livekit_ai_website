import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { LiveKitRoom, RoomAudioRenderer, StartAudio, useVoiceAssistant, useLocalParticipant } from '@livekit/components-react';
import { useChatTranscriptions } from '../hooks/useChatTranscriptions';
import { Track } from 'livekit-client';
import { OutboundCallModal } from '../components2_bank/OutboundCallModal';
import { VisualizerSection } from '../components2_bank/Visualizer';
import { ChatList } from '../components2_bank/Chatlist';
import {
    Bot,
    Phone,
    Globe,
    ArrowLeft,
    MessageSquare,
    Mic,
    MicOff,
    PhoneOff,
    Loader2
} from 'lucide-react';

// --- Configuration ---
const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
const LIVEKIT_URL = import.meta.env?.VITE_LIVEKIT_URL || '';
const TOKEN_ENDPOINT = `${BACKEND_URL}/api/getToken`;

// --- Helper Functions ---
type VisualizerState = 'speaking' | 'listening' | 'connected' | 'disconnected';

function mapAgentToVisualizerState(s: string): VisualizerState {
    if (s === 'connecting') return 'connected';
    if (s === 'speaking' || s === 'listening' || s === 'connected' || s === 'disconnected') return s as VisualizerState;
    return 'connected';
}

// --- Component: Hirebot Web Layout ---
const HirebotWebLayout: React.FC<{ children?: React.ReactNode; onBack?: () => void }> = ({ children, onBack }) => {
    return (
        <div className="h-screen w-full bg-[#0F172A] text-white font-sans flex flex-col relative overflow-hidden">
            {/* Header */}
            <header className="flex-none bg-[#1E293B] border-b border-white/10 px-6 py-4 flex items-center justify-between z-20">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onBack}
                        className="p-2 hover:bg-white/10 rounded-full transition-colors text-slate-400 hover:text-white"
                        title="Back"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 border border-indigo-500/30">
                            <Bot size={24} />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white leading-none">Hirebot Assistant</h2>
                            <p className="text-[10px] text-indigo-400 tracking-wider font-semibold uppercase mt-0.5">Live Session</p>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                        <span className="text-[10px] font-bold text-emerald-500">SECURE CONNECTION</span>
                    </div>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col min-h-0">
                {children}
            </main>
        </div>
    );
};

// --- Component: Active Call View ---
const ActiveCallView: React.FC<{ onDisconnect: () => void }> = ({ onDisconnect }) => {
    const { state, audioTrack: agentTrack } = useVoiceAssistant();
    const { localParticipant, microphoneTrack } = useLocalParticipant();
    const [isMicMuted, setIsMicMuted] = useState(false);
    const messages = useChatTranscriptions();

    const toggleMic = useCallback(() => {
        if (!localParticipant) return;
        const newVal = !isMicMuted;
        localParticipant.setMicrophoneEnabled(!newVal);
        setIsMicMuted(newVal);
    }, [localParticipant, isMicMuted]);

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
        <div className="flex-1 flex flex-col md:flex-row min-h-0 bg-[#0F172A]">
            {/* Left/Middle: Transcript */}
            <div className="flex-1 flex flex-col min-h-0 bg-[#0F172A] border-r border-white/5 order-2 md:order-1">
                <div className="p-4 border-b border-white/5 flex justify-between items-center bg-[#1E293B]/30">
                    <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2 uppercase tracking-wider">
                        <MessageSquare size={16} className="text-indigo-400" /> Conversation Transcript
                    </h3>
                </div>
                <div className="flex-1 overflow-y-auto custom-scrollbar p-2">
                    <ChatList messages={messages} />
                </div>
            </div>

            {/* Right/Side: Visualizer & Controls */}
            <div className="w-full md:w-80 lg:w-96 flex flex-col bg-[#111827] p-6 gap-6 shrink-0 order-1 md:order-2 border-b md:border-b-0 md:border-l border-white/5 shadow-2xl z-10">
                <div className="flex flex-col items-center gap-4 py-6 md:py-10">
                    <div className="relative w-32 h-32 flex items-center justify-center">
                        <div className={`absolute inset-0 bg-indigo-500/20 rounded-full blur-3xl transition-all duration-700 ${state === 'speaking' ? 'scale-150 opacity-100' : 'scale-100 opacity-50'}`}></div>
                        <div className={`relative z-10 w-24 h-24 bg-gradient-to-br from-indigo-500 to-indigo-700 rounded-[2.5rem] flex items-center justify-center shadow-[0_0_30px_rgba(99,102,241,0.3)] transition-transform duration-300 ${state === 'speaking' ? 'scale-105' : ''}`}>
                            <Bot size={56} className="text-white" />
                        </div>
                    </div>
                    <div className="text-center">
                        <h4 className="text-2xl font-bold text-white tracking-tight">Hirebot</h4>
                        <div className="flex items-center justify-center gap-2 mt-2">
                            <span className={`w-2 h-2 rounded-full ${state === 'disconnected' ? 'bg-slate-500' : 'bg-emerald-500 animate-pulse'}`}></span>
                            <p className="text-xs text-slate-400 uppercase tracking-[0.2em] font-bold">
                                {state === 'speaking' ? 'Speaking...' : (state === 'listening' ? 'Listening...' : 'Connected')}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center bg-black/20 rounded-[2rem] border border-white/5 p-8 min-h-[160px] relative overflow-hidden">
                    <div className="absolute inset-0 bg-indigo-500/5 blur-3xl rounded-full"></div>
                    <VisualizerSection state={visualizerState} trackRef={activeTrack} />
                </div>

                <div className="flex flex-col gap-4 mt-auto">
                    <button
                        onClick={toggleMic}
                        className={`w-full flex items-center justify-center gap-3 py-4 rounded-2xl font-bold transition-all duration-300 ${isMicMuted ? 'bg-white text-slate-900 shadow-xl' : 'bg-white/5 text-slate-200 border border-white/10 hover:bg-white/10'}`}
                    >
                        {isMicMuted ? <MicOff size={20} /> : <Mic size={20} />}
                        {isMicMuted ? 'Unmute' : 'Mute Microphone'}
                    </button>
                    <button
                        onClick={onDisconnect}
                        className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl bg-gradient-to-r from-rose-500 to-red-600 text-white font-bold hover:from-rose-600 hover:to-red-700 transition-all shadow-lg shadow-rose-500/25 active:scale-95"
                    >
                        <PhoneOff size={20} />
                        End Session
                    </button>
                </div>
            </div>

            <RoomAudioRenderer />
            <StartAudio label="Click to allow audio playback" />
        </div>
    );
};

export default function HirebotPage() {
    const navigate = useNavigate();

    // View State: 'landing' (buttons) or 'web' (livekit)
    const [viewMode, setViewMode] = useState<'landing' | 'web'>('landing');
    const [isCallModalOpen, setIsCallModalOpen] = useState(false);

    // LiveKit State
    const [token, setToken] = useState<string>('');
    const [connecting, setConnecting] = useState(false);

    const handleConnect = useCallback(async () => {
        setConnecting(true);
        try {
            const userId = `user_${Math.floor(Math.random() * 10000)}`;
            const url = `${TOKEN_ENDPOINT}?name=${userId}&agent=hirebot`;

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
    }, []);

    const handleBack = useCallback(() => {
        if (viewMode === 'web') {
            handleDisconnect();
            setViewMode('landing');
        } else {
            navigate('/');
        }
    }, [navigate, viewMode, handleDisconnect]);

    const handleWebSelection = async () => {
        setConnecting(true);
        try {
            const userId = `user_${Math.floor(Math.random() * 10000)}`;
            const url = `${TOKEN_ENDPOINT}?name=${userId}&agent=hirebot`;

            const response = await fetch(url, { mode: 'cors' });
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }

            const accessToken = await response.text();

            if (!accessToken || accessToken.trim().length === 0) {
                throw new Error("Received empty token from backend");
            }

            // Store in sessionStorage so LegacyAgentPage can pick it up
            sessionStorage.setItem('livekit_token', accessToken);
            sessionStorage.setItem('agent_type', 'hirebot');

            navigate('/hirebot/web');
        } catch (err: any) {
            console.error("Connection failed:", err);
            alert(`Failed to connect: ${err.message}`);
        } finally {
            setConnecting(false);
        }
    };

    // --- RENDER: Landing Selection Screen ---
    if (viewMode === 'landing') {
        return (
            <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 relative">
                {/* Back Button */}
                <button
                    onClick={() => navigate('/')}
                    className="absolute top-6 left-6 p-2 rounded-full bg-white shadow-sm border border-slate-200 text-slate-500 hover:text-slate-900 transition-colors"
                >
                    <ArrowLeft size={20} />
                </button>

                <div className="max-w-md w-full space-y-8 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div>
                        <div className="w-20 h-20 bg-indigo-100 rounded-3xl flex items-center justify-center mx-auto mb-6 text-indigo-600 shadow-xl shadow-indigo-200/50">
                            <Bot size={44} />
                        </div>
                        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">Hirebot</h1>
                        <p className="text-slate-500 mt-3 text-lg">Choose your preferred connection method</p>
                    </div>

                    <div className="grid gap-4 mt-10">
                        <button
                            onClick={handleWebSelection}
                            disabled={connecting}
                            className="w-full flex items-center justify-between p-6 bg-white border border-slate-200 rounded-3xl shadow-sm hover:shadow-xl hover:border-indigo-300 hover:bg-indigo-50/20 transition-all group text-left border-b-4 active:border-b active:translate-y-1 disabled:opacity-70 disabled:pointer-events-none"
                        >
                            <div className="flex items-center gap-5">
                                <div className="w-14 h-14 rounded-2xl bg-indigo-100 flex items-center justify-center text-indigo-600 group-hover:scale-110 transition-transform duration-500">
                                    {connecting ? <Loader2 size={28} className="animate-spin" /> : <Globe size={28} />}
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-900 text-xl tracking-tight">
                                        {connecting ? 'Connecting...' : 'Web Call'}
                                    </h3>
                                    <p className="text-sm text-slate-500 font-medium">Connect directly in browser</p>
                                </div>
                            </div>
                        </button>

                        <button
                            onClick={() => setIsCallModalOpen(true)}
                            className="w-full flex items-center justify-between p-6 bg-white border border-slate-200 rounded-3xl shadow-sm hover:shadow-xl hover:border-emerald-300 hover:bg-emerald-50/20 transition-all group text-left border-b-4 active:border-b active:translate-y-1"
                        >
                            <div className="flex items-center gap-5">
                                <div className="w-14 h-14 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-600 group-hover:scale-110 transition-transform duration-500">
                                    <Phone size={28} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-900 text-xl tracking-tight">Phone Call</h3>
                                    <p className="text-sm text-slate-500 font-medium">Receive a call on your mobile</p>
                                </div>
                            </div>
                        </button>
                    </div>
                </div>

                <OutboundCallModal
                    isOpen={isCallModalOpen}
                    onClose={() => setIsCallModalOpen(false)}
                    agentType="hirebot"
                />
            </div>
        );
    }

    // --- RENDER: Web Mode (LiveKit Room) ---
    return (
        <LiveKitRoom
            video={false}
            audio={true}
            token={token}
            connect={!!token}
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
            <HirebotWebLayout onBack={handleBack}>
                {token ? (
                    <ActiveCallView onDisconnect={handleDisconnect} />
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center p-6 bg-[#0F172A] relative overflow-hidden">
                        {/* Ambient Background Glow */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none"></div>

                        <div className="relative z-10 max-w-sm w-full text-center space-y-8">
                            <div className="relative w-32 h-32 flex items-center justify-center mx-auto">
                                <div className="absolute inset-0 bg-indigo-500/10 rounded-full animate-pulse"></div>
                                <div className="relative w-24 h-24 bg-[#1E293B] border border-white/10 rounded-[2rem] flex items-center justify-center shadow-2xl">
                                    <Bot size={48} className="text-indigo-400" />
                                </div>
                            </div>

                            <div className="space-y-3">
                                <h1 className="text-3xl font-bold text-white tracking-tight">Ready to start?</h1>
                                <p className="text-slate-400">Hirebot is ready to discuss your hiring needs. Click below to begin the voice session.</p>
                            </div>

                            <button
                                onClick={handleConnect}
                                disabled={connecting}
                                className="w-full py-5 rounded-2xl bg-indigo-500 text-white text-lg font-bold shadow-xl shadow-indigo-500/20 hover:bg-indigo-600 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-3 disabled:opacity-70 disabled:pointer-events-none group"
                            >
                                {connecting ? (
                                    <>
                                        <Loader2 size={24} className="animate-spin text-white/70" />
                                        <span>Initialising...</span>
                                    </>
                                ) : (
                                    <>
                                        <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                                            <Mic size={20} />
                                        </div>
                                        <span>Start Conversation</span>
                                    </>
                                )}
                            </button>

                            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Secure WebRTC Session</p>
                        </div>
                    </div>
                )}
            </HirebotWebLayout>
        </LiveKitRoom>
    );
}
