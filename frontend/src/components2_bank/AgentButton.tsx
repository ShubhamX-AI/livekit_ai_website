import { Phone, Globe, ArrowRight } from 'lucide-react';
import type { AgentType } from '../types/agent';

interface AgentButtonProps {
    label: string;
    description?: string; // Added description for card layout
    agentType: AgentType;
    onWebCall: (agent: AgentType) => void;
    onOutboundCall: (agent: AgentType) => void;
    onMobileClick: (agent: AgentType) => void;
    disabled?: boolean;
    hideActions?: boolean; // New prop to hide Web/Call buttons
}

export function AgentButton({ label, description, agentType, onWebCall, onOutboundCall, onMobileClick, disabled, hideActions }: AgentButtonProps) {
    return (
        <div
            onClick={() => hideActions && onMobileClick(agentType)}
            className={`group relative w-full bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col gap-4 transition-all duration-300 hover:shadow-xl hover:border-primary/20 hover:-translate-y-1 overflow-hidden ${hideActions ? 'cursor-pointer' : ''}`}
        >

            {/* Hover Gradient Effect */}
            <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-primary/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

            {/* Header / Title */}
            <div className="relative z-10 flex justify-between items-start">
                <div className="space-y-1">
                    <h3 className="font-bold text-lg text-gray-800 group-hover:text-primary transition-colors">{label}</h3>
                    {description && <p className="text-xs text-gray-500 line-clamp-2">{description}</p>}
                </div>
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary transform group-hover:scale-110 transition-transform">
                    <ArrowRight size={16} className="-rotate-45 group-hover:rotate-0 transition-transform duration-300" />
                </div>
            </div>

            {/* Actions (Desktop) */}
            {!hideActions && (
                <div className="relative z-10 hidden md:grid grid-cols-2 gap-3 mt-auto pt-2">
                    <button
                        onClick={(e) => { e.stopPropagation(); onWebCall(agentType); }}
                        disabled={disabled}
                        className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium bg-gray-50 text-gray-600 hover:bg-primary hover:text-white transition-all duration-200 border border-transparent hover:border-primary/20"
                    >
                        <Globe size={16} />
                        <span>Web</span>
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); onOutboundCall(agentType); }}
                        disabled={disabled}
                        className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium bg-gray-50 text-gray-600 hover:bg-green-600 hover:text-white transition-all duration-200 border border-transparent hover:border-green-600/20"
                    >
                        <Phone size={16} />
                        <span>Call</span>
                    </button>
                </div>
            )}

            {/* Mobile Click Overlay / Card Click Overlay for hideActions */}
            <button
                onClick={() => onMobileClick(agentType)}
                className={`${!hideActions ? 'md:hidden' : ''} absolute inset-0 z-20 w-full h-full cursor-pointer`}
                aria-label={`Select ${label}`}
            />
        </div>
    );
}
