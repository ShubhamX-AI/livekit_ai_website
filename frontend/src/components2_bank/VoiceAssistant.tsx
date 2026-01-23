import React, { useMemo, useCallback, useState, useEffect } from 'react';
import {
  useVoiceAssistant,
  useLocalParticipant,
  useRoomContext,
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import { Mic, MicOff, PhoneOff } from 'lucide-react';

import { Header } from './Header';
import { VisualizerSection } from './Visualizer';
import { ChatList } from './Chatlist';
import { useChatTranscriptions } from '../hooks/useChatTranscriptions';

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
  const [isMicMuted, setIsMicMuted] = useState(false);

  // Auto-enable microphone on mount
  useEffect(() => {
    if (localParticipant) {
      localParticipant.setMicrophoneEnabled(true);
    }
  }, [localParticipant]);

  // 1. One Hook to Rule Them All
  // This now contains text messages AND flashcards in order
  const uiMessages = useChatTranscriptions();

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

  const toggleMic = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    if (!localParticipant) return;
    const newVal = !isMicMuted;
    try {
      await localParticipant.setMicrophoneEnabled(!newVal);
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

      <Header status={visualizerState} />

      {/* Removed FlashcardOverlay - cards are now inside ChatList */}

      <div className="flex-1 w-full relative overflow-hidden flex flex-col">
        <ChatList messages={uiMessages} />
      </div>

      <div className="fixed bottom-8 left-0 right-0 flex justify-center z-50 pointer-events-none">
        <div
          className="
            flex items-center gap-4 px-6 py-3 rounded-full pointer-events-auto
            bg-white/95 backdrop-blur-2xl 
            border border-slate-200/50 shadow-[0_30px_60px_rgba(0,0,0,0.12)]
            transition-all duration-500
          "
        >
          <button
            type="button"
            onClick={toggleMic}
            className={`
              flex items-center gap-2 px-5 py-3 rounded-full transition-all duration-300 font-semibold text-sm
              ${isMicMuted
                ? 'bg-slate-100 text-slate-900 border border-slate-200 shadow-inner'
                : 'bg-slate-900 text-white hover:bg-slate-800 shadow-lg hover:shadow-xl hover:-translate-y-0.5'}
            `}
          >
            {isMicMuted ? <MicOff size={18} /> : <Mic size={18} />}
            <span>{isMicMuted ? 'Unmute' : 'Mute'}</span>
          </button>

          <div className="h-8 w-[1px] bg-slate-200 mx-1" />

          <VisualizerSection
            state={visualizerState}
            trackRef={activeTrack}
          />

          <div className="h-8 w-[1px] bg-slate-200 mx-1" />

          <button
            type="button"
            onClick={handleDisconnect}
            className="
              flex items-center gap-2 px-5 py-3 rounded-full 
              bg-rose-50 text-rose-600 border border-rose-100
              hover:bg-rose-500 hover:text-white hover:border-rose-500 hover:shadow-lg hover:shadow-rose-500/30 hover:-translate-y-0.5
              transition-all duration-300 font-semibold text-sm
            "
          >
            <PhoneOff size={18} />
            <span>End</span>
          </button>

        </div>
      </div>
    </div>
  );
};

export default VoiceAssistant;