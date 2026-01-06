import React, { useMemo, useCallback, useState } from 'react';
import {
  useVoiceAssistant,
  useLocalParticipant,
  useRoomContext,
} from '@livekit/components-react';
import { Track } from 'livekit-client';
import { 
  Mic, 
  MicOff, 
  PhoneOff, 
  Bell, 
  User, 
  Eye, 
  IndianRupee, 
  FileText, 
  Smartphone, 
  Receipt, 
  Home, 
  Wallet, 
  Headphones,
  LayoutDashboard,
  PieChart,
  Settings
} from 'lucide-react';

import { VisualizerSection } from './Visualizer';

// --- Types & Helpers ---
type VisualizerState = 'speaking' | 'listening' | 'connected' | 'disconnected';

function mapAgentToVisualizerState(s: string): VisualizerState {
  if (s === 'connecting') return 'connected';
  if (s === 'speaking' || s === 'listening' || s === 'connected' || s === 'disconnected') return s as VisualizerState;
  return 'connected';
}

const BankingVoiceAssistant: React.FC = () => {
  // --- LiveKit Hooks ---
  const { state, audioTrack: agentTrack } = useVoiceAssistant();
  const { localParticipant, microphoneTrack } = useLocalParticipant();
  const room = useRoomContext();
  const [isMicMuted, setIsMicMuted] = useState(false);

  // --- Audio Track Logic ---
  const userTrackRef = useMemo(() => {
    if (!localParticipant) return undefined;
    return {
      participant: localParticipant,
      source: Track.Source.Microphone,
      publication: microphoneTrack,
    };
  }, [localParticipant, microphoneTrack]);

  const agentTrackRef = useMemo(() => {
    if (!agentTrack || !agentTrack.participant || !agentTrack.publication) return undefined;
    return {
      participant: agentTrack.participant,
      source: Track.Source.Unknown,
      publication: agentTrack.publication,
    };
  }, [agentTrack]);

  const isAgentSpeaking = state === 'speaking';
  const activeTrack = isAgentSpeaking ? agentTrackRef : (!isMicMuted ? userTrackRef : undefined);
  const visualizerState = mapAgentToVisualizerState(state as string);

  // --- Handlers ---
  const toggleMic = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation(); 
    e.preventDefault(); 
    if (!localParticipant) return;
    const newVal = !isMicMuted;
    try {
      await localParticipant.setMicrophoneEnabled(!newVal);
      setIsMicMuted(newVal);
    } catch (error) {
      console.error("Error toggling microphone:", error);
    }
  }, [localParticipant, isMicMuted]);

  const handleDisconnect = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    room?.disconnect();
  }, [room]);

  // --- UI Render ---
  return (
    <div className="min-h-screen w-full bg-[#0B1426] text-white font-sans flex flex-col md:flex-row">
      
      {/* 
        ========================================
        SIDEBAR NAVIGATION (Desktop Only)
        Hidden on mobile, visible on md+ screens
        ========================================
      */}
      <aside className="hidden md:flex flex-col w-64 bg-[#080f1e] border-r border-white/5 h-screen sticky top-0 z-20">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full border border-[#D4AF37] flex items-center justify-center text-[#D4AF37] bg-[#D4AF37]/10">
             <span className="text-2xl font-serif font-bold pt-1">L</span>
          </div>
          <div className="flex flex-col">
              <span className="text-lg font-bold text-[#D4AF37] leading-none">लक्ष्मी बैंक</span>
              <span className="text-[10px] text-slate-400 tracking-wider">PREMIUM</span>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 flex flex-col gap-2">
            <DesktopNavItem icon={<LayoutDashboard size={20} />} label="Dashboard" active />
            <DesktopNavItem icon={<Wallet size={20} />} label="Accounts" />
            <DesktopNavItem icon={<IndianRupee size={20} />} label="Transfers" />
            <DesktopNavItem icon={<PieChart size={20} />} label="Analytics" />
            <DesktopNavItem icon={<Settings size={20} />} label="Settings" />
        </nav>

        <div className="p-4 border-t border-white/5">
            <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 cursor-pointer">
                <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center">
                    <User size={20} className="text-slate-300"/>
                </div>
                <div className="flex flex-col overflow-hidden">
                    <span className="text-sm font-medium truncate">Priya Sharma</span>
                    <span className="text-xs text-slate-400 truncate">priya@example.com</span>
                </div>
            </div>
        </div>
      </aside>

      {/* 
        ========================================
        MAIN CONTENT AREA
        Full width on mobile, remaining width on desktop
        ========================================
      */}
      <main className="flex-1 flex flex-col min-h-screen relative pb-32 md:pb-10">
        
        {/* TOP HEADER (Mobile & Desktop) */}
        <header className="sticky top-0 z-10 bg-[#0B1426]/95 backdrop-blur-md border-b border-white/5 px-6 py-4 flex items-center justify-between">
            {/* Mobile Logo Only */}
            <div className="md:hidden flex items-center gap-2">
                <div className="w-8 h-8 rounded-full border border-[#D4AF37] flex items-center justify-center text-[#D4AF37]">
                    <span className="text-xl font-serif font-bold">L</span>
                </div>
                <span className="font-bold text-[#D4AF37]">Laxmi Bank</span>
            </div>

            {/* Desktop Welcome Message */}
            <div className="hidden md:block">
                <h1 className="text-xl font-semibold text-white">Good Morning, Priya! 👋</h1>
                <p className="text-xs text-slate-400">Here's your financial overview.</p>
            </div>

            <div className="flex items-center gap-4 text-slate-300">
                <button className="p-2 hover:bg-white/5 rounded-full transition-colors relative">
                    <Bell size={20} />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border border-[#0B1426]"></span>
                </button>
                <div className="md:hidden">
                    <User size={20} />
                </div>
                <button className="hidden md:flex items-center gap-2 text-xs font-medium bg-[#1A263E] px-3 py-1.5 rounded-full border border-white/5 hover:border-[#D4AF37] transition-colors">
                    <Headphones size={14} /> Help Support
                </button>
            </div>
        </header>

        {/* SCROLLABLE DASHBOARD CONTENT */}
        <div className="p-4 md:p-8 max-w-7xl mx-auto w-full">
            
            {/* Grid Layout: Stacks on mobile, 3 columns on desktop */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                
                {/* 1. BALANCE CARD (Full on mobile, 7 cols on desktop) */}
                <div className="lg:col-span-7 bg-gradient-to-br from-[#1A263E] to-[#0f1729] rounded-[32px] p-6 md:p-8 border border-white/5 shadow-2xl relative overflow-hidden group">
                     {/* Decorative Background */}
                    <div className="absolute top-0 right-0 w-64 h-64 bg-[#D4AF37]/5 rounded-full blur-[80px] -mr-20 -mt-20 pointer-events-none group-hover:bg-[#D4AF37]/10 transition-colors duration-700"></div>

                    <div className="relative z-10 flex flex-col h-full justify-between">
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <h2 className="text-sm md:text-base text-slate-400 mb-1">Total Balance</h2>
                                <div className="flex items-center gap-3">
                                    <h1 className="text-3xl md:text-5xl font-bold text-white tracking-tight">₹ 1,85,670.50</h1>
                                    <button className="text-slate-500 hover:text-white transition-colors"><Eye size={18} /></button>
                                </div>
                            </div>
                            <div className="w-12 h-12 rounded-2xl bg-[#D4AF37]/20 flex items-center justify-center text-[#D4AF37]">
                                <Wallet size={24} />
                            </div>
                        </div>

                        <div className="flex gap-4 mt-4">
                            <button className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-[#D4AF37] hover:bg-[#bfa03a] text-[#0B1426] px-6 py-3 rounded-xl text-sm font-bold transition-all shadow-[0_0_20px_rgba(212,175,55,0.2)]">
                                Add Money
                            </button>
                            <button className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 px-6 py-3 rounded-xl text-sm text-slate-300 border border-white/10 transition-colors">
                                View Details
                            </button>
                        </div>
                    </div>
                </div>

                {/* 2. QUICK ACTIONS (Horizontal scroll on mobile, Grid on desktop) */}
                <div className="lg:col-span-5 bg-[#16293F]/50 md:bg-[#16293F] rounded-[32px] p-6 border border-white/5">
                    <h3 className="text-sm font-semibold text-slate-400 mb-6">Quick Actions</h3>
                    <div className="grid grid-cols-4 gap-4">
                         <ActionButton icon={<IndianRupee size={24} />} label="Transfer" />
                         <ActionButton icon={<Receipt size={24} />} label="Pay Bills" />
                         <ActionButton icon={<Smartphone size={24} />} label="Recharge" />
                         <ActionButton icon={<FileText size={24} />} label="History" />
                         {/* Extra desktop items */}
                         <div className="hidden md:flex flex-col items-center gap-2 group cursor-pointer">
                            <div className="w-16 h-16 rounded-[24px] bg-[#1A263E] border border-white/5 text-slate-400 flex items-center justify-center shadow-lg group-hover:bg-[#D4AF37] group-hover:text-[#0B1426] transition-all">
                                <Settings size={24} />
                            </div>
                            <span className="text-xs text-slate-400 font-medium group-hover:text-white">More</span>
                         </div>
                    </div>
                </div>

                {/* 3. RECENT TRANSACTIONS (Full width) */}
                <div className="lg:col-span-12 bg-[#111e33] rounded-[32px] p-6 md:p-8 border border-white/5">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-lg font-semibold text-white">Recent Transactions</h3>
                        <button className="text-xs text-[#D4AF37] font-medium hover:underline">View All</button>
                    </div>

                    <div className="flex flex-col gap-4">
                        <TransactionItem 
                            icon={<FileText size={20}/>}
                            bg="bg-rose-500/10"
                            color="text-rose-500"
                            title="Credit Card Bill" 
                            amount="- ₹ 15,000" 
                            sub="Due. 15/12/23" 
                            date="Today, 10:30 AM"
                            isDebit
                        />
                        <TransactionItem 
                            icon={<Home size={20}/>}
                            bg="bg-emerald-500/10"
                            color="text-emerald-500"
                            title="Grocery Mart" 
                            amount="- ₹ 1,250" 
                            sub="Supermarket Purchase" 
                            date="Yesterday, 12:30 PM"
                            isDebit
                        />
                        <TransactionItem 
                            icon={<IndianRupee size={20}/>}
                            bg="bg-blue-500/10"
                            color="text-blue-500"
                            title="Received from Ravi" 
                            amount="+ ₹ 5,000" 
                            sub="UPI Transfer" 
                            date="Dec 11, 10:00 AM"
                        />
                    </div>
                </div>

            </div>
        </div>
      </main>

      {/* 
        ========================================
        FLOATING VOICE ASSISTANT 
        Positioned fixed bottom-center for both, 
        but slightly higher on mobile to clear nav
        ========================================
      */}
      <div className="fixed bottom-24 md:bottom-10 left-0 right-0 flex justify-center z-50 pointer-events-none">
        <div 
          className="
            flex items-center justify-between gap-3 px-4 md:px-6 py-3 rounded-full pointer-events-auto
            w-[90%] max-w-[340px] md:max-w-[400px]
            bg-[#151f32]/90 backdrop-blur-2xl 
            border border-[#D4AF37]/20 shadow-[0_8px_32px_rgba(0,0,0,0.4)]
            transition-all duration-500 hover:border-[#D4AF37]/50
          "
        >
          {/* Mic Toggle */}
          <button 
            type="button" 
            onClick={toggleMic}
            className={`
              shrink-0 w-12 h-12 md:w-14 md:h-14 flex items-center justify-center rounded-full transition-all duration-300
              ${isMicMuted 
                ? 'bg-slate-700 text-slate-400 hover:bg-slate-600' 
                : 'bg-[#D4AF37] text-[#0B1426] hover:scale-105 shadow-[0_0_15px_rgba(212,175,55,0.4)]'}
            `}
          >
            {isMicMuted ? <MicOff size={20}/> : <Mic size={24}/>}
          </button>

          {/* Divider */}
          <div className="h-8 w-[1px] bg-white/10 shrink-0" />
          
          {/* Visualizer Section */}
          <div className="flex-1 flex items-center justify-center min-w-[100px]">
             <VisualizerSection 
                state={visualizerState}
                trackRef={activeTrack}
             />
          </div>
          
          {/* Divider */}
          <div className="h-8 w-[1px] bg-white/10 shrink-0" />

          {/* Hangup */}
          <button 
            type="button"
            onClick={handleDisconnect}
            className="shrink-0 w-12 h-12 md:w-14 md:h-14 flex items-center justify-center rounded-full bg-rose-500/10 text-rose-500 border border-rose-500/20 hover:bg-rose-500 hover:text-white transition-all duration-300"
          >
            <PhoneOff size={20}/>
          </button>
        </div>
      </div>

      {/* 
        ========================================
        BOTTOM NAVIGATION (Mobile Only)
        Hidden on md+ screens
        ========================================
      */}
      <div className="md:hidden fixed bottom-0 w-full bg-[#0B1426]/95 backdrop-blur-xl border-t border-white/5 pb-6 pt-3 px-8 flex justify-between items-center z-40">
        <NavIcon icon={<Home size={24} />} label="Home" active />
        <NavIcon icon={<Wallet size={24} />} label="Accounts" />
        <NavIcon icon={<Headphones size={24} />} label="Support" />
      </div>

    </div>
  );
};

// --- Sub Components ---

const DesktopNavItem: React.FC<{icon: React.ReactNode, label: string, active?: boolean}> = ({ icon, label, active }) => (
    <a href="#" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${active ? 'bg-[#D4AF37]/10 text-[#D4AF37]' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
        {icon}
        <span className="font-medium text-sm">{label}</span>
    </a>
);

const ActionButton: React.FC<{icon: React.ReactNode, label: string}> = ({ icon, label }) => (
    <div className="flex flex-col items-center gap-2 cursor-pointer group">
        <div className="w-14 h-14 md:w-16 md:h-16 rounded-[24px] bg-[#1A263E] border border-white/5 text-[#D4AF37] flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-200 group-hover:bg-[#D4AF37] group-hover:text-[#0B1426]">
            {icon}
        </div>
        <span className="text-[11px] md:text-xs text-center text-slate-400 font-medium leading-tight group-hover:text-white transition-colors">{label}</span>
    </div>
);

const TransactionItem: React.FC<{
    title: string, 
    amount: string, 
    sub: string, 
    date: string,
    icon: React.ReactNode, 
    bg: string, 
    color: string,
    isDebit?: boolean
}> = ({ title, amount, sub, date, icon, bg, color, isDebit }) => (
    <div className="flex justify-between items-center group cursor-pointer hover:bg-white/5 p-3 rounded-2xl transition-colors border border-transparent hover:border-white/5">
        <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-full ${bg} ${color} flex items-center justify-center`}>
                {icon}
            </div>
            <div className="flex flex-col">
                <span className="text-sm md:text-base font-medium text-slate-200">{title}</span>
                <span className="text-xs text-slate-500 mt-0.5">{sub}</span>
            </div>
        </div>
        <div className="flex flex-col items-end">
            <span className={`text-sm md:text-base font-bold ${isDebit ? 'text-white' : 'text-emerald-400'}`}>{amount}</span>
             <span className="text-[10px] md:text-xs text-slate-500 mt-1">{date}</span>
        </div>
    </div>
);

const NavIcon: React.FC<{icon: React.ReactNode, label: string, active?: boolean}> = ({ icon, label, active }) => (
    <div className={`flex flex-col items-center gap-1 cursor-pointer hover:text-[#D4AF37] transition-colors ${active ? 'text-[#D4AF37]' : 'text-slate-500'}`}>
        {icon}
        <span className="text-[10px] font-medium tracking-wide">{label}</span>
        {active && <div className="w-1 h-1 rounded-full bg-[#D4AF37] mt-1" />}
    </div>
);

export default BankingVoiceAssistant;