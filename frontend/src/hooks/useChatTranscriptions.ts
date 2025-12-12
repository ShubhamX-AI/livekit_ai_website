import { useEffect, useState, useCallback } from "react";
import { RoomEvent, Participant } from "livekit-client";
import type { TranscriptionSegment } from "livekit-client";
import { useRoomContext, useLocalParticipant } from "@livekit/components-react";

export interface ChatMessage {
  id: string;
  text: string;
  sender: "user" | "agent";
  isInterim?: boolean;
  timestamp: number; // useful for sorting if needed
}

export function useChatTranscriptions(history: ChatMessage[] = []) {
  const room = useRoomContext();
  const { localParticipant } = useLocalParticipant();
  const [liveMessages, setLiveMessages] = useState<Map<string, ChatMessage>>(new Map());

  const updateSegment = useCallback(
    (segment: TranscriptionSegment, participant?: Participant) => {
      // 1. Safety check: If no participant (system event?), assume agent or ignore
      if (!participant) return;

      const senderIsAgent = participant.identity !== localParticipant?.identity;

      setLiveMessages((prev) => {
        const next = new Map(prev);

        const msg: ChatMessage = {
          id: segment.id,
          text: segment.text,
          sender: senderIsAgent ? "agent" : "user",
          isInterim: !segment.final,
          timestamp: segment.firstReceivedTime,
        };

        // 2. Logic: Always update the segment. 
        // If it was interim and is now final, this overwrite fixes it.
        next.set(segment.id, msg);

        return next;
      });
    },
    [localParticipant]
  );

  useEffect(() => {
    if (!room) return;

    // 3. Event Listener with proper typing
    const handler = (
      segments: TranscriptionSegment[], 
      participant?: Participant
    ) => {
      for (const segment of segments) {
        updateSegment(segment, participant);
      }
    };

    room.on(RoomEvent.TranscriptionReceived, handler);
    return () => {
      room.off(RoomEvent.TranscriptionReceived, handler);
    };
  }, [room, updateSegment]);

  // 4. Merge History + Live, sorted by time (optional but recommended)
  // We prioritize 'history' then append 'liveMessages'
  const uiMessages = [
    ...history, 
    ...Array.from(liveMessages.values())
  ].sort((a, b) => a.timestamp - b.timestamp);

  return uiMessages;
}