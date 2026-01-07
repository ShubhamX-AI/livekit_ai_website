import React, { useState } from 'react';
import { BankingDashboardUI } from './BankingDashboardUI';
import { Bot } from 'lucide-react';
import './VoiceAgentStyles.css';
import { AgentCardUI } from './AgentCardUI';

interface BankingPreviewProps {
    onConnect: () => void;
    onBack: () => void;
}

const BankingPreview: React.FC<BankingPreviewProps> = ({ onConnect, onBack }) => {
    const [isConnecting, setIsConnecting] = useState(false);
    const [isCardOpen, setIsCardOpen] = useState(false);

    const handleConnect = async () => {
        setIsConnecting(true);
        // Add a small artificial delay or just pass through
        await onConnect();
        // setIsConnecting(false); // Component will unmount/switch anyway
    };

    return (
        <BankingDashboardUI onBack={onBack}>
            {/* 
                ========================================
                PREVIEW / OFFLINE AGENT BUTTON
                ========================================
            */}
            <div className="fixed bottom-24 md:bottom-6 right-6 z-50 flex flex-col items-end gap-4">

                {/* Agent Card (Open) */}
                {isCardOpen && (
                    <AgentCardUI
                        state={isConnecting ? 'connecting' : 'standby'}
                        onClose={() => setIsCardOpen(false)}
                        onConnect={handleConnect}
                    />
                )}

                {/* Floating Trigger Button (Closed) */}
                {!isCardOpen && (
                    <button
                        onClick={() => setIsCardOpen(true)}
                        disabled={isConnecting} // Should generally not happen if closed, but for safety
                        className="pointer-events-auto group relative w-16 h-16 rounded-full bg-gradient-to-br from-[#D4AF37] to-[#bfa03a] shadow-[0_4px_20px_rgba(212,175,55,0.4)] flex items-center justify-center transition-transform hover:scale-110 active:scale-95 disabled:scale-100 disabled:opacity-80"
                    >
                        {/* Tooltip */}
                        <div className="absolute right-full mr-4 bg-[#151f32] text-[#D4AF37] px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none border border-[#D4AF37]/20">
                            Ask Vyom
                        </div>

                        <div className="relative z-10">
                            <Bot size={32} className="text-[#0B1426]" />
                        </div>

                        {/* Ping animation to draw attention */}
                        <div className="absolute inset-0 rounded-full bg-[#D4AF37] opacity-50 animate-ping"></div>
                    </button>
                )}
            </div>
        </BankingDashboardUI>
    );
};

export default BankingPreview;
