import React from 'react';
import {
    Menu,
    User,
    Cloud,
    Thermometer,
    Accessibility,
    Moon,
    MoveUpRight,
    Download,
    Facebook,
    Twitter,
    Instagram,
    Youtube,
    ArrowLeft
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import jharkhandLogo from '../../assets/tour/jharkhand-logo.png';

export const JharkhandTourismUI: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
    const navigate = useNavigate();

    return (
        <div className="relative w-full h-screen bg-black font-sans overflow-hidden flex flex-col">

            {/* BACKGROUND IMAGE (Patratu Valley) */}
            <div className="absolute inset-0 z-0">
                <img
                    src="https://images.unsplash.com/photo-1506744038136-46273834b3fb?q=80&w=2070&auto=format&fit=crop"
                    alt="Jharkhand Nature"
                    className="w-full h-full object-cover"
                />
                {/* Overlay Gradient for readability */}
                <div className="absolute inset-0 bg-gradient-to-r from-black/70 via-black/30 to-transparent"></div>
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/50"></div>
            </div>

            {/* HEADER */}
            <header className="relative z-50 w-full flex items-center justify-between px-4 md:px-10 py-3 border-b border-white/10 bg-gradient-to-b from-black/80 to-transparent shrink-0">
                {/* Logo Section */}
                <div className="flex items-center gap-3">
                    {/* Back Button (Mobile & Desktop) */}
                    <button
                        onClick={() => navigate('/')}
                        className="p-2 -ml-2 hover:bg-white/10 rounded-full transition-colors text-slate-400 hover:text-white"
                        title="Back to Home"
                    >
                        <ArrowLeft size={20} />
                    </button>

                    {/* Jharkhand Tourism Logo */}
                    <div className="flex items-center gap-3">
                        <img
                            src={jharkhandLogo}
                            alt="Jharkhand Tourism"
                            className="h-12 w-auto md:h-14 drop-shadow-lg"
                        />
                    </div>
                </div>

                {/* Desktop Navigation Tools */}
                <div className="hidden xl:flex items-center gap-6 text-xs font-medium text-white/90">
                    <a href="#" className="hover:text-[#F4A024] transition-colors">Skip to Main Content</a>
                    <span className="text-white/30">|</span>

                    {/* Font Resizer */}
                    <div className="flex items-center gap-2">
                        <span className="cursor-pointer hover:text-[#F4A024]">A-</span>
                        <span className="bg-white/20 px-1.5 py-0.5 rounded text-white cursor-pointer">A</span>
                        <span className="cursor-pointer hover:text-[#F4A024]">A+</span>
                    </div>
                    <span className="text-white/30">|</span>

                    {/* Dark Mode */}
                    <button className="hover:text-[#F4A024]"><Moon size={16} /></button>
                    <span className="text-white/30">|</span>

                    {/* Accessibility */}
                    <button className="flex items-center gap-1 hover:text-[#F4A024]">
                        <Accessibility size={16} />
                        <span>More</span>
                    </button>

                    {/* Weather Widget */}
                    <div className="flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1.5 rounded border border-white/10">
                        <Thermometer size={14} className="text-[#F4A024]" />
                        <span>27°C</span>
                        <Cloud size={14} className="text-sky-300 fill-current" />
                    </div>

                    {/* SOS Button */}
                    <button className="bg-[#F4A024] hover:bg-[#d68515] text-black font-bold px-6 py-2 rounded flex items-center gap-2 transition-all transform hover:scale-105 shadow-[0_0_15px_rgba(244,160,36,0.5)]">
                        SOS <MoveUpRight size={14} strokeWidth={3} />
                    </button>

                    <span className="text-white/30">|</span>
                    <button className="hover:text-[#F4A024]"><User size={20} /></button>
                    <span className="text-white/30">|</span>
                    <button className="hover:text-[#F4A024]"><Menu size={28} /></button>
                </div>

                {/* Mobile Menu Button */}
                <div className="xl:hidden flex items-center gap-4">
                    <button className="bg-[#F4A024] text-black text-xs font-bold px-3 py-1.5 rounded">SOS</button>
                    <Menu size={24} className="text-white" />
                </div>
            </header>

            {/* MAIN CONTENT */}
            <main className="relative z-10 flex-1 flex flex-col justify-center px-6 md:px-16 py-8 overflow-hidden">

                {/* Hero Text Section - Centered Vertically */}
                <div className="flex flex-col gap-6 max-w-4xl">
                    <h1 className="text-5xl md:text-7xl lg:text-[5.5rem] leading-[0.95] font-serif text-white drop-shadow-2xl">
                        NATURE,<br />
                        <span className="text-white/95">CULTURE,</span><br />
                        <span className="text-white/90">DISCOVERY</span>
                    </h1>

                    <p className="text-base md:text-xl text-gray-200 font-light max-w-2xl drop-shadow-md border-l-2 border-[#F4A024] pl-4">
                        Discover plateaus, waterfalls and living tribal traditions across India's green heartland.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 mt-4">
                        <button className="bg-[#F4A024] hover:bg-[#d68515] text-black font-bold text-sm md:text-base px-8 py-4 rounded-sm flex items-center justify-center gap-2 transition-transform hover:-translate-y-1 shadow-lg">
                            Plan your trip <MoveUpRight size={18} />
                        </button>
                        <button className="bg-white hover:bg-gray-100 text-black font-bold text-sm md:text-base px-8 py-4 rounded-sm flex items-center justify-center gap-2 transition-transform hover:-translate-y-1 shadow-lg">
                            Download brochure <Download size={18} />
                        </button>
                    </div>
                </div>
            </main>

            {/* Sidebar Social Links (Left Side) - Hidden on mobile */}
            <div className="hidden lg:flex fixed left-6 top-1/2 -translate-y-1/2 flex-col gap-6 z-20">
                <SocialIcon icon={<Facebook size={20} />} />
                <SocialIcon icon={<Twitter size={20} />} />
                <SocialIcon icon={<Instagram size={20} />} />
                <SocialIcon icon={<Youtube size={20} />} />
            </div>

            {/* Injected Children (Voice Agent Overlay) */}
            {children}

        </div>
    );
};

// --- Sub Components ---

const SocialIcon: React.FC<{ icon: React.ReactNode }> = ({ icon }) => (
    <a href="#" className="text-white/60 hover:text-[#F4A024] transition-colors hover:scale-110 transform">
        {icon}
    </a>
);