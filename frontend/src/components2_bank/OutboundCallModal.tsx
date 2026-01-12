import { useState } from 'react';
import { X, Phone, Globe, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface OutboundCallModalProps {
    isOpen: boolean;
    onClose: () => void;
    agentType: string;
}

const COUNTRY_CODES = [
    { code: '+1', country: 'US/CA', flag: '🇺🇸' },
    { code: '+44', country: 'UK', flag: '🇬🇧' },
    { code: '+91', country: 'IN', flag: '🇮🇳' },
    { code: '+61', country: 'AU', flag: '🇦🇺' },
    { code: '+81', country: 'JP', flag: '🇯🇵' },
    { code: '+49', country: 'DE', flag: '🇩🇪' },
];

export function OutboundCallModal({ isOpen, onClose, agentType }: OutboundCallModalProps) {
    const [phoneNumber, setPhoneNumber] = useState('');
    const [countryCode, setCountryCode] = useState('+91');
    const [isLoading, setIsLoading] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    if (!isOpen) return null;

    const handleCall = async () => {
        if (!phoneNumber || phoneNumber.length < 5) {
            setErrorMessage('Please enter a valid phone number');
            setStatus('error');
            return;
        }

        setIsLoading(true);
        setStatus('idle');
        setErrorMessage('');

        try {
            const fullPhoneNumber = `${countryCode}${phoneNumber}`;
            const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

            const response = await fetch(`${BACKEND_URL}/api/makeCall`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phone_number: fullPhoneNumber,
                    agent_type: agentType,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || 'Failed to initiate call');
            }

            setStatus('success');
            setTimeout(() => {
                onClose();
                setStatus('idle');
                setPhoneNumber('');
            }, 2000);

        } catch (err: any) {
            console.error("Outbound call failed:", err);
            setErrorMessage(err.message || "Failed to connect to server");
            setStatus('error');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop with blur */}
            <div
                className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative w-full max-w-md bg-white/90 backdrop-blur-xl border border-white/20 shadow-2xl rounded-3xl overflow-hidden animate-in zoom-in-95 duration-300 transform transition-all">

                {/* Header */}
                <div className="px-6 py-5 border-b border-gray-100 flex items-center justify-between bg-white/50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                            <Phone size={20} />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900 leading-none">Outbound Call</h3>
                            <p className="text-sm text-gray-500 mt-1 capitalize">{agentType} Agent</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6">
                    {status === 'success' ? (
                        <div className="flex flex-col items-center justify-center py-8 text-center animate-in fade-in slide-in-from-bottom-4">
                            <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-4">
                                <CheckCircle2 size={32} />
                            </div>
                            <h4 className="text-xl font-semibold text-gray-900">Call Initiated!</h4>
                            <p className="text-gray-500 mt-2">Your agent is calling you now.</p>
                        </div>
                    ) : (
                        <>
                            <div className="space-y-4">
                                <label className="block text-sm font-medium text-gray-700 ml-1">
                                    Phone Number
                                </label>
                                <div className="flex gap-3">
                                    <div className="relative w-1/3">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                                            <Globe size={16} />
                                        </div>
                                        <select
                                            value={countryCode}
                                            onChange={(e) => setCountryCode(e.target.value)}
                                            className="block w-full pl-9 pr-8 py-3 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all appearance-none outline-none cursor-pointer hover:bg-gray-100"
                                        >
                                            {COUNTRY_CODES.map((country) => (
                                                <option key={country.code} value={country.code}>
                                                    {country.flag} {country.code}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <input
                                        type="tel"
                                        value={phoneNumber}
                                        onChange={(e) => setPhoneNumber(e.target.value.replace(/\D/g, ''))}
                                        placeholder="98765 43210"
                                        className="block w-2/3 px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none"
                                        autoFocus
                                    />
                                </div>
                                <p className="text-xs text-gray-500 ml-1">
                                    Enter your number to receive a call from our AI agent.
                                </p>
                            </div>

                            {status === 'error' && (
                                <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm flex items-start gap-2 animate-in fade-in">
                                    <AlertCircle size={16} className="mt-0.5" />
                                    <span>{errorMessage}</span>
                                </div>
                            )}

                            <button
                                onClick={handleCall}
                                disabled={isLoading}
                                className="w-full py-4 bg-primary hover:bg-primary-hover text-white rounded-xl font-semibold shadow-lg hover:shadow-primary/30 transition-all active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 size={20} className="animate-spin" />
                                        <span>Initiating Call...</span>
                                    </>
                                ) : (
                                    <>
                                        <Phone size={20} />
                                        <span>Call Now</span>
                                    </>
                                )}
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
