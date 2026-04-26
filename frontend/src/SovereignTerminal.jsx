import React, { useState, useEffect } from 'react';
import CommandCenter from './components/CommandCenter';
import MatrixConvert from './components/MatrixConvert';
import GovernanceHUD from './components/GovernanceHUD';
import { Globe, Cpu, Zap, Share2, Terminal, Shield, Ghost, Activity, Gavel, Mic, CircleDot, Clock } from 'lucide-react';
import { useSovereignState } from './hooks/useSovereignState';
import { useApiKey } from './hooks/useApiKey';
import { getMarketSignals } from './api/pbgClient';

const MarketScanner = () => <div className="p-6 text-[#738091] uppercase tracking-widest font-bold">Market Scanner Active</div>;
const RiskOracle = () => <div className="p-6 text-[#738091] uppercase tracking-widest font-bold">Risk Oracle Active</div>;
const ExecutionHUD = () => <div className="p-6 text-[#738091] uppercase tracking-widest font-bold">Execution SEA Active</div>;
const GhostProtocolHUD = () => <div className="p-6 text-[#738091] uppercase tracking-widest font-bold">Ghost Protocol Active</div>;
const InstitutionalHUD = () => <div className="p-6 text-[#738091] uppercase tracking-widest font-bold">Institutional Oracle Active</div>;
const TreasuryHUD = () => <div className="p-6 text-[#738091] uppercase tracking-widest font-bold">Sovereign Wealth Treasury Active</div>;
const MeshHUD = () => <div className="p-6 text-[#738091] uppercase tracking-widest font-bold">Neural Mesh Active</div>;
const SingularityHUD = () => <div className="p-6 text-[#738091] uppercase tracking-widest font-bold">Singularity Core Active</div>;

function LivePulseFooter() {
    const { apiKey } = useApiKey();
    const { recentEvents } = useSovereignState();
    const [signals, setSignals] = useState([]);

    useEffect(() => {
        if (!apiKey) return;
        getMarketSignals(apiKey)
            .then(d => setSignals(d.signals || []))
            .catch(() => {});
    }, [apiKey]);

    // Build ticker: live WS events first, then market signals from REST
    const eventItems = recentEvents.map(e => e.label);
    const signalItems = signals.map(s =>
        `${s.signal_type} · ${s.market} · ${s.teams} · +${(s.value_score * 100).toFixed(1)}%`
    );
    const items = [...eventItems, ...signalItems];

    return (
        <div className="bg-[#151A22] border-t border-white/10 p-1.5 flex items-center justify-between z-10 sticky bottom-0 overflow-hidden font-sans">
            <div className="flex items-center gap-3 px-3 border-r border-white/10 pr-6 shrink-0">
                <CircleDot className={`w-3 h-3 ${items.length > 0 ? 'text-emerald-500' : 'text-[#738091]'}`} />
                <span className="text-[9px] font-bold text-white uppercase tracking-widest">Live Pulse</span>
            </div>
            <div className="flex-1 flex overflow-hidden whitespace-nowrap px-4">
                {items.length > 0 ? (
                    <div className="animate-[marquee_30s_linear_infinite] inline-block text-[11px] font-mono font-bold text-[#738091] tracking-tighter uppercase">
                        {items.map((item, i) => (
                            <span key={i} className="mx-8">
                                <span className="text-sky-400">●</span> {item}
                            </span>
                        ))}
                    </div>
                ) : (
                    <span className="text-[11px] font-mono text-[#738091] uppercase tracking-widest">AWAITING SIGNAL FEED...</span>
                )}
            </div>
        </div>
    );
}

export default function SovereignTerminal() {
    const [activeTab, setActiveTab] = useState('command');
    const [currentTime, setCurrentTime] = useState('');
    const state = useSovereignState();

    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    const renderModule = () => {
        switch (activeTab) {
            case 'command': return <CommandCenter />;
            case 'scanner': return <MarketScanner />;
            case 'convert': return <MatrixConvert />;
            case 'execution': return <ExecutionHUD />;
            case 'ghost': return <GhostProtocolHUD />;
            case 'ORACLE': return <InstitutionalHUD />;
            case 'TREASURY': return <TreasuryHUD />;
            case 'mesh': return <MeshHUD />;
            case 'singularity': return <SingularityHUD />;
            case 'governance': return <GovernanceHUD />;
            default: return <CommandCenter />;
        }
    };

    const nav = [
        { id: 'command', label: 'COMMAND_CENTER', icon: Activity },
        { id: 'mesh', label: 'NEURAL_MESH', icon: Globe },
        { id: 'scanner', label: 'MARKET_SCANNER', icon: Cpu },
        { id: 'convert', label: 'MATRIX_CONVERT', icon: Terminal },
        { id: 'singularity', label: 'SINGULARITY_CORE', icon: Zap },
        { id: 'governance', label: 'SHARD_GOVERNANCE', icon: Gavel },
        { id: 'ORACLE', label: 'INSTITUTIONAL_ORACLE', icon: Share2 },
        { id: 'execution', label: 'EXECUTION_SEA', icon: Activity },
        { id: 'TREASURY', label: 'SOVEREIGN_WEALTH', icon: Shield },
        { id: 'ghost', label: 'GHOST_PROTOCOL', icon: Ghost }
    ];

    return (
        <div className="h-screen flex text-[13px] font-sans bg-[#0B0E14] text-white dark">

            {/* Sidebar (Flat, Brutal, Unified) */}
            <aside className="w-64 bg-[#151A22] border-r border-white/10 flex flex-col z-20">
                <div className="p-6 border-b border-white/10 bg-[#0B0E14]">
                    <h1 className="text-sm font-bold tracking-widest uppercase text-white flex items-center gap-3">
                        <div className="w-3 h-3 bg-sky-500"></div>
                        PBG.CORE
                    </h1>
                    <p className="text-[10px] text-[#738091] font-bold tracking-widest mt-3 uppercase">Command Terminal</p>
                </div>

                <nav className="flex-1 flex flex-col py-4 overflow-y-auto">
                    {nav.map(item => {
                        const Icon = item.icon;
                        const isActive = activeTab === item.id;
                        return (
                            <button
                                key={item.id}
                                onClick={() => setActiveTab(item.id)}
                                className={`px-6 py-3 flex items-center gap-4 text-[10px] uppercase tracking-widest font-bold ${isActive
                                    ? 'bg-[#0B0E14] text-white border-l-4 border-sky-500'
                                    : 'text-[#738091] border-l-4 border-transparent hover:text-white hover:text-white hover:bg-white/5'
                                    }`}
                            >
                                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-sky-500' : ''}`} />
                                {item.label}
                            </button>
                        );
                    })}
                </nav>

                <div className="p-6 border-t border-white/10 bg-[#0B0E14]">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-[9px] text-[#738091] font-bold uppercase tracking-widest">Connection</span>
                        <span className="text-[10px] font-mono font-bold text-emerald-500 tracking-tighter">SECURE L2</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-[9px] text-[#738091] font-bold uppercase tracking-widest">Uptime</span>
                        <span className="text-[10px] font-mono font-bold text-white tracking-tighter">99.99%</span>
                    </div>
                </div>
            </aside>

            {/* Main Area */}
            <main className="flex-1 flex flex-col relative z-0 bg-[#0B0E14]">

                {/* Header (Brutal & Flat) */}
                <header className="border-b border-white/10 px-8 py-4 flex justify-between items-center bg-[#151A22] z-10">
                    <div className="flex items-center gap-8">
                        <div className="flex items-center gap-4">
                            <span className="text-[10px] text-[#738091] uppercase tracking-widest font-bold">Active Module</span>
                            <h2 className="text-[12px] font-bold text-white tracking-widest uppercase">{activeTab.replace('_', ' ')}</h2>
                        </div>

                        <div className="h-5 w-px bg-white/10"></div>

                        <div className="flex gap-8">
                            <div className="flex items-center gap-3">
                                <div className={`w-2 h-2 ${state.status === 'STABLE' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                <span className="text-[10px] font-bold font-mono tracking-tighter text-[#738091]">{state.status || 'STABLE'}</span>
                            </div>
                            <div className="flex items-center gap-3 text-[#738091]">
                                <Globe className="w-3.5 h-3.5" />
                                <span className="text-[10px] font-bold font-mono tracking-tighter">{state.mesh?.active_nodes || 3} NODES</span>
                            </div>
                            <div className="flex items-center gap-3 text-[#738091]">
                                <Shield className="w-3.5 h-3.5" />
                                <span className="text-[10px] font-bold font-mono tracking-tighter">{state.solana?.USDC || '0.00'} USDC</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="text-[11px] font-bold font-mono tracking-tighter text-white flex items-center gap-3 uppercase">
                            <Clock className="w-3.5 h-3.5 text-[#738091]" />
                            {currentTime} UTC
                        </div>
                        <button className="flex items-center gap-2 px-4 py-2 bg-[#0B0E14] border border-white/10 rounded-none text-[10px] font-bold tracking-widest text-white uppercase hover:bg-white/5 transition-none">
                            <Mic className="w-3 h-3 text-[#738091]" /> Voice OS
                        </button>
                    </div>
                </header>

                <div className="flex-1 overflow-auto p-8 z-10 font-sans">
                    {renderModule()}
                </div>

                <LivePulseFooter />
            </main>
        </div>
    );
}
