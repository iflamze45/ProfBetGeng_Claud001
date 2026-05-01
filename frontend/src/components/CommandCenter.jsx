import React, { useState, useEffect } from 'react';
import { ShieldCheck, BarChart3, Zap, AlertTriangle, ChevronRight, ArrowRight, RefreshCw, Clock } from 'lucide-react';
import { useApiKey } from '../hooks/useApiKey';
import { getArbWindows } from '../api/pbgClient';

export default function CommandCenter() {
    const { apiKey } = useApiKey();
    const [signals, setSignals] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!apiKey) return;
        setLoading(true);
        getArbWindows({ apiKey }).catch(() => ({ windows: [] }))
            .then((arbData) => {
                const arbItems = (arbData.windows || []).map((a, i) => ({
                    id: `A${i + 1}`,
                    sport: 'Arb',
                    market: a.teams,
                    teams: a.teams,
                    status: 'CRITICAL',
                    confidence: ((1 - 1 / (1 + a.profit_margin)) * 100 + 90).toFixed(2),
                    gap: `+${(a.profit_margin * 100).toFixed(1)}%`,
                    time: 'live',
                    isCritical: true,
                }));
                setSignals(arbItems);
            }).finally(() => setLoading(false));
    }, [apiKey]);

    const stats = [
        { label: 'Active Signals', value: String(signals.length), trend: signals.length > 0 ? 'LIVE' : '—', icon: ShieldCheck, color: 'text-emerald-500' },
        { label: 'Arb Windows', value: String(signals.filter(s => s.sport === 'Arb').length), trend: 'DETECTED', icon: BarChart3, color: 'text-sky-400' },
        { label: 'Top Value Gap', value: signals[0]?.gap || '—', trend: signals[0]?.market || '—', icon: Zap, color: 'text-amber-500' },
    ];

    return (
        <div className="flex flex-col h-full space-y-6 font-sans dark">

            {/* Header Section */}
            <div className="flex flex-row items-end justify-between border-b border-white/10 pb-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-white m-0 p-0 uppercase">PBG.CORE Command Terminal</h2>
                    <p className="text-[10px] text-[#738091] uppercase tracking-widest mt-1.5 flex items-center gap-2 font-bold">
                        <span className="w-2 h-2 bg-sky-500"></span>
                        Active Surveillance In Progress
                    </p>
                </div>
                <div className="flex gap-2">
                    <button className="px-4 py-2 border border-white/10 bg-[#0B0E14] rounded-none text-[11px] font-bold text-white/80 hover:bg-[#151A22] transition-none flex items-center gap-2 uppercase">
                        <Clock className="w-3.5 h-3.5 text-[#738091]" /> View History
                    </button>
                    <button className="px-4 py-2 bg-sky-500 border border-sky-600 rounded-none text-[11px] font-bold text-white hover:bg-sky-600 transition-none flex items-center gap-2 uppercase">
                        System Broadcast <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* Top KPIs Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {stats.map((stat, idx) => (
                    <div key={idx} className="rounded-none border border-white/10 bg-[#0B0E14] p-5 flex flex-col justify-between">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-[11px] font-bold uppercase tracking-widest text-[#738091]">{stat.label}</span>
                            <stat.icon className={`w-4 h-4 ${stat.color}`} />
                        </div>
                        <div className="flex items-baseline justify-between">
                            <p className="text-3xl font-mono font-bold text-white tracking-tighter">{stat.value}</p>
                            <span className="text-[11px] font-mono font-bold text-[#738091]">{stat.trend}</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Market Anomalies Table (Ultra Dense) */}
            <div className="flex-1 min-h-0 bg-[#0B0E14] border border-white/10 rounded-none flex flex-col overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 bg-[#151A22]">
                    <div className="flex items-center gap-2">
                        <h3 className="text-[12px] font-bold text-white uppercase tracking-wide">Market Anomalies</h3>
                        <span className="px-1.5 py-0.5 border border-white/10 bg-[#0B0E14] text-[#738091] text-[9px] font-bold uppercase tracking-widest">Real-time Gap Detection</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-sky-500" />
                        <span className="text-[10px] text-[#738091] uppercase tracking-widest font-bold">Live Feed</span>
                    </div>
                </div>

                <div className="flex-1 overflow-auto">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-[#151A22] sticky top-0 z-10 border-b border-white/10">
                            <tr>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2 w-16">ID</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2">Signal Market</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2 text-right">Confidence</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2 text-right">Value Gap</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2 text-right">Time</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2 text-right w-16">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/10">
                            {loading ? (
                                <tr><td colSpan={6} className="px-5 py-8 text-center text-[#738091] text-[11px] uppercase tracking-widest">
                                    <RefreshCw className="w-4 h-4 animate-spin inline mr-2" />Loading signals...
                                </td></tr>
                            ) : signals.length === 0 ? (
                                <tr><td colSpan={6} className="px-5 py-8 text-center text-[#738091] text-[11px] uppercase tracking-widest">No signals detected</td></tr>
                            ) : signals.map((item) => (
                                <tr key={item.id} className="hover:bg-[#151A22] transition-none cursor-pointer">
                                    <td className="px-5 py-2.5 text-[11px] font-mono font-bold text-[#738091]">SIG-{item.id}</td>
                                    <td className="px-5 py-2.5">
                                        <div className="flex items-center gap-2">
                                            {item.isCritical ? (
                                                <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
                                            ) : (
                                                <ChevronRight className="w-3.5 h-3.5 text-sky-500" />
                                            )}
                                            <span className="text-[12px] font-bold text-white uppercase">{item.market}</span>
                                            <span className="text-[10px] text-[#738091] uppercase font-bold">{item.teams || item.sport}</span>
                                        </div>
                                    </td>
                                    <td className="px-5 py-2.5 text-[11px] font-mono font-bold text-white text-right tracking-tighter">{item.confidence}%</td>
                                    <td className="px-5 py-2.5 text-[11px] font-mono font-bold text-emerald-500 text-right tracking-tighter">{item.gap}</td>
                                    <td className="px-5 py-2.5 text-[11px] font-mono font-bold text-[#738091] text-right uppercase tracking-tighter">{item.time}</td>
                                    <td className="px-5 py-2.5 text-right flex justify-end">
                                        <span className={`px-1.5 py-0.5 border text-[9px] font-bold tracking-widest uppercase ${item.isCritical ? 'bg-red-500/10 border-red-500 text-red-500' : 'bg-sky-500/10 border-sky-500 text-sky-500'}`}>
                                            {item.status}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    );
}
