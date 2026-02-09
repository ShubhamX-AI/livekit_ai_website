import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components2_bank/Header';
import { AlertCircle, Sparkles, Settings } from 'lucide-react';
import type { AgentType } from '../types/agent';
import { AgentButton } from '../components2_bank/AgentButton';
import { OutboundCallModal } from '../components2_bank/OutboundCallModal';
import { AgentInteractionModal } from '../components2_bank/AgentInteractionModal';
import { InboundSettingsModal } from '../components2_bank/InboundSettingsModal';

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
    const [selectedAgent, setSelectedAgent] = useState<AgentType>('invoice');

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
        // preserve original behavior: navigate for bank/tour/bandhan_banking, connect for others
        if (agent === 'bank') {
            navigate('/bank');
        } else if (agent === 'tour') {
            navigate('/jharkhand');
        } else if (agent === 'bandhan_banking') {
            navigate('/bandhan_banking');
        } else if (agent === 'ambuja') {
            navigate('/ambuja');
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
        <div className="flex flex-col min-h-screen bg-[#FDFDFF] text-slate-900 font-sans selection:bg-indigo-500/20 antialiased">
            {/* Ambient Background Elements */}
            <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] bg-indigo-100/30 rounded-full blur-[140px]" />
                <div className="absolute -bottom-[20%] -right-[10%] w-[60%] h-[60%] bg-blue-100/30 rounded-full blur-[140px]" />
            </div>

            <Header status="disconnected" />

            {/* Inbound Settings Float */}
            <button
                onClick={() => setInboundSettingsOpen(true)}
                className="fixed top-28 right-8 z-50 p-3 bg-white/60 backdrop-blur-xl border border-slate-200 shadow-xl rounded-2xl text-slate-500 hover:text-indigo-600 hover:scale-105 transition-all duration-300 group"
                title="Inbound Call Settings"
            >
                <Settings size={22} className="group-hover:rotate-45 transition-transform duration-500" />
            </button>

            <main className="flex-1 flex flex-col items-center justify-start pt-32 pb-40 px-6 relative z-10 w-full max-w-7xl mx-auto">

                {/* Hero Section */}
                <div className="text-center space-y-10 mb-28 w-full max-w-5xl animate-fade-in-up">
                    <div className="inline-flex items-center gap-3 px-6 py-2.5 rounded-full bg-white border border-slate-100 shadow-[0_2px_15px_rgba(0,0,0,0.02)] text-sm font-bold text-slate-500 tracking-tight mb-4">
                        <span className="flex h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
                        <Sparkles size={16} className="text-indigo-500" />
                        <span>INTELLIGENT VOICE SOLUTIONS</span>
                    </div>

                    <h1 className="text-5xl sm:text-7xl md:text-[100px] font-black tracking-tighter text-slate-950 leading-[1.1] md:leading-[0.95] mb-4">
                        Speak to your <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-br from-indigo-700 via-blue-600 to-indigo-500">Virtual Workforce.</span>
                    </h1>

                    <p className="text-xl md:text-3xl text-slate-500 max-w-3xl mx-auto leading-relaxed font-normal opacity-80">
                        Deploy specialized AI agents tailored for your business needs.
                        Professional, instant, and human-like interactions.
                    </p>
                </div>

                {error && (
                    <div className="w-full max-w-lg mx-auto mb-20 p-6 rounded-3xl bg-red-50/50 border border-red-100/50 text-red-800 flex items-start gap-5 shadow-2xl backdrop-blur-lg animate-shake">
                        <div className="p-2 bg-red-100 rounded-xl text-red-600">
                            <AlertCircle className="w-6 h-6 flex-shrink-0" />
                        </div>
                        <div className="space-y-1">
                            <p className="font-extrabold text-lg">System Alert</p>
                            <p className="text-base opacity-80 leading-relaxed font-medium">{error}</p>
                        </div>
                    </div>
                )}

                {/* Agents Grid */}
                <div className="w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 animate-fade-in-up [animation-delay:200ms]">
                    <AgentButton
                        label="Invoice Agent"
                        description="Professional billing & accounts management."
                        agentType="invoice"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />

                    <AgentButton
                        label="Restaurant Agent"
                        description="Seamless restaurant booking & hospitality."
                        agentType="restaurant"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />

                    <AgentButton
                        label="Wealth Advisor"
                        description="Check balances & secure financial advice."
                        agentType="bank"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />

                    <AgentButton
                        label="Tour Concierge"
                        description="Bespoke travel planning & local tours."
                        agentType="tour"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />

                    <AgentButton
                        label="Real Estate Agent"
                        description="High-value real estate guidance & tours."
                        agentType="realestate"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />

                    <AgentButton
                        label="Distributor Agent"
                        description="Efficient supply chain coordination."
                        agentType="distributor"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />

                    <AgentButton
                        label="Bandhan Elite"
                        description="Exclusive premium banking experiences."
                        agentType="bandhan_banking"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />

                    <AgentButton
                        label="Ambuja Neotia"
                        description="Luxury residential & lifestyle support."
                        agentType="ambuja"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />

                    <AgentButton
                        label="Hirebot Agent"
                        description="Your spanish agent"
                        agentType="hirebot"
                        onWebCall={handleWebCall}
                        onOutboundCall={handleOutboundCall}
                        onMobileClick={handleMobileClick}
                        disabled={connecting}
                    />
                </div>

                {/* Bottom Trust Section */}
                <div className="mt-40 flex flex-col items-center gap-12">
                    <p className="text-xs font-black text-slate-300 tracking-[0.3em] uppercase">Powered and secured by</p>
                    <div className="flex flex-wrap justify-center gap-12 text-sm font-bold text-slate-400">
                        <span className="hover:text-indigo-600 transition-colors">LiveKit Agents</span>
                        <span className="hover:text-blue-500 transition-colors">OpenAI Realtime</span>
                        <span className="hover:text-indigo-400 transition-colors">Cartesia</span>
                        <span className="hover:text-slate-800 transition-colors">WebRTC 2.0</span>
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

            <style dangerouslySetInnerHTML={{
                __html: `
                  @keyframes fade-in-up {
                      from { opacity: 0; transform: translateY(60px); }
                      to { opacity: 1; transform: translateY(0); }
                  }
                  .animate-fade-in-up {
                      animation: fade-in-up 1.2s cubic-bezier(0.23, 1, 0.32, 1) forwards;
                  }
                  @keyframes shake {
                      0%, 100% { transform: translateX(0); }
                      25% { transform: translateX(-8px); }
                      75% { transform: translateX(8px); }
                  }
                  .animate-shake {
                      animation: shake 0.5s ease-in-out 0s 2;
                  }
                `
            }} />
        </div>
    );
}
