import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components2_bank/Header';
import { AlertCircle, Mic } from 'lucide-react';
import type { AgentType } from '../types/agent';
import { AgentButton } from '../components2_bank/AgentButton';
import { OutboundCallModal } from '../components2_bank/OutboundCallModal';
import { AgentInteractionModal } from '../components2_bank/AgentInteractionModal';
import { InboundSettingsModal } from '../components2_bank/InboundSettingsModal';
import { Settings } from 'lucide-react';

// Safely access environment variables with fallback
const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
const TOKEN_ENDPOINT = `${BACKEND_URL}/api/getToken`;

export default function HomePage() {
    const navigate = useNavigate();
    const [connecting, setConnecting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [outboundModalOpen, setOutboundModalOpen] = useState(false);
    const [interactionModalOpen, setInteractionModalOpen] = useState(false);
    const [inboundSettingsOpen, setInboundSettingsOpen] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState<AgentType>('web');

    const connect = async (chosenAgent: AgentType) => {
        setConnecting(true);
        setError(null);
        try {
            const userId = `user_${Math.floor(Math.random() * 10000)}`;
            const url = `${TOKEN_ENDPOINT}?name=${userId}&agent=${chosenAgent}`;

            const response = await fetch(url, { mode: 'cors' });
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }

            const accessToken = await response.text();

            if (!accessToken || accessToken.trim().length === 0) {
                throw new Error("Received empty token from backend");
            }

            // Store token in sessionStorage and navigate
            sessionStorage.setItem('livekit_token', accessToken);
            sessionStorage.setItem('agent_type', chosenAgent);

            // Navigate based on agent type
            if (chosenAgent === 'bank') {
                navigate('/bank');
            } else {
                navigate(`/${chosenAgent}`);
            }
        } catch (err: any) {
            console.error("Connection failed:", err);
            let msg = "Failed to connect to backend.";
            if (err.message && err.message.includes('Failed to fetch')) {
                msg = `Could not reach server at ${BACKEND_URL}. Ensure your backend is running.`;
            } else if (err.message) {
                msg = err.message;
            }
            setError(msg);
        } finally {
            setConnecting(false);
        }
    };

    const handleWebCall = (agent: AgentType) => {
        // preserve original behavior: navigate for bank/tour, connect for others
        if (agent === 'bank') {
            navigate('/bank');
        } else if (agent === 'tour') {
            navigate('/jharkhand');
        } else {
            connect(agent);
        }
    };

    const handleOutboundCall = (agent: AgentType) => {
        setSelectedAgent(agent);
        setOutboundModalOpen(true);
    };

    const handleMobileClick = (agent: AgentType) => {
        setSelectedAgent(agent);
        setInteractionModalOpen(true);
    };

    return (
        <div className="flex flex-col min-h-screen bg-background text-text-main font-sans selection:bg-primary/20">
            <Header status="disconnected" />

            <button
                onClick={() => setInboundSettingsOpen(true)}
                className="fixed top-6 right-6 z-50 p-3 bg-white/80 backdrop-blur-xl border border-white/40 shadow-sm rounded-full text-zinc-500 hover:text-primary hover:bg-primary/5 transition-all duration-300 group"
                title="Inbound Call Settings"
            >
                <Settings size={20} className="group-hover:rotate-90 transition-transform duration-500" />
            </button>

            <main className="flex-1 flex flex-col items-center justify-center p-5 relative overflow-hidden">
                {/* ... existing main content ... */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />

                <div className="max-w-xl w-full text-center space-y-10 animate-fade-in-up relative z-10">

                    <div className="space-y-6">
                        <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center mx-auto text-primary shadow-[0_8px_30px_rgba(0,0,0,0.06)] border border-border">
                            <Mic size={40} strokeWidth={1.5} />
                        </div>
                        <div className="space-y-2">
                            <h2 className="text-4xl md:text-5xl font-bold text-primary tracking-tight">How can I help you?</h2>
                            <p className="text-text-muted text-lg max-w-md mx-auto leading-relaxed">
                                Connect to INT. Intelligence to access real-time voice insights, analysis, and support.
                            </p>
                        </div>
                    </div>

                    {error && (
                        <div className="max-w-md mx-auto p-4 rounded-xl bg-red-50 border border-red-100 text-red-700 flex items-start gap-3 text-left shadow-sm">
                            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <p className="text-sm font-medium leading-tight">{error}</p>
                        </div>
                    )}

                    <div className="flex flex-col gap-4 max-w-xs mx-auto w-full">
                        <AgentButton
                            label="Indusnet Web Agent"
                            agentType="web"
                            onWebCall={handleWebCall}
                            onOutboundCall={handleOutboundCall}
                            onMobileClick={handleMobileClick}
                            disabled={connecting}
                        />

                        <AgentButton
                            label="Invoice Agent"
                            agentType="invoice"
                            onWebCall={handleWebCall}
                            onOutboundCall={handleOutboundCall}
                            onMobileClick={handleMobileClick}
                            disabled={connecting}
                        />

                        <AgentButton
                            label="Restaurant Agent"
                            agentType="restaurant"
                            onWebCall={handleWebCall}
                            onOutboundCall={handleOutboundCall}
                            onMobileClick={handleMobileClick}
                            disabled={connecting}
                        />

                        <AgentButton
                            label="Banking Agent"
                            agentType="bank"
                            onWebCall={handleWebCall}
                            onOutboundCall={handleOutboundCall}
                            onMobileClick={handleMobileClick}
                            disabled={connecting}
                        />

                        <AgentButton
                            label="Tour Agent"
                            agentType="tour"
                            onWebCall={handleWebCall}
                            onOutboundCall={handleOutboundCall}
                            onMobileClick={handleMobileClick}
                            disabled={connecting}
                        />
                        <AgentButton
                            label="Real Estate Agent"
                            agentType="realestate"
                            onWebCall={handleWebCall}
                            onOutboundCall={handleOutboundCall}
                            onMobileClick={handleMobileClick}
                            disabled={connecting}
                        />
                    
                    <AgentButton
                            label="Distributor Agent"
                            agentType="distributor"
                            onWebCall={handleWebCall}
                            onOutboundCall={handleOutboundCall}
                            onMobileClick={handleMobileClick}
                            disabled={connecting}
                    />
                    </div>

                    <div className="pt-8 flex justify-center gap-6 text-sm text-text-muted opacity-70">
                        <span className="flex items-center gap-1">Secure Connection</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">Real-time Audio</span>
                    </div>

                </div>
            </main>

            <OutboundCallModal
                isOpen={outboundModalOpen}
                onClose={() => setOutboundModalOpen(false)}
                agentType={selectedAgent}
            />
            
            <AgentInteractionModal
                isOpen={interactionModalOpen}
                onClose={() => setInteractionModalOpen(false)}
                agentType={selectedAgent}
                onWebCall={handleWebCall}
                onOutboundCall={handleOutboundCall}
            />

            <InboundSettingsModal
                isOpen={inboundSettingsOpen}
                onClose={() => setInboundSettingsOpen(false)}
            />
        </div>
    );
}
