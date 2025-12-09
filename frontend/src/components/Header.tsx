import React from 'react';
import { Sparkles } from 'lucide-react';

interface HeaderProps {
  status: 'speaking' | 'listening' | 'connected' | 'disconnected';
}

export const Header: React.FC<HeaderProps> = ({ status }) => {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 p-6 flex justify-center pointer-events-none">
      <div className="pointer-events-auto bg-white/10 backdrop-blur-md border border-white/20 px-6 py-2 rounded-full shadow-lg flex items-center gap-3 transition-all duration-300">
        <Sparkles className={`w-4 h-4 transition-colors duration-500 ${
          status === 'speaking' ? 'text-indigo-400' : 
          status === 'listening' ? 'text-emerald-400' : 'text-gray-400'
        }`} />
        <span className="font-semibold text-sm text-gray-700 tracking-wide">
          INT. AI
        </span>
      </div>
    </nav>
  );
};