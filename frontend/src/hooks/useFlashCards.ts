import { useState, useEffect } from 'react';
import { useDataChannel } from '@livekit/components-react';

export interface FlashcardData {
  title: string;
  value: string;
  id?: string;
}

export function useFlashcards() {
  const [currentCard, setCurrentCard] = useState<FlashcardData | null>(null);
  
  // Listen for the specific topic defined in Python
  const { message } = useDataChannel("ui.flashcard");

  useEffect(() => {
    if (message && message.payload) {
      const decoder = new TextDecoder();
      const strData = decoder.decode(message.payload);
      console.log("📡 RAW SIGNAL RECEIVED:", strData);
      
      try {
        const data = JSON.parse(strData);
        console.log("✅ PARSED FLASHCARD:", data)
        if (data.type === 'flashcard') {
          setCurrentCard({
            title: data.title,
            value: data.value,
            id: data.id
          });

          // Optional: Auto-dismiss after 10 seconds
          const timer = setTimeout(() => setCurrentCard(null), 10000);
          return () => clearTimeout(timer);
        }
      } catch (error) {
        console.error("Failed to parse flashcard data:", error);
      }
    }
  }, [message]);

  const dismiss = () => setCurrentCard(null);

  return { currentCard, dismiss };
}