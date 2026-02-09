import { useState, useEffect } from 'react';
import { X, Save, Loader2, CheckCircle2, AlertCircle, Settings } from 'lucide-react';
import 'react-phone-number-input/style.css';
import PhoneInput, { isValidPhoneNumber } from 'react-phone-number-input';

interface InboundSettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const AGENT_OPTIONS = [
    { value: 'invoice', label: 'Invoice Agent' },
    { value: 'restaurant', label: 'Restaurant Agent' },
    { value: 'bank', label: 'Banking Agent' },
    { value: 'tour', label: 'Tour Agent' },
    { value: 'realestate', label: 'Real Estate Agent' },
    { value: 'bandhan_banking', label: 'Bandhan Banking Agent' },
    { value: 'hirebot', label: 'Hirebot Agent' }, 

];

export function InboundSettingsModal({ isOpen, onClose }: InboundSettingsModalProps) {
    const [phoneNumber, setPhoneNumber] = useState<string | undefined>();
    const [selectedAgent, setSelectedAgent] = useState('invoice');
    const [isLoading, setIsLoading] = useState(false);
    const [fetching, setFetching] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    // Load from local storage on mount
    useEffect(() => {
        const saved = localStorage.getItem('inbound_phone_number');
        if (saved) {
            setPhoneNumber(saved);
        }
    }, []);

    // Fetch mapping when modal opens or phone number is restored
    useEffect(() => {
        if (isOpen && phoneNumber && isValidPhoneNumber(phoneNumber)) {
            fetchMapping(phoneNumber);
        }
    }, [isOpen]);

    const fetchMapping = async (phone: string) => {
        setFetching(true);
        try {
            const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
            const res = await fetch(`${BACKEND_URL}/api/getInboundAgent?phone_number=${encodeURIComponent(phone)}`);
            if (res.ok) {
                const data = await res.json();
                if (data.agent_type) {
                    setSelectedAgent(data.agent_type);
                }
            }
        } catch (e) {
            console.error("Failed to fetch mapping", e);
        } finally {
            setFetching(false);
        }
    };

    if (!isOpen) return null;

    const handleSave = async () => {
        if (!phoneNumber || !isValidPhoneNumber(phoneNumber)) {
            setErrorMessage('Please enter a valid phone number');
            setStatus('error');
            return;
        }

        setIsLoading(true);
        setStatus('idle');
        setErrorMessage('');

        // Save to local storage
        localStorage.setItem('inbound_phone_number', phoneNumber);

        try {
            const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

            const response = await fetch(`${BACKEND_URL}/api/setInboundAgent`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phone_number: phoneNumber,
                    agent_type: selectedAgent,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || 'Failed to save settings');
            }

            setStatus('success');
            setTimeout(() => {
                onClose();
                setStatus('idle');
            }, 2000);

        } catch (err: any) {
            console.error("Save failed:", err);
            setErrorMessage(err.message || "Failed to save settings");
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
                            <Settings size={20} />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900 leading-none">Inbound Call Settings</h3>
                            <p className="text-sm text-gray-500 mt-1">Link your number to an agent</p>
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
                            <h4 className="text-xl font-semibold text-gray-900">Settings Saved!</h4>
                            <p className="text-gray-500 mt-2">Your inbound call preference has been updated.</p>
                        </div>
                    ) : (
                        <>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 ml-1 mb-1">
                                        Your Phone Number
                                    </label>
                                    <div className="premium-phone-input relative">
                                        <PhoneInput
                                            international
                                            defaultCountry="IN"
                                            value={phoneNumber}
                                            onChange={setPhoneNumber}
                                            onBlur={() => {
                                                if (phoneNumber && isValidPhoneNumber(phoneNumber)) {
                                                    fetchMapping(phoneNumber);
                                                }
                                            }}
                                            className="flex items-center gap-3 p-3 bg-gray-50 border border-gray-200 rounded-xl focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all"
                                            numberInputProps={{
                                                className: "w-full bg-transparent border-none outline-none text-gray-900 placeholder-gray-400 font-medium text-base",
                                                placeholder: "Enter phone number"
                                            }}
                                        />
                                        {fetching && (
                                            <div className="absolute right-3 top-1/2 -translate-y-1/2">
                                                <Loader2 size={16} className="animate-spin text-gray-400" />
                                            </div>
                                        )}
                                    </div>
                                    <style>{`
                                        .premium-phone-input .PhoneInputCountry {
                                            margin-right: 8px;
                                        }
                                        .premium-phone-input .PhoneInputCountrySelect {
                                            background: transparent;
                                        }
                                        .premium-phone-input .PhoneInputCountryIcon {
                                            width: 24px;
                                            height: 18px;
                                            border-radius: 2px;
                                            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                                        }
                                        .premium-phone-input .PhoneInputCountryIcon--border {
                                            background-color: transparent;
                                            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                                            border: none;
                                        }
                                    `}</style>
                                    <p className="text-xs text-gray-500 ml-1 mt-1">
                                        Calls from this number will be routed to the selected agent.
                                    </p>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 ml-1 mb-1">
                                        Preferred Agent
                                    </label>
                                    <div className="relative">
                                        <select
                                            value={selectedAgent}
                                            onChange={(e) => setSelectedAgent(e.target.value)}
                                            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl appearance-none outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-medium text-gray-900"
                                        >
                                            {AGENT_OPTIONS.map((opt) => (
                                                <option key={opt.value} value={opt.value}>
                                                    {opt.label}
                                                </option>
                                            ))}
                                        </select>
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
                                            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M2.5 4.5L6 8L9.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {status === 'error' && (
                                <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm flex items-start gap-2 animate-in fade-in">
                                    <AlertCircle size={16} className="mt-0.5" />
                                    <span>{errorMessage}</span>
                                </div>
                            )}

                            <button
                                onClick={handleSave}
                                disabled={isLoading}
                                className="w-full py-4 bg-primary hover:bg-primary-hover text-white rounded-xl font-semibold shadow-lg hover:shadow-primary/30 transition-all active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 size={20} className="animate-spin" />
                                        <span>Saving Settings...</span>
                                    </>
                                ) : (
                                    <>
                                        <Save size={20} />
                                        <span>Save Preferences</span>
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
