import { useState, useEffect } from 'react';
import { Server, Activity, ShieldAlert, Cpu, Gavel, Filter, RefreshCw } from 'lucide-react';
import { useApiKey } from '../hooks/useApiKey';
const getSgnNodes = () => Promise.resolve([]);
const getGovProposals = () => Promise.resolve([]);

export default function GovernanceHUD() {
    const { apiKey } = useApiKey();
    const [nodes, setNodes] = useState([]);
    const [proposals, setProposals] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!apiKey) return;
        setLoading(true);
        Promise.all([
            getSgnNodes(apiKey).catch(() => []),
            getGovProposals(apiKey).catch(() => []),
        ]).then(([nodeData, propData]) => {
            setNodes(Array.isArray(nodeData) ? nodeData : []);
            setProposals(Array.isArray(propData) ? propData : []);
        }).finally(() => setLoading(false));
    }, [apiKey]);

    const activeNodes = nodes.filter(n => n.status === 'ONLINE').length;

    const stats = [
        { label: 'Active Nodes', value: String(activeNodes), trend: `${nodes.length} TOTAL`, icon: Cpu, color: 'text-sky-500' },
        { label: 'Governance Proposals', value: String(proposals.length), trend: proposals.length === 0 ? 'CLEAR' : 'PENDING', icon: ShieldAlert, color: 'text-emerald-500' },
        { label: 'Avg Latency', value: nodes.length ? `${Math.round(nodes.reduce((a, n) => a + (n.latency_ms || 0), 0) / nodes.length)}ms` : '—', trend: 'MESH', icon: Activity, color: 'text-amber-500' },
    ];

    return (
        <div className="flex flex-col h-full space-y-6 font-sans dark">

            {/* Header Section */}
            <div className="flex flex-row items-end justify-between border-b border-white/10 pb-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-white m-0 p-0 uppercase">SARGE Command Dashboard</h2>
                    <p className="text-[10px] text-[#738091] uppercase tracking-widest mt-1.5 flex items-center gap-2 font-bold">
                        <span className="w-2 h-2 bg-emerald-500"></span>
                        Multi-Team Isolation & Governance Active
                    </p>
                </div>
                <div className="flex gap-2">
                    <button className="px-4 py-2 border border-white/10 bg-[#0B0E14] text-[11px] font-bold text-[#738091]-emphasis rounded-none hover:bg-[#151A22] transition-none flex items-center gap-2 uppercase">
                        <Server className="w-3.5 h-3.5" /> Registry Sync
                    </button>
                    <button className="px-4 py-2 bg-red-500 border border-red-600 text-[11px] font-bold text-white hover:bg-red-600 rounded-none transition-none flex items-center gap-2 uppercase">
                        <Gavel className="w-3.5 h-3.5" /> Execute Purge
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
                            <span className={`text-[11px] font-mono font-bold ${stat.trend === 'WARNING' ? 'text-red-500' : 'text-[#738091]'}`}>{stat.trend}</span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Active Intelligence Registry Table */}
            <div className="flex-1 min-h-0 bg-[#0B0E14] border border-white/10 rounded-none flex flex-col overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-white/10 bg-[#151A22]">
                    <div className="flex items-center gap-2">
                        <h3 className="text-[12px] font-bold text-white uppercase tracking-wide">Satellite Node Registry</h3>
                        <span className="px-1.5 py-0.5 border border-white/10 bg-[#0B0E14] text-[#738091] text-[9px] font-bold uppercase tracking-widest">SGN Mesh</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Filter className="w-3.5 h-3.5 text-sky-500" />
                        <span className="text-[10px] text-[#738091] uppercase tracking-widest font-bold">Filter By Owner</span>
                    </div>
                </div>

                <div className="flex-1 overflow-auto">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-[#151A22] sticky top-0 z-10 border-b border-white/10">
                            <tr>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2">Node ID</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2">Region</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2 text-right">Latency</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2 text-right">Active Tasks</th>
                                <th className="text-[10px] uppercase font-bold text-[#738091] tracking-widest px-5 py-2 text-right">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/10">
                            {loading ? (
                                <tr><td colSpan={5} className="px-5 py-8 text-center text-[#738091] text-[11px] uppercase tracking-widest">
                                    <RefreshCw className="w-4 h-4 animate-spin inline mr-2" />Loading nodes...
                                </td></tr>
                            ) : nodes.length === 0 ? (
                                <tr><td colSpan={5} className="px-5 py-8 text-center text-[#738091] text-[11px] uppercase tracking-widest">No nodes registered</td></tr>
                            ) : nodes.map((node) => (
                                <tr key={node.id} className="hover:bg-[#151A22] transition-none cursor-pointer">
                                    <td className="px-5 py-2.5 flex flex-col">
                                        <span className="text-[12px] font-bold text-white uppercase">{node.id}</span>
                                        <span className="text-[10px] font-mono text-[#738091] tracking-tighter">{node.endpoint}</span>
                                    </td>
                                    <td className="px-5 py-2.5">
                                        <div className="flex items-center gap-2">
                                            <Server className="w-3.5 h-3.5 text-sky-500" />
                                            <span className="text-[11px] font-bold text-white uppercase">{node.region}</span>
                                        </div>
                                    </td>
                                    <td className="px-5 py-2.5 text-[11px] font-mono font-bold text-white text-right tracking-tighter">
                                        {node.latency_ms ?? 0}ms
                                    </td>
                                    <td className="px-5 py-2.5 text-[11px] font-mono font-bold text-white text-right tracking-tighter">
                                        {node.active_tasks ?? 0}
                                    </td>
                                    <td className="px-5 py-2.5 text-right">
                                        <span className={`px-1.5 py-0.5 border text-[9px] font-bold tracking-widest uppercase ${node.status === 'ONLINE' ? 'bg-emerald-500/10 border-emerald-500 text-emerald-500' : 'bg-red-500/10 border-red-500 text-red-500'}`}>
                                            {node.status}
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
