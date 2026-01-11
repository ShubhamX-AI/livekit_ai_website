import React from 'react';
import { AudioVisualizer } from './AudioVisualizer';
import type { TrackReferenceOrPlaceholder } from '@livekit/components-core';

interface VisualizerSectionProps {
  state: 'speaking' | 'listening' | 'connected' | 'disconnected';
  trackRef?: TrackReferenceOrPlaceholder;
}

export const VisualizerSection: React.FC<VisualizerSectionProps> = ({ state, trackRef }) => {
  const isAgent = state === 'speaking';
  
  // Colors: Emerald (Agent) | Blue (User)
  const themeColor = isAgent ? '#10b981' : '#3b82f6'; 

  return (
    <div className="w-[300px] flex flex-col items-center justify-center relative">
      
      {/* 1. Visualizer Area (The Wave) */}
      <div className="relative w-full h-[48px] flex items-center justify-center">
         {/* Background Glow (Subtle) */}
         <div 
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60%] h-[20px] blur-[25px] opacity-40 transition-colors duration-500 pointer-events-none"
            style={{ backgroundColor: themeColor }}
         />
         
         {/* The Canvas */}
         <div className="w-full h-full animate-fade-in z-10">
            <AudioVisualizer trackRef={trackRef} color={themeColor} />
         </div>
      </div>
      
      {/* 2. Status Text (Perfectly Centered) */}
      <div className="absolute -bottom-4 left-0 right-0 flex items-center justify-center">
        <span 
            className="text-[10px] uppercase tracking-[0.2em] font-bold transition-colors duration-500 text-center whitespace-nowrap"
            style={{ 
              color: themeColor,
              textShadow: `0 0 10px ${themeColor}40` // Subtle text glow
            }}
        >
          {isAgent ? 'INT. AI Speaking' : 'Listening'}
        </span>
      </div>

    </div>
  );
};