import React, { type ReactNode } from 'react';
import { LiveKitRoom, RoomAudioRenderer, StartAudio } from '@livekit/components-react';

interface LiveKitAssistantProviderProps {
    token: string;
    serverUrl: string;
    children: ReactNode;
    onDisconnected?: () => void;
    onError?: (error: Error) => void;
}

export const LiveKitAssistantProvider: React.FC<LiveKitAssistantProviderProps> = ({
    token,
    serverUrl,
    children,
    onDisconnected,
    onError
}) => {
    return (
        <LiveKitRoom
            video={false}
            audio={true}
            token={token}
            connect={!!token}
            serverUrl={serverUrl}
            data-lk-theme="default"
            style={{ height: '100dvh' }}
            onDisconnected={onDisconnected}
            onError={onError}
        >
            {children}
            {/* Essential for audio playback */}
            <RoomAudioRenderer />
            {/* Necessary to handle browser's autoplay policies */}
            <StartAudio label="Click to allow audio playback" />
        </LiveKitRoom>
    );
};
