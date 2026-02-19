import { useState } from 'react';
import { X, Phone, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import 'react-phone-number-input/style.css';
import PhoneInput, { isValidPhoneNumber } from 'react-phone-number-input';

interface OutboundCallModalProps {
    isOpen: boolean;
    onClose: () => void;
    agentType: string;
}

export function OutboundCallModal({ isOpen, onClose, agentType }: OutboundCallModalProps) {
    const [phoneNumber, setPhoneNumber] = useState<string | undefined>();
    const [provider, setProvider] = useState<'exotel' | 'twilio'>(agentType === 'hirebot' ? 'twilio' : 'exotel');
    const [isLoading, setIsLoading] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    if (!isOpen) return null;

    const handleCall = async () => {
        if (!phoneNumber || !isValidPhoneNumber(phoneNumber)) {
            setErrorMessage('Please enter a valid phone number');
            setStatus('error');
            return;
        }

        setIsLoading(true);
        setStatus('idle');
        setErrorMessage('');

        try {
            const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

            const response = await fetch(`${BACKEND_URL}/api/makeCall`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phone_number: phoneNumber,
                    agent_type: agentType,
                    call_from: provider,
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
                setPhoneNumber(undefined);
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

                                <div className="premium-phone-input">
                                    <PhoneInput
                                        international
                                        defaultCountry="IN"
                                        value={phoneNumber}
                                        onChange={setPhoneNumber}
                                        className="flex items-center gap-3 p-3 bg-gray-50 border border-gray-200 rounded-xl focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all"
                                        numberInputProps={{
                                            className: "w-full bg-transparent border-none outline-none text-gray-900 placeholder-gray-400 font-medium text-base",
                                            placeholder: "Enter phone number"
                                        }}
                                    />
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

                                <p className="text-xs text-gray-500 ml-1">
                                    Enter your number to receive a call from our AI agent.
                                </p>
                            </div>

                            <div className="space-y-4">
                                <label className="block text-sm font-medium text-gray-700 ml-1">
                                    SIP Provider
                                </label>
                                <div className={`grid gap-3 p-1 bg-gray-100 rounded-2xl relative ${agentType === 'hirebot' ? 'grid-cols-1' : 'grid-cols-2'}`}>
                                    {agentType !== 'hirebot' && (
                                        <button
                                            onClick={() => setProvider('exotel')}
                                            className={`relative z-10 py-2.5 text-sm font-bold rounded-xl transition-all duration-300 ${provider === 'exotel' ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'}`}
                                        >
                                            Exotel
                                        </button>
                                    )}
                                    <button
                                        onClick={() => setProvider('twilio')}
                                        className={`relative z-10 py-2.5 text-sm font-bold rounded-xl transition-all duration-300 ${provider === 'twilio' ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'}`}
                                    >
                                        Twilio
                                    </button>
                                    <div
                                        className={`absolute top-1 bottom-1 bg-white shadow-sm rounded-xl transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${agentType === 'hirebot'
                                                ? 'left-1 right-1 w-[calc(100%-8px)]'
                                                : `w-[calc(50%-4px)] ${provider === 'exotel' ? 'left-1' : 'left-[calc(50%+2px)]'}`
                                            }`}
                                    />
                                </div>
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
