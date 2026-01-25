import React from 'react';
import { useLiveKitAssistant } from './useLiveKitAssistant';
import { LiveKitAssistantProvider } from './LiveKitAssistantProvider';

const LIVEKIT_URL = import.meta.env?.VITE_LIVEKIT_URL || '';

export const SimpleVoiceAssistant: React.FC = () => {
    const {
        token,
        isConnecting,
        isConnected,
        visualizerState,
        messages,
        connect,
        disconnect,
        toggleMic,
        isMicMuted
    } = useLiveKitAssistant();

    return (
        <div className="voice-assistant-container">
            {!isConnected ? (
                <button
                    onClick={() => connect('bandhan_banking')}
                    disabled={isConnecting}
                >
                    {isConnecting ? 'Connecting...' : 'Start Voice Chat'}
                </button>
            ) : (
                <LiveKitAssistantProvider
                    token={token}
                    serverUrl={LIVEKIT_URL}
                    onDisconnected={disconnect}
                >
                    <div className="p-4 border rounded shadow-lg bg-white">
                        <h2 className="text-xl font-bold mb-4">Voice Assistant</h2>
                        <div className="mb-4">
                            Status: <span className="font-mono">{visualizerState}</span>
                        </div>

                        <div className="flex gap-2 mb-4">
                            <button
                                className="px-4 py-2 bg-slate-800 text-white rounded"
                                onClick={toggleMic}
                            >
                                {isMicMuted ? 'Unmute' : 'Mute'}
                            </button>
                            <button
                                className="px-4 py-2 bg-red-600 text-white rounded"
                                onClick={disconnect}
                            >
                                End Session
                            </button>
                        </div>

                        <div className="h-64 overflow-y-auto border-t pt-4">
                            {messages.map((msg) => (
                                <div key={msg.id} className={`mb-2 ${msg.sender === 'agent' ? 'text-blue-600' : 'text-slate-700'}`}>
                                    <strong>{msg.sender === 'agent' ? 'Bot: ' : 'You: '}</strong>
                                    {msg.text}
                                </div>
                            ))}
                        </div>
                    </div>
                </LiveKitAssistantProvider>
            )}
        </div>
    );
};
