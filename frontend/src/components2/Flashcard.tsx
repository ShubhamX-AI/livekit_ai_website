import React from 'react';
import { X, Lightbulb } from 'lucide-react';
import type { FlashcardData } from '../hooks/useFlashCards';

interface FlashcardProps {
  data: FlashcardData | null;
  onDismiss: () => void;
}

export const FlashcardOverlay: React.FC<FlashcardProps> = ({ data, onDismiss }) => {
  if (!data) return null;

  return (
    <div className="absolute top-24 right-4 z-40 max-w-xs animate-in fade-in slide-in-from-top-4 duration-500">
      <div className="
        relative overflow-hidden
        bg-white/90 backdrop-blur-xl 
        border border-emerald-100 
        shadow-[0_8px_30px_rgb(0,0,0,0.12)]
        rounded-2xl p-5
      ">
        {/* Decorator Background */}
        <div className="absolute -right-4 -top-4 w-20 h-20 bg-emerald-50 rounded-full blur-2xl opacity-60 pointer-events-none" />

        <div className="flex justify-between items-start mb-2 relative">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-emerald-100 rounded-lg text-emerald-600">
              <Lightbulb size={16} fill="currentColor" className="opacity-80" />
            </div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-600">
              Insight
            </span>
          </div>
          
          <button 
            onClick={onDismiss}
            className="text-zinc-400 hover:text-zinc-600 transition-colors p-1 hover:bg-zinc-100 rounded-full"
          >
            <X size={16} />
          </button>
        </div>

        <h3 className="text-zinc-900 font-semibold text-lg leading-tight mb-2 relative">
          {data.title}
        </h3>
        
        <p className="text-zinc-600 text-sm leading-relaxed relative">
          {data.value}
        </p>
      </div>
    </div>
  );
};