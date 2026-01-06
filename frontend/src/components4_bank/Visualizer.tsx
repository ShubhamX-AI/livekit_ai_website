import React from 'react';
// Make sure to import your actual AudioVisualizer component path
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
    // Changed w-[300px] to flexible width with bounds
    <div className="flex-1 w-full max-w-[200px] sm:max-w-[300px] flex flex-col items-center justify-center relative transition-all duration-300">
      
      {/* 1. Visualizer Area (The Wave) */}
      <div className="relative w-full h-[40px] sm:h-[48px] flex items-center justify-center">
         {/* Background Glow (Subtle) */}
         <div 
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[20px] blur-[20px] opacity-40 transition-colors duration-500 pointer-events-none"
            style={{ backgroundColor: themeColor }}
         />
         
         {/* The Canvas */}
         <div className="w-full h-full animate-fade-in z-10 opacity-90">
             {/* Pass width/height styles to canvas via container if needed, or rely on AudioVisualizer auto-resize */}
            <AudioVisualizer trackRef={trackRef} color={themeColor} />
         </div>
      </div>
      
      {/* 2. Status Text */}
      <div className="absolute -bottom-3 left-0 right-0 flex items-center justify-center">
        <span 
            className="text-[9px] sm:text-[10px] uppercase tracking-[0.2em] font-bold transition-colors duration-500 text-center whitespace-nowrap"
            style={{ 
              color: themeColor,
              textShadow: `0 0 10px ${themeColor}40`
            }}
        >
          {isAgent ? 'INT. AI Speaking' : 'Listening'}
        </span>
      </div>

    </div>
  );
};