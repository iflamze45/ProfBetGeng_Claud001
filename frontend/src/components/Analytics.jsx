import { useState, useEffect, useCallback } from 'react';
import { BarChart3, TrendingUp, CheckCircle, RefreshCw, Users } from 'lucide-react';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN || 'pbg_admin_secret';

async function fetchAnalytics() {
    const res = await fetch(`${BASE_URL}/api/v1/admin/analytics`, {
        headers: { 'X-Admin-Token': ADMIN_TOKEN },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

function BarChart({ data }) {
    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center h-32 text-[#738091] text-[11px] font-mono uppercase tracking-widest">
                No data yet
            </div>
        );
    }

    const maxCount = Math.max(...data.map(d => d.count), 1);

    return (
        <div className="flex items-end gap-2 h-32 px-2 pt-4">
            {data.slice(-14).map((item, i) => {
                const heightPct = (item.count / maxCount) * 100;
                return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1 min-w-0">
                        <span className="text-[8px] font-mono text-[#738091]">{item.count}</span>
                        <div
                            className="w-full bg-sky-500/70 hover:bg-sky-400 transition-none"
                            style={{ height: `${Math.max(heightPct, 4)}%` }}
                            title={`${item.date}: ${item.count}`}
                        />
                        <span className="text-[7px] font-mono text-[#738091] truncate w-full text-center">
                            {item.date.slice(5)}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}

export default function Analytics() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            setData(await fetchAnalytics());
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const topKey = data?.conversions_per_key?.[0];
    const stats = data ? [
        { label: 'Total Conversions', value: data.total_conversions, icon: BarChart3, color: 'text-sky-500' },
        { label: 'Success Rate', value: `${(data.success_rate * 100).toFixed(1)}%`, icon: CheckCircle, color: 'text-emerald-500' },
        { label: 'Unique Keys', value: data.conversions_per_key.length, icon: Users, color: 'text-amber-500' },
        { label: 'Top Key', value: topKey ? `${topKey.count} req` : '—', icon: TrendingUp, color: 'text-purple-400' },
    ] : [];

    return (
        <div className="flex flex-col h-full space-y-6 font-sans dark">

            <div className="flex items-end justify-between border-b border-white/10 pb-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-white uppercase">Analytics</h2>
                    <p className="text-[10px] text-[#738091] uppercase tracking-widest mt-1.5 font-bold">
                        Admin — Conversion Intelligence
                    </p>
                </div>
                <button
                    onClick={load}
                    disabled={loading}
                    className="px-4 py-2 border border-white/10 bg-[#0B0E14] text-[11px] font-bold text-[#738091] hover:bg-[#151A22] flex items-center gap-2 uppercase disabled:opacity-40"
                >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </button>
            </div>

            {error && (
                <div className="px-5 py-3 text-[11px] text-red-400 font-mono border border-red-500/20 bg-red-500/5">
                    Error: {error}
                </div>
            )}

            {loading && !data ? (
                <div className="flex items-center justify-center h-32 text-[#738091] text-[11px] font-mono uppercase tracking-widest">
                    Loading…
                </div>
            ) : data && (
                <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {stats.map((stat, i) => (
                            <div key={i} className="border border-white/10 bg-[#0B0E14] p-5">
                                <div className="flex items-center justify-between mb-4">
                                    <span className="text-[11px] font-bold uppercase tracking-widest text-[#738091]">{stat.label}</span>
                                    <stat.icon className={`w-4 h-4 ${stat.color}`} />
                                </div>
                                <p className="text-3xl font-mono font-bold text-white tracking-tighter">{stat.value}</p>
                            </div>
                        ))}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
                        <div className="bg-[#0B0E14] border border-white/10 flex flex-col">
                            <div className="px-5 py-3 border-b border-white/10 bg-[#151A22]">
                                <h3 className="text-[12px] font-bold text-white uppercase tracking-wide">Daily Trend</h3>
                            </div>
                            <div className="flex-1 p-4">
                                <BarChart data={data.daily_trend} />
                            </div>
                        </div>

                        <div className="bg-[#0B0E14] border border-white/10 flex flex-col overflow-hidden">
                            <div className="px-5 py-3 border-b border-white/10 bg-[#151A22]">
                                <h3 className="text-[12px] font-bold text-white uppercase tracking-wide">Per-Key Usage</h3>
                            </div>
                            <div className="flex-1 overflow-auto">
                                {data.conversions_per_key.length === 0 ? (
                                    <div className="flex items-center justify-center h-20 text-[#738091] text-[11px] font-mono uppercase tracking-widest">
                                        No conversions yet
                                    </div>
                                ) : (
                                    <table className="w-full">
                                        <thead>
                                            <tr className="border-b border-white/10 bg-[#151A22]">
                                                {['API Key', 'Conversions'].map(h => (
                                                    <th key={h} className="px-5 py-2.5 text-left text-[9px] font-bold text-[#738091] uppercase tracking-widest">
                                                        {h}
                                                    </th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {data.conversions_per_key
                                                .sort((a, b) => b.count - a.count)
                                                .map((item, i) => (
                                                    <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                                                        <td className="px-5 py-2.5 font-mono text-[11px] text-sky-400 tracking-tighter">
                                                            {item.api_key.slice(0, 16)}…
                                                        </td>
                                                        <td className="px-5 py-2.5 font-mono text-[11px] text-white font-bold">
                                                            {item.count}
                                                        </td>
                                                    </tr>
                                                ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
