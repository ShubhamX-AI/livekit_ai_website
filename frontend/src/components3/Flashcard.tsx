import React from 'react';
import { Lightbulb } from 'lucide-react';

interface FlashcardData {
  title: string;
  value: string;
}

interface FlashcardBlockProps {
  data: FlashcardData;
}

export const FlashcardBlock: React.FC<FlashcardBlockProps> = ({ data }) => {
  return (
    <div className="max-w-xs w-full animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="
        relative overflow-hidden
        bg-emerald-50/50 backdrop-blur-sm
        border border-emerald-100 
        shadow-sm hover:shadow-md transition-shadow
        rounded-2xl p-5
      ">
        {/* Decorator Background */}
        <div className="absolute -right-4 -top-4 w-20 h-20 bg-emerald-100 rounded-full blur-2xl opacity-60 pointer-events-none" />

        <div className="flex items-center gap-2 mb-3">
          <div className="p-1.5 bg-emerald-100 rounded-lg text-emerald-600">
            <Lightbulb size={16} fill="currentColor" className="opacity-80" />
          </div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-600">
            Key Insight
          </span>
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