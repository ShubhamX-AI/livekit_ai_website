import React, { useEffect, useState, useMemo, useCallback } from 'react';
import {
  useVoiceAssistant,
  useLocalParticipant,
  useRoomContext,
  useTranscriptions,
} from '@livekit/components-react';
import { Track, Participant } from 'livekit-client';
import { Mic, MicOff, PhoneOff } from 'lucide-react';

import { Header } from './Header';
import { VisualizerSection } from './Visualizer';
import { ChatList } from './Chatlist';
import type { ChatMessage } from './Chatlist';

interface VoiceEvent {
  id: string;
  text: string;
  final: boolean;
  participant?: Participant;
  fromParticipant?: Participant;
}

type VisualizerState = 'speaking' | 'listening' | 'connected' | 'disconnected';

function mapAgentToVisualizerState(s: string): VisualizerState {
  if (s === 'connecting') return 'connected';
  if (s === 'speaking' || s === 'listening' || s === 'connected' || s === 'disconnected') return s;
  return 'connected';
}

const VoiceAssistant: React.FC = () => {
  const { state, audioTrack: agentTrack } = useVoiceAssistant();
  const { localParticipant, microphoneTrack } = useLocalParticipant();
  const room = useRoomContext();
  const transcriptions = useTranscriptions() as unknown as VoiceEvent[];

  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [isMicMuted, setIsMicMuted] = useState(false);

  // Track logic
  const userTrackRef = useMemo(() => {
    // Even if muted, we keep the participant ref so the visualizer doesn't crash, 
    // it will just receive no audio data.
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
  
  // Decide which track to visualize
  // If user is muted and Agent isn't speaking, we pass undefined to Visualizer 
  // (Visualizer will show idle breathing animation)
  const activeTrack = isAgentSpeaking ? agentTrackRef : (!isMicMuted ? userTrackRef : undefined);
  
  const visualizerState = mapAgentToVisualizerState(state as string);

  // Chat History Logic
  const uiMessages = useMemo(() => {
    const liveMessages: ChatMessage[] = transcriptions
      .filter(t => !t.final)
      .map(t => {
        const p = t.participant || t.fromParticipant;
        const isAgent = p?.identity?.includes('agent') || (p && p.identity !== localParticipant?.identity);
        return { id: t.id, text: t.text, sender: isAgent ? 'agent' : 'user', isInterim: true };
      });
    return [...history, ...liveMessages];
  }, [history, transcriptions, localParticipant]);

  useEffect(() => {
    transcriptions.forEach(seg => {
      if (seg.final) {
        setHistory(prev => {
          if (prev.some(m => m.id === seg.id)) return prev;
          const p = seg.participant || seg.fromParticipant;
          const isAgent = p?.identity?.includes('agent') || (p && p.identity !== localParticipant?.identity);
          return [...prev, { id: seg.id, text: seg.text, sender: isAgent ? 'agent' : 'user', isInterim: false }];
        });
      }
    });
  }, [transcriptions, localParticipant]);

  // Robust Mute Handler
  const toggleMic = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent click from bubbling
    e.preventDefault();  // Prevent default button behavior
    
    if (!localParticipant) return;
    
    const newVal = !isMicMuted;
    
    try {
      // Toggle the actual LiveKit track
      await localParticipant.setMicrophoneEnabled(!newVal);
      // Only update UI state if successful
      setIsMicMuted(newVal);
    } catch (error) {
      console.error("Error toggling microphone:", error);
    }
  }, [localParticipant, isMicMuted]);

  const handleDisconnect = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    room?.disconnect();
  }, [room]);

  return (
    <div className="fixed inset-0 w-full h-[100dvh] bg-zinc-50 text-zinc-900 overflow-hidden flex flex-col font-sans">
      
      {/* 1. Header */}
      <Header status={visualizerState} />

      {/* 2. Chat List */}
      <div className="flex-1 w-full relative overflow-hidden flex flex-col">
        <ChatList messages={uiMessages} />
      </div>

      {/* 3. THE DYNAMIC BOTTOM DOCK */}
      <div className="fixed bottom-8 left-0 right-0 flex justify-center z-50 pointer-events-none">
        <div 
          className="
            flex items-center gap-6 px-5 py-4 rounded-[32px] pointer-events-auto
            bg-white/90 backdrop-blur-2xl 
            border border-white/50 shadow-[0_20px_50px_rgba(0,0,0,0.1)]
            transition-all duration-500
          "
        >
           
          {/* Left: Mic Toggle */}
          <button 
            type="button" // CRITICAL: Prevents accidental form submission behavior
            onClick={toggleMic}
            className={`
              relative w-14 h-14 flex items-center justify-center rounded-full transition-all duration-300 shadow-sm
              ${isMicMuted 
                ? 'bg-zinc-100 text-zinc-400 hover:bg-zinc-200' 
                : 'bg-zinc-900 text-white hover:bg-zinc-800 hover:scale-105 hover:shadow-lg'}
            `}
          >
            {isMicMuted ? <MicOff size={22}/> : <Mic size={22}/>}
          </button>

          {/* Center: The Premium Visualizer */}
          <div className="h-10 w-[1px] bg-zinc-200/60 mx-1" />
          
          <VisualizerSection 
            state={visualizerState}
            trackRef={activeTrack}
          />
          
          <div className="h-10 w-[1px] bg-zinc-200/60 mx-1" />

          {/* Right: End Call */}
          <button 
            type="button"
            onClick={handleDisconnect}
            className="w-14 h-14 flex items-center justify-center rounded-full bg-rose-50 text-rose-500 hover:bg-rose-100 hover:scale-105 transition-all duration-300 shadow-sm hover:shadow-rose-100"
          >
            <PhoneOff size={22}/>
          </button>

        </div>
      </div>
    </div>
  );
};

export default VoiceAssistant;