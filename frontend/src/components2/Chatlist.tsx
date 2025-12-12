import React, { useEffect, useRef, useState } from 'react';

export interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  isInterim?: boolean;
}

interface ChatListProps {
  messages: ChatMessage[];
}

// --------------------------------------------------------------------------
// Helper: Typewriter Component for Smooth Text Rendering
// --------------------------------------------------------------------------
const TypewriterText: React.FC<{ text: string; speed?: number }> = ({ text, speed = 10 }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    let i = 0;
    setDisplayedText(''); // Reset on new text
    
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
export const ChatList: React.FC<ChatListProps> = ({ messages }) => {
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
      <div className="max-w-3xl mx-auto flex flex-col pt-24 pb-48 gap-6"> 
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
          
          return (
            <div 
              key={msg.id} 
              // FORCE ALIGNMENT: User -> Right (justify-end), Agent -> Left (justify-start)
              className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div 
                className={`
                  relative max-w-[80%] px-6 py-4 text-[15px] leading-relaxed rounded-[24px]
                  shadow-sm transition-all duration-300 border
                  ${isInterim ? 'opacity-80 scale-[0.99]' : 'opacity-100 scale-100 animate-fade-in-up'}
                  
                  /* --- NEW COLOR THEME --- */
                  /* USER = BLUE | AI = GREEN (Emerald) */
                  ${isUser 
                    ? `
                        bg-gradient-to-br from-blue-500 to-blue-600
                        text-white
                        border-transparent
                        rounded-tr-sm
                      `
                    : `
                        bg-white
                        text-zinc-800
                        border-zinc-200
                        rounded-tl-sm
                      `
                  }
                `}
              >
                 {/* Agent Name Tag */}
                 {!isUser && (
                   <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 mb-1 opacity-80">
                     INT. AI
                   </div>
                 )}

                 {/* Text Content */}
                 <div className={isUser ? 'font-medium' : 'font-normal'}>
                    {/* Only use Typewriter for final AI messages to avoid flickering on interim updates */}
                    {(!isUser && !isInterim) ? (
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