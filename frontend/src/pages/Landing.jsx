import React, { useState } from 'react';
import { SignIn } from '@clerk/react';

function Landing() {
    const [showLogin, setShowLogin] = useState(false);

    return (
        <div
            className="min-h-screen bg-gray-950 text-white relative flex flex-col"
            style={{
                backgroundImage: "url('/landing-bg.png')",
                backgroundSize: "cover",
                backgroundPosition: "center",
                backgroundRepeat: "no-repeat"
            }}
        >
            {/* Dark overlay for better text readability */}
            <div className="absolute inset-0 bg-gray-950/70 z-0"></div>

            {/* Navigation */}
            <nav className="relative z-20 flex items-center justify-between px-8 py-6">
                <div className="flex items-center gap-3">
                    <img src="/logo.png" alt="MemBlocks Logo" className="w-10 h-10 object-contain" />
                    <span className="text-xl font-bold tracking-wide">MemBlocks</span>
                </div>
                <button
                    onClick={() => setShowLogin(true)}
                    className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 transition-colors rounded-xl font-medium shadow-lg shadow-indigo-500/20"
                >
                    Login
                </button>
            </nav>

            {/* Hero Content */}
            <main className="relative z-10 flex-1 flex flex-col items-center justify-center text-center px-4 -mt-20">
                <div className="inline-block mb-4 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-indigo-300 text-sm font-medium tracking-wide backdrop-blur-md">
                    Next-Generation LLM Context
                </div>
                <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400 drop-shadow-sm">
                    Modular Memory
                </h1>
                <p className="text-xl md:text-2xl text-gray-300 max-w-3xl mb-10 leading-relaxed font-light">
                    Plug in &amp; Play the Blocks. <br className="hidden md:block" />
                    Give your AI agents persistent, composable, and self-organizing memory architecture that spans across sessions.
                </p>
                <button
                    onClick={() => setShowLogin(true)}
                    className="px-8 py-4 bg-white text-gray-950 hover:bg-gray-100 transition-colors rounded-2xl font-bold text-lg shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)]"
                >
                    Start Building Memories
                </button>
            </main>

            {/* Login Modal Overlay */}
            {showLogin && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                    <div className="relative">
                        {/* Close button for the modal */}
                        <button
                            onClick={() => setShowLogin(false)}
                            className="absolute -top-12 right-0 text-gray-400 hover:text-white transition-colors flex items-center gap-2"
                        >
                            <span className="text-sm font-medium">Close</span>
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>

                        <div className="bg-gray-900 p-1 rounded-2xl shadow-2xl border border-gray-800">
                            <SignIn
                                routing="hash"
                                afterSignInUrl="/"
                                afterSignUpUrl="/"
                                appearance={{
                                    variables: {
                                        colorBackground: '#111827', // Tailwind gray-900
                                        colorText: '#f3f4f6',       // Tailwind gray-100
                                        colorPrimary: '#4f46e5',    // Tailwind indigo-600
                                        colorInputBackground: '#1f2937',// Tailwind gray-800
                                        colorInputText: '#f3f4f6',  // Tailwind gray-100
                                        colorTextSecondary: '#9ca3af', // Tailwind gray-400
                                    },
                                    elements: {
                                        card: "bg-transparent shadow-none border-0",
                                        headerTitle: "text-white",
                                        headerSubtitle: "text-gray-400",
                                        socialButtonsBlockButton: "border-gray-700 bg-gray-800 text-white hover:bg-gray-700",
                                        socialButtonsBlockButtonText: "text-gray-200",
                                        dividerLine: "bg-gray-700",
                                        dividerText: "text-gray-400",
                                        formFieldLabel: "text-gray-300",
                                        formFieldInput: "bg-gray-800 border-gray-700 text-white focus:border-indigo-500",
                                        footerActionText: "text-gray-400",
                                        footerActionLink: "text-indigo-400 hover:text-indigo-300"
                                    }
                                }}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Landing;
