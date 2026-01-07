import React from 'react';
import { Bot, X, Mic, MicOff, PhoneOff, Loader2 } from 'lucide-react';
import './VoiceAgentStyles.css';
import { VisualizerSection } from '../Visualizer';

interface AgentCardUIProps {
    state: 'standby' | 'connecting' | 'active';
    onClose: () => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onToggleMic?: () => void;
    isMicMuted?: boolean;
    isAgentSpeaking?: boolean;
    visualizerState?: 'speaking' | 'listening' | 'connected' | 'disconnected';
    trackRef?: any;
    statusText?: string;
}

export const AgentCardUI: React.FC<AgentCardUIProps> = ({
    state,
    onClose,
    onConnect,
    onDisconnect,
    onToggleMic,
    isMicMuted = false,
    isAgentSpeaking = false,
    visualizerState = 'connected',
    trackRef,
    statusText
}) => {
    return (
        <div className="pointer-events-auto bg-[#151f32]/90 backdrop-blur-2xl border border-[#D4AF37]/20 shadow-[0_8px_32px_rgba(0,0,0,0.4)] rounded-[24px] p-4 flex flex-col items-center gap-4 w-[280px] animate-fade-in-up transition-all">

            {/* Header / Controls */}
            <div className="w-full flex justify-between items-center border-b border-white/5 pb-3">
                <div className="flex items-center gap-2">
                    {state === 'active' ? (
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                    ) : (
                        <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                    )}
                    <span className="text-xs text-[#D4AF37] font-semibold tracking-wide">
                        {state === 'active' ? 'VYOM ACTIVE' : 'VYOM STANDBY'}
                    </span>
                </div>
                <button
                    onClick={onClose}
                    className="text-slate-400 hover:text-white transition-colors p-1"
                >
                    <X size={16} />
                </button>
            </div>

            {/* Agent Visual / Animation */}
            <div className="relative w-24 h-24 flex items-center justify-center my-2">
                {/* Glow Effect */}
                <div className={`absolute inset-0 bg-[#D4AF37]/20 rounded-full blur-xl transition-all duration-300 ${isAgentSpeaking ? 'scale-125 opacity-100' : 'scale-100 opacity-50'}`}></div>

                {/* The Face / Icon */}
                <div className={`relative z-10 w-20 h-20 bg-gradient-to-b from-[#D4AF37] to-[#8a7020] rounded-2xl flex items-center justify-center shadow-lg transition-transform duration-200 ${isAgentSpeaking ? 'animate-mouth-move' : ''}`}>
                    <Bot size={40} className="text-[#0B1426]" />
                </div>
            </div>

            {/* Status Text & Waveform / Connect Button */}
            <div className="w-full flex flex-col items-center gap-2 min-h-[64px] justify-center">
                {state === 'active' ? (
                    <>
                        <span className="text-sm font-medium text-slate-200">
                            {statusText || (isAgentSpeaking ? "Speaking..." : "Listening...")}
                        </span>
                        <div className="h-8 w-full flex items-center justify-center">
                            <VisualizerSection
                                state={visualizerState}
                                trackRef={trackRef}
                            />
                        </div>
                    </>
                ) : (
                    <div className="flex flex-col items-center gap-2 w-full">
                        <span className="text-xs text-slate-400 text-center px-4 leading-tight">
                            Start a voice session to manage your account.
                        </span>
                    </div>
                )}
            </div>

            {/* Footer Actions */}
            <div className="w-full">
                {state === 'active' ? (
                    <div className="flex gap-2">
                        <button
                            onClick={onToggleMic}
                            className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${!isMicMuted ? 'bg-[#D4AF37] text-[#0B1426]' : 'bg-red-500/10 text-red-500 border border-red-500/20'}`}
                        >
                            {isMicMuted ? <><MicOff size={14} /> Muted</> : <><Mic size={14} /> Mute Mic</>}
                        </button>
                        <button
                            onClick={onDisconnect}
                            className="w-10 flex items-center justify-center rounded-xl bg-slate-700/50 text-slate-400 hover:bg-rose-500 hover:text-white transition-colors"
                        >
                            <PhoneOff size={16} />
                        </button>
                    </div>
                ) : (
                    <button
                        onClick={onConnect}
                        disabled={state === 'connecting'}
                        className="w-full py-3 rounded-xl bg-[#D4AF37] text-[#0B1426] text-sm font-bold shadow-lg shadow-[#D4AF37]/20 hover:bg-[#bfa03a] hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2 disabled:opacity-70 disabled:pointer-events-none"
                    >
                        {state === 'connecting' ? (
                            <>
                                <Loader2 size={16} className="animate-spin" /> Connecting...
                            </>
                        ) : (
                            <>
                                <Mic size={16} /> Connect with Agent
                            </>
                        )}
                    </button>
                )}
            </div>

        </div>
    );
};
