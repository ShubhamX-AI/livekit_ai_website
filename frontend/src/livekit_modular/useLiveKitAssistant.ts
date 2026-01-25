import { useState, useCallback, useMemo, useEffect } from 'react';
import {
    useVoiceAssistant,
    useLocalParticipant,
    useRoomContext,
    type TrackReferenceOrPlaceholder
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import { useLiveKitTranscriptions, type ChatMessage } from './useLiveKitTranscriptions';

export type VisualizerState = 'speaking' | 'listening' | 'connected' | 'disconnected' | 'connecting';

export interface LiveKitAssistantHook {
    token: string;
    isConnecting: boolean;
    isConnected: boolean;
    visualizerState: VisualizerState;
    activeTrack: TrackReferenceOrPlaceholder | undefined;
    isMicMuted: boolean;
    messages: ChatMessage[];
    connect: (agentName?: string) => Promise<void>;
    disconnect: () => void;
    toggleMic: () => void;
}

const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
const TOKEN_ENDPOINT = `${BACKEND_URL}/api/getToken`;

export function useLiveKitAssistant(): LiveKitAssistantHook {
    const [token, setToken] = useState<string>('');
    const [isConnecting, setIsConnecting] = useState(false);
    const [isMicMuted, setIsMicMuted] = useState(false);

    // LiveKit Hooks
    const { state, audioTrack: agentTrack } = useVoiceAssistant();
    const { localParticipant, microphoneTrack } = useLocalParticipant();
    const room = useRoomContext();
    const messages = useLiveKitTranscriptions();

    // Auto-enable microphone on mount/connect
    useEffect(() => {
        if (localParticipant && token) {
            localParticipant.setMicrophoneEnabled(true);
        }
    }, [localParticipant, token]);

    const connect = useCallback(async (agentName: string = 'bandhan_banking') => {
        setIsConnecting(true);
        try {
            const userId = `user_${Math.floor(Math.random() * 10000)}`;
            const url = `${TOKEN_ENDPOINT}?name=${userId}&agent=${agentName}`;

            const response = await fetch(url, { mode: 'cors' });
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }

            const accessToken = await response.text();
            if (!accessToken || accessToken.trim().length === 0) {
                throw new Error("Received empty token from backend");
            }

            setToken(accessToken);
        } catch (err) {
            console.error("Connection failed:", err);
            throw err;
        } finally {
            setIsConnecting(false);
        }
    }, []);

    const disconnect = useCallback(() => {
        setToken('');
        room?.disconnect();
    }, [room]);

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

    const visualizerState = useMemo((): VisualizerState => {
        if (isConnecting) return 'connecting';
        if (!token) return 'disconnected';
        if (state === 'speaking' || state === 'listening') return state as VisualizerState;
        return 'connected';
    }, [state, isConnecting, token]);

    const activeTrack = useMemo(() => {
        if (state === 'speaking') return agentTrackRef;
        if (!isMicMuted) return userTrackRef;
        return undefined;
    }, [state, agentTrackRef, userTrackRef, isMicMuted]);

    return {
        token,
        isConnecting,
        isConnected: !!token,
        visualizerState,
        activeTrack,
        isMicMuted,
        messages,
        connect,
        disconnect,
        toggleMic
    };
}
