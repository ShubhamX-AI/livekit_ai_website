import React from 'react';
import { Sparkles, Activity } from 'lucide-react';

interface HeaderProps {
  status: 'speaking' | 'listening' | 'connected' | 'disconnected';
}

export const Header: React.FC<HeaderProps> = ({ status }) => {
  // Logic: AI Speaking = Green, User/Listening = Blue
  const isAgent = status === 'speaking';
  const isListening = status === 'listening';

  return (
    <div className="fixed top-6 left-6 z-50 pointer-events-none select-none">
      <div 
        className={`
          pointer-events-auto backdrop-blur-xl border shadow-[0_4px_20px_rgba(0,0,0,0.05)] 
          px-4 py-2.5 rounded-full flex items-center gap-3 transition-all duration-500
          ${isAgent 
             ? 'bg-emerald-50/90 border-emerald-200/50' 
             : isListening 
                ? 'bg-blue-50/90 border-blue-200/50' 
                : 'bg-white/80 border-white/40'}
        `}
      >
        <div className={`
          relative flex items-center justify-center w-7 h-7 rounded-full transition-colors duration-500
          ${isAgent ? 'bg-emerald-100 text-emerald-600' : isListening ? 'bg-blue-100 text-blue-600' : 'bg-zinc-100 text-zinc-400'}
        `}>
           {isAgent ? (
             <Sparkles className="w-3.5 h-3.5 animate-pulse" strokeWidth={2.5} />
           ) : (
             <Activity className="w-3.5 h-3.5" strokeWidth={2.5} />
           )}
        </div>
        
        <div className="flex flex-col">
           <span className={`font-bold text-[11px] tracking-wider uppercase transition-colors duration-500 ${isAgent ? 'text-emerald-700' : isListening ? 'text-blue-700' : 'text-zinc-600'}`}>
             INT. Intelligence
           </span>
           <span className="text-[9px] text-zinc-400 font-medium leading-none mt-0.5">
             {isAgent ? 'Voice Active' : isListening ? 'Listening...' : 'Standby'}
           </span>
        </div>
      </div>
    </div>
  );
};