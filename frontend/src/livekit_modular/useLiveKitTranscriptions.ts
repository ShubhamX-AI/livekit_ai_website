import { useEffect, useState, useCallback } from "react";
import { RoomEvent, Participant } from "livekit-client";
import type { TranscriptionSegment } from "livekit-client";
import { useRoomContext, useLocalParticipant } from "@livekit/components-react";

export interface ChatMessage {
    id: string;
    sender: 'user' | 'agent';
    type: 'text' | 'flashcard';
    text?: string;
    cardData?: {
        title: string;
        value: string;
    };
    isInterim?: boolean;
    timestamp: number;
}

export function useLiveKitTranscriptions() {
    const room = useRoomContext();
    const { localParticipant } = useLocalParticipant();
    const [messages, setMessages] = useState<Map<string, ChatMessage>>(new Map());

    const handleTranscription = useCallback(
        (segments: TranscriptionSegment[], participant?: Participant) => {
            if (!participant) return;
            const senderIsAgent = participant.identity !== localParticipant?.identity;

            setMessages((prev) => {
                const next = new Map(prev);
                for (const segment of segments) {
                    next.set(segment.id, {
                        id: segment.id,
                        type: 'text',
                        text: segment.text.replace(/\[.*?\]/g, '').trim(),
                        sender: senderIsAgent ? "agent" : "user",
                        isInterim: !segment.final,
                        timestamp: segment.firstReceivedTime,
                    });
                }
                return next;
            });
        },
        [localParticipant]
    );

    const handleData = useCallback(
        (payload: Uint8Array, _participant?: Participant, _kind?: any, topic?: string) => {
            if (topic !== "ui.flashcard") return;

            const strData = new TextDecoder().decode(payload);
            try {
                const data = JSON.parse(strData);
                if (data.type === 'flashcard') {
                    const id = `card-${Date.now()}`;
                    setMessages((prev) => {
                        const next = new Map(prev);
                        next.set(id, {
                            id: id,
                            type: 'flashcard',
                            cardData: {
                                title: data.title,
                                value: data.value
                            },
                            sender: 'agent',
                            timestamp: Date.now(),
                            isInterim: false
                        });
                        return next;
                    });
                }
            } catch (e) {
                console.error(e);
            }
        },
        []
    );

    useEffect(() => {
        if (!room) return;
        room.on(RoomEvent.TranscriptionReceived, handleTranscription);
        room.on(RoomEvent.DataReceived, handleData);
        return () => {
            room.off(RoomEvent.TranscriptionReceived, handleTranscription);
            room.off(RoomEvent.DataReceived, handleData);
        };
    }, [room, handleTranscription, handleData]);

    return Array.from(messages.values()).sort((a, b) => a.timestamp - b.timestamp);
}
