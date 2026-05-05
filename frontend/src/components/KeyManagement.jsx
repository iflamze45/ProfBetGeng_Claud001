import { useState, useEffect, useCallback } from 'react';
import { Key, RefreshCw, Trash2, ToggleLeft, ToggleRight, Edit2, Check, X } from 'lucide-react';
import { adminListKeys, adminDeactivateKey, adminPatchKey } from '../api/pbgClient';

function StatusBadge({ isActive }) {
    return (
        <span className={`px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest ${
            isActive
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-red-500/10 text-red-400 border border-red-500/30'
        }`}>
            {isActive ? 'ACTIVE' : 'REVOKED'}
        </span>
    );
}

function KeyRow({ keyData, onDeactivate, onPatch }) {
    const [editing, setEditing] = useState(false);
    const [nameInput, setNameInput] = useState(keyData.name || '');
    const [busy, setBusy] = useState(false);

    const handleDeactivate = async () => {
        if (!keyData.is_active) return;
        setBusy(true);
        try { await onDeactivate(keyData.key_id); } finally { setBusy(false); }
    };

    const handleToggle = async () => {
        setBusy(true);
        try { await onPatch(keyData.key_id, { is_active: !keyData.is_active }); } finally { setBusy(false); }
    };

    const handleRename = async () => {
        if (nameInput.trim() === keyData.name) { setEditing(false); return; }
        setBusy(true);
        try {
            await onPatch(keyData.key_id, { name: nameInput.trim() });
            setEditing(false);
        } finally { setBusy(false); }
    };

    return (
        <tr className="border-b border-white/5 hover:bg-white/[0.02] transition-none">
            <td className="px-5 py-3 font-mono text-[11px] text-sky-400 tracking-tighter">
                {keyData.key_prefix}…
            </td>
            <td className="px-5 py-3">
                {editing ? (
                    <div className="flex items-center gap-2">
                        <input
                            className="bg-[#0B0E14] border border-white/20 text-white text-[11px] px-2 py-1 font-mono outline-none w-40"
                            value={nameInput}
                            onChange={e => setNameInput(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') setEditing(false); }}
                            autoFocus
                        />
                        <button onClick={handleRename} disabled={busy} className="text-emerald-400 hover:text-emerald-300">
                            <Check className="w-3.5 h-3.5" />
                        </button>
                        <button onClick={() => setEditing(false)} className="text-[#738091] hover:text-white">
                            <X className="w-3.5 h-3.5" />
                        </button>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 group">
                        <span className="text-[11px] font-bold text-white">{keyData.name || '—'}</span>
                        <button
                            onClick={() => setEditing(true)}
                            className="opacity-0 group-hover:opacity-100 text-[#738091] hover:text-white transition-opacity"
                        >
                            <Edit2 className="w-3 h-3" />
                        </button>
                    </div>
                )}
            </td>
            <td className="px-5 py-3">
                <StatusBadge isActive={keyData.is_active} />
            </td>
            <td className="px-5 py-3 font-mono text-[11px] text-[#738091]">
                {keyData.request_count ?? 0}
            </td>
            <td className="px-5 py-3 font-mono text-[11px] text-[#738091]">
                {keyData.last_used_at
                    ? new Date(keyData.last_used_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                    : '—'}
            </td>
            <td className="px-5 py-3">
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleToggle}
                        disabled={busy}
                        title={keyData.is_active ? 'Revoke key' : 'Re-activate key'}
                        className="text-[#738091] hover:text-sky-400 disabled:opacity-30 transition-none"
                    >
                        {keyData.is_active
                            ? <ToggleRight className="w-4 h-4 text-emerald-400" />
                            : <ToggleLeft className="w-4 h-4" />}
                    </button>
                    <button
                        onClick={handleDeactivate}
                        disabled={busy || !keyData.is_active}
                        title="Permanently deactivate"
                        className="text-[#738091] hover:text-red-400 disabled:opacity-30 transition-none"
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            </td>
        </tr>
    );
}

export default function KeyManagement() {
    const [keys, setKeys] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await adminListKeys();
            setKeys(data.keys || []);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const handleDeactivate = async (keyId) => {
        await adminDeactivateKey(keyId);
        setKeys(prev => prev.map(k => k.key_id === keyId ? { ...k, is_active: false } : k));
    };

    const handlePatch = async (keyId, updates) => {
        const updated = await adminPatchKey(keyId, updates);
        setKeys(prev => prev.map(k => k.key_id === keyId ? { ...k, ...updated } : k));
    };

    const activeCount = keys.filter(k => k.is_active).length;
    const totalRequests = keys.reduce((sum, k) => sum + (k.request_count || 0), 0);

    return (
        <div className="flex flex-col h-full space-y-6 font-sans dark">

            <div className="flex items-end justify-between border-b border-white/10 pb-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight text-white uppercase">Key Management</h2>
                    <p className="text-[10px] text-[#738091] uppercase tracking-widest mt-1.5 font-bold">
                        Admin — API Key Registry
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

            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: 'Total Keys', value: keys.length, icon: Key, color: 'text-sky-500' },
                    { label: 'Active Keys', value: activeCount, icon: ToggleRight, color: 'text-emerald-500' },
                    { label: 'Total Requests', value: totalRequests, icon: RefreshCw, color: 'text-amber-500' },
                ].map((stat, i) => (
                    <div key={i} className="border border-white/10 bg-[#0B0E14] p-5">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-[11px] font-bold uppercase tracking-widest text-[#738091]">{stat.label}</span>
                            <stat.icon className={`w-4 h-4 ${stat.color}`} />
                        </div>
                        <p className="text-3xl font-mono font-bold text-white tracking-tighter">{stat.value}</p>
                    </div>
                ))}
            </div>

            <div className="flex-1 min-h-0 bg-[#0B0E14] border border-white/10 flex flex-col overflow-hidden">
                <div className="px-5 py-3 border-b border-white/10 bg-[#151A22] flex items-center gap-2">
                    <h3 className="text-[12px] font-bold text-white uppercase tracking-wide">API Key Registry</h3>
                    <span className="px-1.5 py-0.5 border border-white/10 bg-[#0B0E14] text-[#738091] text-[9px] font-bold uppercase tracking-widest">
                        {keys.length} KEYS
                    </span>
                </div>

                {error && (
                    <div className="px-5 py-3 text-[11px] text-red-400 font-mono border-b border-white/10">
                        Error: {error}
                    </div>
                )}

                <div className="flex-1 overflow-auto">
                    {loading ? (
                        <div className="flex items-center justify-center h-32 text-[#738091] text-[11px] font-mono uppercase tracking-widest">
                            Loading…
                        </div>
                    ) : keys.length === 0 ? (
                        <div className="flex items-center justify-center h-32 text-[#738091] text-[11px] font-mono uppercase tracking-widest">
                            No keys found
                        </div>
                    ) : (
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-white/10 bg-[#151A22]">
                                    {['Prefix', 'Name', 'Status', 'Requests', 'Last Used', 'Actions'].map(h => (
                                        <th key={h} className="px-5 py-2.5 text-left text-[9px] font-bold text-[#738091] uppercase tracking-widest">
                                            {h}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {keys.map(key => (
                                    <KeyRow
                                        key={key.key_id}
                                        keyData={key}
                                        onDeactivate={handleDeactivate}
                                        onPatch={handlePatch}
                                    />
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
}
