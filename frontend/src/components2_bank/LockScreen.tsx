import React, { useState } from 'react';
import { Lock, Eye, EyeOff, Loader2 } from 'lucide-react';
import { Header } from './Header';

interface LockScreenProps {
    onUnlock: () => void;
}

// Safely access environment variables with fallback
const BACKEND_URL = import.meta.env?.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

export const LockScreen: React.FC<LockScreenProps> = ({ onUnlock }) => {
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            // Trim URL and password to avoid issues
            const url = `${BACKEND_URL}/api/checkPassword?password=${encodeURIComponent(password)}`;
            const response = await fetch(url);
            const result = await response.text();

            if (result === 'ok') {
                // Success! Store authentication status
                sessionStorage.setItem('authenticated', 'true');
                onUnlock();
            } else {
                setError('Invalid password. Please try again.');
                setPassword('');
            }
        } catch (err) {
            console.error('Authentication error:', err);
            setError('Failed to connect to server. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col min-h-screen bg-background text-text-main font-sans selection:bg-primary/20 relative overflow-hidden">
            <Header status="disconnected" />

            {/* Background Blob Effect */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />

            <div className="flex-1 flex flex-col items-center justify-center p-5 relative z-10 animate-fade-in-up">

                {/* Logo/Icon Section */}
                <div className="text-center space-y-6 mb-10">
                    <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center mx-auto text-primary shadow-[0_8px_30px_rgba(0,0,0,0.06)] border border-border">
                        <Lock size={40} strokeWidth={1.5} />
                    </div>
                    <div className="space-y-2">
                        <h1 className="text-4xl md:text-5xl font-bold text-primary tracking-tight">
                            Secure Access
                        </h1>
                        <p className="text-text-muted text-lg max-w-md mx-auto leading-relaxed">
                            Enter your password to unlock the application
                        </p>
                    </div>
                </div>

                {/* Password Form */}
                <form onSubmit={handleSubmit} className="w-full max-w-md space-y-6">
                    <div className="space-y-2">
                        <div className="relative group">
                            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-primary transition-colors">
                                <Lock size={20} />
                            </div>

                            <input
                                id="password"
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter password"
                                autoFocus
                                disabled={isLoading}
                                className="w-full bg-white border border-border rounded-xl pl-12 pr-12 py-4 text-text-main placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all shadow-sm hover:border-primary/50 disabled:opacity-70 disabled:cursor-not-allowed disabled:bg-gray-50"
                            />

                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                disabled={isLoading}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-text-muted hover:text-primary transition-colors disabled:opacity-50 cursor-pointer"
                            >
                                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                            </button>
                        </div>

                        {/* Error Message */}
                        {error && (
                            <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 animate-fade-in flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                                {error}
                            </div>
                        )}
                    </div>

                    {/* Unlock Button */}
                    <button
                        type="submit"
                        disabled={!password || isLoading}
                        className="group relative w-full py-4 px-8 bg-primary hover:bg-primary-hover text-white text-lg rounded-full font-semibold transition-all shadow-lg hover:shadow-primary/30 hover:-translate-y-1 flex items-center justify-center gap-3 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
                    >
                        {isLoading ? (
                            <>
                                <Loader2 size={24} className="animate-spin" />
                                Authenticating...
                            </>
                        ) : (
                            <>
                                Unlock Application
                            </>
                        )}
                    </button>
                </form>

                <div className="mt-12 flex justify-center gap-6 text-sm text-text-muted opacity-70">
                    <span className="flex items-center gap-1">Secure Connection</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">End-to-End Encryption</span>
                </div>
            </div>
        </div>
    );
};
