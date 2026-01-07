import React, { useEffect, useRef, useState } from 'react';
import { FlashcardBlock } from './Flashcard';

// 1. UPDATE THE INTERFACE HERE
export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  // New fields for handling Flashcards
  type: 'text' | 'flashcard';
  text?: string;               // Text is now optional (flashcards might not have text)
  cardData?: {                 // Data for the flashcard
    title: string;
    value: string;
  };
  isInterim?: boolean;
  timestamp?: number;
}

interface ChatListProps {
  messages: ChatMessage[];
}

// --------------------------------------------------------------------------
// Helper: Typewriter Component
// --------------------------------------------------------------------------
const TypewriterText: React.FC<{ text: string; speed?: number }> = ({ text, speed = 10 }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    let i = 0;
    setDisplayedText('');

    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayedText((prev) => prev + text.charAt(i));
        i++;
      } else {
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return <span>{displayedText}</span>;
};

// --------------------------------------------------------------------------
// Main ChatList Component
// --------------------------------------------------------------------------
export const ChatList: React.FC<ChatListProps & { compact?: boolean }> = ({ messages, compact = false }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div
      className="flex-1 w-full overflow-y-auto px-4 custom-scrollbar"
      style={{
        maskImage: 'linear-gradient(to bottom, transparent 0%, black 5%, black 85%, transparent 100%)',
        WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 5%, black 85%, transparent 100%)'
      }}
    >
      <div className={`mx-auto flex flex-col gap-6 ${compact ? 'pt-4 pb-2 max-w-full' : 'max-w-3xl pt-24 pb-48'}`}>
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4 opacity-30">
            <div className="w-12 h-1 bg-zinc-300 rounded-full" />
            <p className="text-sm text-zinc-500 font-medium font-mono uppercase tracking-widest">
              System Ready
            </p>
          </div>
        )}

        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          const isInterim = msg.isInterim;

          // --- FLASHCARD RENDER ---
          // Now TypeScript knows 'type' and 'cardData' exist because we updated the interface above
          if (msg.type === 'flashcard' && msg.cardData) {
            return (
              <div key={msg.id} className="flex w-full justify-start pl-4 animate-in fade-in slide-in-from-bottom-2">
                {/* Render the Flashcard Component Inline */}
                <FlashcardBlock data={msg.cardData} />
              </div>
            );
          }

          // --- TEXT RENDER (Standard) ---
          // We only render this block if there is actual text to show
          if (!msg.text) return null;

          return (
            <div
              key={msg.id}
              className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`
                  relative max-w-[80%] px-6 py-4 text-[15px] leading-relaxed rounded-[24px]
                  shadow-sm transition-all duration-300 border
                  ${isInterim ? 'opacity-80 scale-[0.99]' : 'opacity-100 scale-100 animate-fade-in-up'}
                  
                  ${isUser
                    ? `bg-gradient-to-br from-blue-500 to-blue-600 text-white border-transparent rounded-tr-sm`
                    : `bg-white text-zinc-800 border-zinc-200 rounded-tl-sm`
                  }
                `}
              >
                {!isUser && (
                  <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 mb-1 opacity-80">
                    INT. AI
                  </div>
                )}

                <div className={isUser ? 'font-medium' : 'font-normal'}>
                  {(!isUser && !isInterim && msg.text) ? (
                    <TypewriterText text={msg.text} speed={15} />
                  ) : (
                    msg.text
                  )}
                </div>
              </div>
            </div>
          );
        })}

        <div ref={bottomRef} className="h-4" />
      </div>
    </div>
  );
};