import { X, Globe, Phone } from 'lucide-react';
import type { AgentType } from '../types/agent';

interface AgentInteractionModalProps {
    isOpen: boolean;
    onClose: () => void;
    agentType: AgentType;
    onWebCall: (agent: AgentType) => void;
    onOutboundCall: (agent: AgentType) => void;
}

export function AgentInteractionModal({
    isOpen,
    onClose,
    agentType,
    onWebCall,
    onOutboundCall
}: AgentInteractionModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative w-full max-w-sm bg-white/90 backdrop-blur-xl border border-white/20 shadow-2xl rounded-3xl overflow-hidden animate-in zoom-in-95 duration-300">

                <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-white/50">
                    <div>
                        <h3 className="text-lg font-semibold text-gray-900 leading-none">Connect with Agent</h3>
                        <p className="text-sm text-gray-500 mt-1 capitalize">{agentType} Agent</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="p-6 flex flex-col gap-4">
                    <button
                        onClick={() => {
                            onWebCall(agentType);
                            onClose();
                        }}
                        className="w-full bg-white border-2 border-primary text-primary hover:bg-primary-50 p-4 rounded-xl font-semibold shadow-sm flex items-center justify-between group transition-all"
                    >
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
                                <Globe size={20} />
                            </div>
                            <span className="text-lg">Web Call</span>
                        </div>
                    </button>

                    <button
                        onClick={() => {
                            onOutboundCall(agentType);
                            onClose();
                        }}
                        className="w-full bg-primary text-white hover:bg-primary-hover p-4 rounded-xl font-semibold shadow-lg shadow-primary/20 flex items-center justify-between group transition-all"
                    >
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-white group-hover:scale-110 transition-transform">
                                <Phone size={20} />
                            </div>
                            <span className="text-lg">Phone Call</span>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    );
}
