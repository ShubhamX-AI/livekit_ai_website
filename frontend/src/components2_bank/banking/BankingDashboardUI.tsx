import React from 'react';
import {
    ArrowLeft,
    Bell,
    User,
    Eye,
    IndianRupee,
    Smartphone,
    Receipt,
    Home,
    Wallet,
    Headphones,
    LayoutDashboard,
    PieChart,
    Utensils,
    ShoppingBag,
    Zap,
    CreditCard,
} from 'lucide-react';

export const BankingDashboardUI: React.FC<{ children?: React.ReactNode; onBack?: () => void }> = ({ children, onBack }) => {
    return (
        <div className="h-screen w-full bg-[#0B1426] text-white font-sans flex flex-col md:flex-row relative overflow-hidden">

            {/* SIDEBAR NAVIGATION (Desktop Only) */}
            <aside className="hidden md:flex flex-col w-64 bg-[#080f1e] border-r border-white/5 h-screen sticky top-0 z-20 shrink-0">
                <div className="p-6 flex items-center gap-3">
                    <button
                        onClick={onBack}
                        className="p-2 -ml-2 hover:bg-white/10 rounded-full transition-colors text-slate-400 hover:text-white"
                        title="Back to Home"
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div className="w-10 h-10 rounded-full border border-[#D4AF37] flex items-center justify-center text-[#D4AF37] bg-[#D4AF37]/10 shrink-0">
                        <span className="text-2xl font-serif font-bold pt-1">L</span>
                    </div>
                    <div className="flex flex-col">
                        <span className="text-lg font-bold text-[#D4AF37] leading-none">लक्ष्मी बैंक</span>
                        <span className="text-[10px] text-slate-400 tracking-wider">VYOM ASSISTANT</span>
                    </div>
                </div>

                <nav className="flex-1 px-4 py-6 flex flex-col gap-2 overflow-y-auto custom-scrollbar">
                    <DesktopNavItem icon={<LayoutDashboard size={20} />} label="Dashboard" active />
                    <DesktopNavItem icon={<Wallet size={20} />} label="Accounts" />
                    <DesktopNavItem icon={<CreditCard size={20} />} label="Cards" />
                    <DesktopNavItem icon={<IndianRupee size={20} />} label="Transfers" />
                    <DesktopNavItem icon={<PieChart size={20} />} label="Investments" />
                </nav>

                <div className="p-4 border-t border-white/5">
                    <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 cursor-pointer">
                        <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center">
                            <User size={20} className="text-slate-300" />
                        </div>
                        <div className="flex flex-col overflow-hidden">
                            <span className="text-sm font-medium truncate">Priya Sharma</span>
                            <span className="text-xs text-slate-400 truncate">Savings ...3812</span>
                        </div>
                    </div>
                </div>
            </aside>

            {/* MAIN CONTENT AREA */}
            <main className="flex-1 flex flex-col h-full relative">

                {/* TOP HEADER */}
                <header className="sticky top-0 z-10 bg-[#0B1426]/95 backdrop-blur-md border-b border-white/5 px-6 py-4 flex items-center justify-between">
                    <div className="md:hidden flex items-center gap-2">
                        <button
                            onClick={onBack}
                            className="p-2 -ml-2 mr-1 hover:bg-white/10 rounded-full transition-colors text-slate-400 hover:text-white"
                        >
                            <ArrowLeft size={20} />
                        </button>
                        <div className="w-8 h-8 rounded-full border border-[#D4AF37] flex items-center justify-center text-[#D4AF37]">
                            <span className="text-xl font-serif font-bold">L</span>
                        </div>
                        <span className="font-bold text-[#D4AF37]">Laxmi Bank</span>
                    </div>

                    <div className="hidden md:block">
                        <h1 className="text-xl font-semibold text-white">Hello, Priya! 👋</h1>
                        <p className="text-xs text-slate-400">Jan 2, 2026 • Overview</p>
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

                {/* COMPACT DASHBOARD CONTENT */}
                <div className="flex-1 p-4 md:p-6 w-full max-w-7xl mx-auto overflow-y-auto md:overflow-hidden flex flex-col gap-4 pb-24 md:pb-6 custom-scrollbar">

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-auto md:h-full">

                        {/* LEFT COLUMN (Balance + Activity) */}
                        <div className="lg:col-span-8 flex flex-col gap-4 h-auto md:h-full">

                            {/* 1. BALANCE CARD - Compact */}
                            <div className="flex-none bg-gradient-to-br from-[#1A263E] to-[#0f1729] rounded-[24px] p-5 md:p-6 border border-white/5 shadow-2xl relative overflow-hidden group">
                                <div className="absolute top-0 right-0 w-64 h-64 bg-[#D4AF37]/5 rounded-full blur-[80px] -mr-20 -mt-20 pointer-events-none group-hover:bg-[#D4AF37]/10 transition-colors duration-700"></div>
                                <div className="relative z-10 flex flex-col h-full justify-between">
                                    <div className="flex justify-between items-start mb-2">
                                        <div>
                                            <h2 className="text-sm text-slate-400 mb-0.5 whitespace-nowrap">Savings Account <span className="text-slate-500 text-xs tracking-wider ml-1">XX3812</span></h2>
                                            <div className="flex items-center gap-2">
                                                <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white tracking-tight">₹ 42,650.75</h1>
                                                <button className="text-slate-500 hover:text-white transition-colors"><Eye size={16} /></button>
                                            </div>
                                            <p className="text-[10px] text-slate-500 mt-1">Ledger Balance: ₹ 43,210.75</p>
                                        </div>
                                        <div className="w-10 h-10 rounded-xl bg-[#D4AF37]/20 flex items-center justify-center text-[#D4AF37]">
                                            <Wallet size={20} />
                                        </div>
                                    </div>
                                    <div className="flex gap-3 mt-3">
                                        <button className="flex-1 flex items-center justify-center gap-2 bg-[#D4AF37] hover:bg-[#bfa03a] text-[#0B1426] px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-[0_0_20px_rgba(212,175,55,0.2)]">
                                            Send Money
                                        </button>
                                        <button className="flex-1 flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 px-4 py-2.5 rounded-xl text-xs text-slate-300 border border-white/10 transition-colors">
                                            View History
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* 3. RECENT ACTIVITY - Fill Remaining Height */}
                            <div className="flex-1 bg-[#111e33] rounded-[24px] p-5 md:p-6 border border-white/5 flex flex-col min-h-[400px] md:min-h-0">
                                <div className="flex justify-between items-center mb-4 flex-none">
                                    <h3 className="text-base font-semibold text-white">Recent Activity</h3>
                                    <button className="text-[10px] text-[#D4AF37] font-medium hover:underline">View All</button>
                                </div>

                                <div className="flex flex-col gap-2 overflow-y-auto pr-2 custom-scrollbar">
                                    <TransactionItem
                                        icon={<Zap size={18} />}
                                        bg="bg-amber-500/10"
                                        color="text-amber-500"
                                        title="Electricity Bill (CESC)"
                                        amount="₹ 1,840"
                                        sub="Consumer: XX7712"
                                        date="Due Jan 10"
                                        isDebit={false}
                                        isBill={true}
                                    />
                                    <TransactionItem
                                        icon={<Utensils size={18} />}
                                        bg="bg-rose-500/10"
                                        color="text-rose-500"
                                        title="Swiggy"
                                        amount="- ₹ 487"
                                        sub="Food & Dining"
                                        date="Jan 1"
                                        isDebit
                                    />
                                    <TransactionItem
                                        icon={<ShoppingBag size={18} />}
                                        bg="bg-indigo-500/10"
                                        color="text-indigo-400"
                                        title="Amazon India"
                                        amount="- ₹ 2,349"
                                        sub="Shopping"
                                        date="Dec 29"
                                        isDebit
                                    />
                                    <TransactionItem
                                        icon={<Smartphone size={18} />}
                                        bg="bg-blue-500/10"
                                        color="text-blue-400"
                                        title="Jio Fiber"
                                        amount="- ₹ 1,179"
                                        sub="Bill Payment"
                                        date="Dec 28"
                                        isDebit
                                    />
                                </div>
                            </div>

                        </div>

                        {/* RIGHT COLUMN (Quick Actions) */}
                        <div className="lg:col-span-4 bg-[#16293F]/50 md:bg-[#16293F] rounded-[24px] p-5 md:p-6 border border-white/5 h-auto md:h-full flex flex-col min-h-[300px] md:min-h-0">
                            <h3 className="text-sm font-semibold text-slate-400 mb-4 flex-none">Quick Actions</h3>
                            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 gap-3 overflow-y-auto pr-1">
                                <ActionButton icon={<IndianRupee size={20} />} label="Transfer" />
                                <ActionButton icon={<Receipt size={20} />} label="Pay Bills" />
                                <ActionButton icon={<Smartphone size={20} />} label="Recharge" />
                                <ActionButton icon={<CreditCard size={20} />} label="DCB Card" />
                                <div className="flex flex-col items-center gap-2 group cursor-pointer p-2 rounded-xl hover:bg-white/5 transition-colors">
                                    <div className="w-12 h-12 rounded-[18px] bg-[#1A263E] border border-white/5 text-slate-400 flex items-center justify-center shadow-lg group-hover:bg-[#D4AF37] group-hover:text-[#0B1426] transition-all">
                                        <PieChart size={20} />
                                    </div>
                                    <span className="text-[10px] text-slate-400 font-medium group-hover:text-white">FDs</span>
                                </div>
                                <div className="flex flex-col items-center gap-2 group cursor-pointer p-2 rounded-xl hover:bg-white/5 transition-colors">
                                    <div className="w-12 h-12 rounded-[18px] bg-[#1A263E] border border-white/5 text-slate-400 flex items-center justify-center shadow-lg group-hover:bg-[#D4AF37] group-hover:text-[#0B1426] transition-all">
                                        <Home size={20} />
                                    </div>
                                    <span className="text-[10px] text-slate-400 font-medium group-hover:text-white">Loans</span>
                                </div>
                            </div>

                            {/* Promo / Banner Area (Optional filler) */}
                            <div className="mt-auto pt-4 hidden lg:block">
                                <div className="bg-gradient-to-r from-[#D4AF37]/10 to-[#D4AF37]/5 rounded-xl p-4 border border-[#D4AF37]/20">
                                    <p className="text-xs text-[#D4AF37] font-bold mb-1">Gold Loan @ 8.5%</p>
                                    <p className="text-[10px] text-slate-400">Instant approval in seconds.</p>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </main>

            {/* INJECTED CHILDREN (Agent Overlay) */}
            {children}

            {/* BOTTOM NAV (Mobile) */}
            <div className="md:hidden fixed bottom-0 w-full bg-[#0B1426]/95 backdrop-blur-xl border-t border-white/5 pb-6 pt-3 px-8 flex justify-between items-center z-40">
                <NavIcon icon={<Home size={24} />} label="Home" active />
                <NavIcon icon={<Wallet size={24} />} label="Accounts" />
                <NavIcon icon={<Headphones size={24} />} label="Support" />
            </div>

        </div>
    );
};

// --- Sub Components ---

const DesktopNavItem: React.FC<{ icon: React.ReactNode, label: string, active?: boolean }> = ({ icon, label, active }) => (
    <a href="#" className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${active ? 'bg-[#D4AF37]/10 text-[#D4AF37]' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
        {icon}
        <span className="font-medium text-sm">{label}</span>
    </a>
);

const ActionButton: React.FC<{ icon: React.ReactNode, label: string }> = ({ icon, label }) => (
    <div className="flex flex-col items-center gap-2 cursor-pointer group p-2 rounded-xl hover:bg-white/5 transition-colors">
        <div className="w-12 h-12 rounded-[18px] bg-[#1A263E] border border-white/5 text-[#D4AF37] flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform duration-200 group-hover:bg-[#D4AF37] group-hover:text-[#0B1426]">
            {icon}
        </div>
        <span className="text-[10px] md:text-xs text-center text-slate-400 font-medium leading-tight group-hover:text-white transition-colors">{label}</span>
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
    isDebit?: boolean,
    isBill?: boolean
}> = ({ title, amount, sub, date, icon, bg, color, isDebit, isBill }) => (
    <div className={`flex justify-between items-center group cursor-pointer hover:bg-white/5 p-2 rounded-xl transition-colors border border-transparent hover:border-white/5 ${isBill ? 'bg-amber-500/5 border-amber-500/20' : ''}`}>
        <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full ${bg} ${color} flex items-center justify-center flex-shrink-0`}>
                {icon}
            </div>
            <div className="flex flex-col min-w-0">
                <span className={`text-sm font-medium truncate ${isBill ? 'text-amber-400' : 'text-slate-200'}`}>{title}</span>
                <span className="text-[10px] text-slate-500">{sub}</span>
            </div>
        </div>
        <div className="flex flex-col items-end flex-shrink-0 ml-2">
            <span className={`text-sm font-bold ${isBill ? 'text-amber-400' : (isDebit ? 'text-white' : 'text-emerald-400')}`}>
                {amount}
            </span>
            <span className={`text-[9px] mt-0.5 ${isBill ? 'text-amber-500/80 font-medium' : 'text-slate-500'}`}>{date}</span>
        </div>
    </div>
);

const NavIcon: React.FC<{ icon: React.ReactNode, label: string, active?: boolean }> = ({ icon, label, active }) => (
    <div className={`flex flex-col items-center gap-1 cursor-pointer hover:text-[#D4AF37] transition-colors ${active ? 'text-[#D4AF37]' : 'text-slate-500'}`}>
        {icon}
        <span className="text-[10px] font-medium tracking-wide">{label}</span>
        {active && <div className="w-1 h-1 rounded-full bg-[#D4AF37] mt-1" />}
    </div>
);
