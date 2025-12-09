import React, { useEffect, useState, useRef, useMemo } from 'react';
import {
  useVoiceAssistant,
  BarVisualizer,
  useChat,
  useLocalParticipant,
  useRoomContext,
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import { Sparkles, Mic, MicOff, PhoneOff, ChevronLeft } from 'lucide-react';
import type { TranscriptionMessage } from '../types';

const VoiceAssistant: React.FC = () => {
  // --- HOOKS ---
  const { state, audioTrack: agentTrack } = useVoiceAssistant();
  const { localParticipant, microphoneTrack } = useLocalParticipant();
  const room = useRoomContext();
  const { chatMessages } = useChat();

  // --- STATE ---
  const [transcripts, setTranscripts] = useState<TranscriptionMessage[]>([]);
  const [isMicMuted, setIsMicMuted] = useState(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // --- 1. SYNC CHAT ---
  useEffect(() => {
    if (chatMessages) {
      const formattedMessages: TranscriptionMessage[] = chatMessages.map((msg) => ({
        id: msg.id || Math.random().toString(),
        text: msg.message,
        sender: msg.from?.identity === 'agent' ? 'agent' : 'user',
        timestamp: msg.timestamp || Date.now()
      }));
      setTranscripts(formattedMessages);
    }
  }, [chatMessages]);

  // --- 2. AUTO SCROLL ---
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts, state]);

  // --- 3. TRACK LOGIC (THE WAVE SOURCE) ---
  const isAgentSpeaking = state === 'speaking';
  
  const userTrackRef = useMemo(() => {
    if (!localParticipant || !microphoneTrack) return undefined;
    return {
      participant: localParticipant,
      source: Track.Source.Microphone,
      publication: microphoneTrack,
    };
  }, [localParticipant, microphoneTrack]);

  const activeTrackReference = isAgentSpeaking ? agentTrack : userTrackRef;

  // --- 4. ACTIONS ---
  const toggleMic = () => {
    if (localParticipant) {
      const newVal = !isMicMuted;
      localParticipant.setMicrophoneEnabled(!newVal);
      setIsMicMuted(newVal);
    }
  };

  const handleDisconnect = () => {
    room?.disconnect();
  };

  // --- THEME COLORS ---
  // Agent: Deep Indigo/Purple | User: Emerald/Teal
  const themeColor = isAgentSpeaking ? '#6366f1' : '#10b981'; 
  const glowColor = isAgentSpeaking ? 'rgba(99, 102, 241, 0.4)' : 'rgba(16, 185, 129, 0.4)';

  return (
    <div className="relative flex flex-col w-full h-[100dvh] bg-white text-slate-900 font-sans overflow-hidden">
      
      {/* --- BACKGROUND MIST --- */}
      <div className="absolute inset-0 pointer-events-none z-0">
         {/* Top Gradient Blob */}
         <div 
           className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[150vw] h-[50vh] rounded-[100%] blur-[80px] opacity-40 transition-colors duration-1000 ease-in-out"
           style={{ backgroundColor: isAgentSpeaking ? '#e0e7ff' : '#d1fae5' }} 
         />
      </div>

      {/* --- HEADER (Fixed Top Left) --- */}
      <header className="absolute top-0 left-0 w-full p-4 md:p-8 z-50 flex items-center justify-between">
        <div className="flex items-center gap-3">
            {/* Back Arrow (Visual only, or link to home) */}
            <button onClick={handleDisconnect} className="md:hidden text-slate-400 hover:text-slate-800">
                <ChevronLeft size={24} />
            </button>

            {/* Brand Logo */}
            <div className="flex items-center gap-2">
                <span className={`p-2 rounded-xl transition-colors duration-500 ${isAgentSpeaking ? 'bg-indigo-50 text-indigo-600' : 'bg-emerald-50 text-emerald-600'}`}>
                    <Sparkles size={18} fill="currentColor" />
                </span>
                <span className="font-bold text-lg md:text-xl tracking-tight text-slate-900">
                    INT. <span className="font-light text-slate-500">Intelligence</span>
                </span>
            </div>
        </div>
      </header>

      {/* --- MAIN CONTENT AREA --- */}
      <main className="flex-1 flex flex-col items-center relative z-10 w-full max-w-2xl mx-auto pt-24 pb-32 px-4">
        
        {/* --- 1. THE WAVEFORM --- */}
        <div className="flex-none flex flex-col items-center justify-center w-full min-h-[180px] transition-all duration-500">
           
           {/* Visualizer Container */}
           <div className="relative w-full max-w-[320px] h-[64px] flex items-center justify-center mb-6">
              
              {/* Glow behind the wave */}
              <div 
                className="absolute inset-0 blur-3xl transition-colors duration-500 opacity-60 rounded-full"
                style={{ backgroundColor: glowColor }}
              />

              {activeTrackReference ? (
                <BarVisualizer
                  state={state}
                  barCount={30} // High count for "Wave" look
                  trackRef={activeTrackReference}
                  style={{ height: '100%', width: '100%', gap: '5px' }}
                  options={{ minHeight: 12, maxHeight: 60 }} 
                  className="relative z-10"
                >
                    {/* CSS Injection for Fluid Color Change */}
                    <style>{`
                        .lk-audio-visualizer > rect { 
                            fill: ${themeColor} !important; 
                            rx: 3px; 
                            transition: height 0.1s ease, fill 0.5s ease;
                        } 
                    `}</style>
                </BarVisualizer>
              ) : (
                /* Idle Animation (Three Dots) */
                <div className="flex items-center gap-2 opacity-50">
                   <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0s'}}></div>
                   <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.2s'}}></div>
                   <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.4s'}}></div>
                </div>
              )}
           </div>

           {/* Status Label */}
           <div className="text-center space-y-1">
              <p 
                className="text-xl md:text-2xl font-medium tracking-wide transition-colors duration-500"
                style={{ color: themeColor }}
              >
                {isAgentSpeaking ? "AI is speaking" : "Listening..."}
              </p>
           </div>
        </div>

        {/* --- 2. CONVERSATION HISTORY (Responsive List) --- */}
        <div 
          className="flex-1 w-full overflow-y-auto custom-scrollbar relative px-2 md:px-4"
          style={{ 
            maskImage: 'linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)',
            WebkitMaskImage: 'linear-gradient(to bottom, transparent, black 15%, black 85%, transparent)'
          }}
        >
          <div className="space-y-6 py-8">
            {transcripts.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-slate-300 gap-2 mt-10">
                    <p className="text-sm">Start speaking to interact</p>
                </div>
            )}
            
            {transcripts.map((msg) => (
              <div 
                key={msg.id} 
                className={`flex w-full animate-fade-in-up ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div 
                  className={`
                    px-5 py-3.5 text-[15px] md:text-base leading-relaxed max-w-[85%] md:max-w-[75%] rounded-2xl shadow-sm
                    transition-all duration-300
                    ${msg.sender === 'user' 
                      ? 'bg-slate-50 text-slate-800 border border-slate-200 rounded-tr-none' 
                      : 'bg-white text-slate-800 border border-slate-100 rounded-tl-none shadow-[0_2px_8px_rgba(0,0,0,0.04)]'
                    }
                  `}
                >
                    {msg.text}
                </div>
              </div>
            ))}
            <div ref={transcriptEndRef} className="h-4" />
          </div>
        </div>

      </main>

      {/* --- FOOTER CONTROLS (Floating & Premium) --- */}
      <div className="absolute bottom-8 left-0 right-0 z-50 flex justify-center px-4">
        <div className="flex items-center gap-4 md:gap-6 bg-white/80 backdrop-blur-xl border border-white/40 p-3 px-6 rounded-full shadow-2xl shadow-slate-200/50 transform hover:scale-[1.02] transition-transform duration-300">
           
           {/* Mute Button */}
           <button 
             onClick={toggleMic}
             className={`
               w-12 h-12 md:w-14 md:h-14 rounded-full flex items-center justify-center transition-all duration-300
               ${isMicMuted 
                 ? 'bg-slate-100 text-slate-500 hover:bg-slate-200' 
                 : 'bg-black text-white shadow-lg shadow-black/20 hover:bg-slate-800'
               }
             `}
           >
             {isMicMuted ? <MicOff size={20} /> : <Mic size={20} />}
           </button>

           {/* Divider */}
           <div className="w-[1px] h-8 bg-slate-200/60" />

           {/* End Call Button */}
           <button 
             onClick={handleDisconnect}
             className="w-12 h-12 md:w-14 md:h-14 rounded-full bg-red-50 text-red-500 hover:bg-red-500 hover:text-white flex items-center justify-center transition-all duration-300"
           >
             <PhoneOff size={20} />
           </button>

        </div>
      </div>

    </div>
  );
};

export default VoiceAssistant;