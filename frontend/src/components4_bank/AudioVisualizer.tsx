import React, { useEffect, useRef } from 'react';
import type { TrackReferenceOrPlaceholder } from '@livekit/components-core';

interface AudioVisualizerProps {
  trackRef?: TrackReferenceOrPlaceholder;
  color: string;
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ trackRef, color }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(null);
  const analyserRef = useRef<AnalyserNode>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode>(null);
  const audioContextRef = useRef<AudioContext>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    // Setup Audio Context (Singleton-ish)
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    const ctx = audioContextRef.current;

    // Connect Track
    if (trackRef?.publication?.track) {
      const stream = new MediaStream([trackRef.publication.track.mediaStreamTrack]);
      // Ensure context is running
      if (ctx.state === 'suspended') ctx.resume();

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048; // High resolution for smooth volume detection
      analyserRef.current = analyser;

      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);
      sourceRef.current = source;
    }

    // Animation Variables
    let phase = 0;
    
    const draw = () => {
      if (!canvas) return;
      const ctx2d = canvas.getContext('2d');
      if (!ctx2d) return;

      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      // 1. Calculate Volume (RMS)
      let volume = 0;
      if (analyserRef.current) {
        const bufferLength = analyserRef.current.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyserRef.current.getByteTimeDomainData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          const v = (dataArray[i] - 128) / 128;
          sum += v * v;
        }
        volume = Math.sqrt(sum / bufferLength);
      }
      
      // Smooth volume transition (Linear interpolation)
      // If no track (muted/idle), volume is small but non-zero for "breathing" effect
      const targetAmplitude = trackRef ? Math.max(0.1, volume * 4) : 0.1;

      // Clear Canvas
      ctx2d.clearRect(0, 0, width, height);

      // Draw 3 overlapping sine waves for that "Siri" liquid look
      // We use the 'color' prop but vary opacity
      const lines = [
        { color: color, opacity: 1.0, speed: 0.05, freq: 0.02, ampMult: 1.0 },
        { color: color, opacity: 0.5, speed: 0.03, freq: 0.015, ampMult: 0.8 },
        { color: color, opacity: 0.2, speed: 0.02, freq: 0.01, ampMult: 0.6 },
      ];

      lines.forEach((line) => {
        ctx2d.beginPath();
        ctx2d.strokeStyle = line.color;
        ctx2d.lineWidth = 2;
        ctx2d.globalAlpha = line.opacity;

        for (let x = 0; x < width; x++) {
          // Math for the wave:
          // y = Center + Amplitude * sin(x * Frequency + Phase)
          // We apply a "window function" (attenuation) so the wave tapers at the edges
          
          // Window function: 1 at center, 0 at edges (Parabolic)
          const relativeX = (x / width) * 2 - 1; // -1 to 1
          const attenuation = 1 - Math.pow(relativeX, 2); // Parabola opening down

          const y = centerY + 
                    Math.sin(x * line.freq + phase * line.speed) * 
                    (height / 2.5) * 
                    targetAmplitude * 
                    line.ampMult * 
                    attenuation;

          if (x === 0) ctx2d.moveTo(x, y);
          else ctx2d.lineTo(x, y);
        }
        ctx2d.stroke();
      });

      phase += 1.5; // Move the wave forward
      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      // Clean up audio nodes only if they exist
      if (sourceRef.current) {
         sourceRef.current.disconnect(); 
         sourceRef.current = null;
      }
      // Note: We don't close the AudioContext to prevent issues with rapid re-mounting
    };
  }, [trackRef, color]);

  return (
    <canvas 
      ref={canvasRef} 
      width={400} // Higher res width
      height={100} // Taller for amplitude
      className="w-full h-full object-contain"
    />
  );
};