import { useState, useEffect, useCallback } from 'react';
import { Users, Plus, Trash2, Ticket, UserMinus, RefreshCw } from 'lucide-react';
import { useApiKey } from '../hooks/useApiKey';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

function apiHeaders(apiKey) {
    return { 'Content-Type': 'application/json', 'X-API-Key': apiKey };
}

async function apiFetch(path, options = {}, apiKey) {
    const res = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers: { ...apiHeaders(apiKey), ...(options.headers || {}) },
    });
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
}

function EmptyState({ label }) {
    return (
        <div className="flex items-center justify-center h-20 text-[#738091] text-[11px] font-mono uppercase tracking-widest">
            {label}
        </div>
    );
}

function MemberList({ syndicate, apiKey }) {
    const [newKey, setNewKey] = useState('');
    const [busy, setBusy] = useState(false);
    const [members, setMembers] = useState([]);

    useEffect(() => {
        // Members are not returned from list endpoint; this panel shows what we've added locally
        setMembers([]);
    }, [syndicate?.id]);

    const handleAdd = async () => {
        if (!newKey.trim()) return;
        setBusy(true);
        try {
            const m = await apiFetch(
                `/api/v1/syndicates/${syndicate.id}/members`,
                { method: 'POST', body: JSON.stringify({ api_key: newKey.trim() }) },
                apiKey,
            );
            setMembers(prev => [...prev, m]);
            setNewKey('');
        } catch (e) {
            alert(e.message);
        } finally { setBusy(false); }
    };

    const handleRemove = async (memberKey) => {
        setBusy(true);
        try {
            await apiFetch(
                `/api/v1/syndicates/${syndicate.id}/members/${encodeURIComponent(memberKey)}`,
                { method: 'DELETE' },
                apiKey,
            );
            setMembers(prev => prev.filter(m => m.api_key !== memberKey));
        } catch (e) {
            alert(e.message);
        } finally { setBusy(false); }
    };

    return (
        <div className="flex flex-col gap-3">
            <div className="flex gap-2">
                <input
                    className="flex-1 bg-[#0B0E14] border border-white/20 text-white text-[11px] px-3 py-2 font-mono outline-none placeholder:text-[#738091]"
                    placeholder="Paste API key to invite..."
                    value={newKey}
                    onChange={e => setNewKey(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAdd()}
                />
                <button
                    onClick={handleAdd}
                    disabled={busy || !newKey.trim()}
                    className="px-4 py-2 bg-sky-500 text-white text-[11px] font-bold uppercase disabled:opacity-40 hover:bg-sky-400"
                >
                    <Plus className="w-3.5 h-3.5" />
                </button>
            </div>
            {members.length === 0 ? (
                <EmptyState label="No members added this session" />
            ) : (
                <div className="space-y-1">
                    {members.map((m, i) => (
                        <div key={i} className="flex items-center justify-between px-3 py-2 bg-[#0B0E14] border border-white/5">
                            <span className="font-mono text-[11px] text-sky-400">{m.api_key.slice(0, 20)}…</span>
                            <button
                                onClick={() => handleRemove(m.api_key)}
                                disabled={busy}
                                className="text-[#738091] hover:text-red-400"
                            >
                                <UserMinus className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function TicketPanel({ syndicate, apiKey }) {
    const [code, setCode] = useState('');
    const [tickets, setTickets] = useState([]);
    const [busy, setBusy] = useState(false);

    const handleAdd = async () => {
        if (!code.trim()) return;
        setBusy(true);
        try {
            const t = await apiFetch(
                `/api/v1/syndicates/${syndicate.id}/tickets`,
                { method: 'POST', body: JSON.stringify({ booking_code: code.trim() }) },
                apiKey,
            );
            setTickets(prev => [...prev, t]);
            setCode('');
        } catch (e) {
            alert(e.message);
        } finally { setBusy(false); }
    };

    return (
        <div className="flex flex-col gap-3">
            <div className="flex gap-2">
                <input
                    className="flex-1 bg-[#0B0E14] border border-white/20 text-white text-[11px] px-3 py-2 font-mono outline-none placeholder:text-[#738091]"
                    placeholder="Booking code (e.g. SB123456)..."
                    value={code}
                    onChange={e => setCode(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAdd()}
                />
                <button
                    onClick={handleAdd}
                    disabled={busy || !code.trim()}
                    className="px-4 py-2 bg-emerald-600 text-white text-[11px] font-bold uppercase disabled:opacity-40 hover:bg-emerald-500"
                >
                    <Ticket className="w-3.5 h-3.5" />
                </button>
            </div>
            {tickets.length === 0 ? (
                <EmptyState label="No tickets shared yet" />
            ) : (
                <div className="space-y-1">
                    {tickets.map((t, i) => (
                        <div key={i} className="flex items-center justify-between px-3 py-2 bg-[#0B0E14] border border-white/5">
                            <span className="font-mono text-[11px] text-emerald-400">{t.booking_code}</span>
                            <span className="text-[9px] text-[#738091] font-mono uppercase">
                                {new Date(t.added_at).toLocaleDateString()}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function Syndicate() {
    const { apiKey } = useApiKey();
    const [syndicates, setSyndicates] = useState([]);
    const [selected, setSelected] = useState(null);
    const [activePanel, setActivePanel] = useState('members');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [creating, setCreating] = useState(false);
    const [newName, setNewName] = useState('');

    const load = useCallback(async () => {
        if (!apiKey) return;
        setLoading(true);
        setError(null);
        try {
            const data = await apiFetch('/api/v1/syndicates', {}, apiKey);
            setSyndicates(data.syndicates || []);
        } catch (e) {
            setError(e.message);
        } finally { setLoading(false); }
    }, [apiKey]);

    useEffect(() => { load(); }, [load]);

    const handleCreate = async () => {
        if (!newName.trim()) return;
        setCreating(true);
        try {
            const s = await apiFetch(
                '/api/v1/syndicates',
                { method: 'POST', body: JSON.stringify({ name: newName.trim() }) },
                apiKey,
            );
            setSyndicates(prev => [s, ...prev]);
            setNewName('');
            setSelected(s);
        } catch (e) {
            setError(e.message);
        } finally { setCreating(false); }
    };

    const handleDelete = async (syndicate) => {
        try {
            await apiFetch(`/api/v1/syndicates/${syndicate.id}`, { method: 'DELETE' }, apiKey);
            setSyndicates(prev => prev.filter(s => s.id !== syndicate.id));
            if (selected?.id === syndicate.id) setSelected(null);
        } catch (e) {
            setError(e.message);
        }
    };

    if (!apiKey) {
        return (
            <div className="flex items-center justify-center h-full text-[#738091] text-[11px] font-mono uppercase tracking-widest">
                API key required — enter key in Command Center
            </div>
        );
    }

    return (
        <div className="flex h-full gap-4 font-sans dark">

            {/* Left — Syndicate list */}
            <div className="w-72 flex flex-col border border-white/10 bg-[#0B0E14]">
                <div className="px-5 py-3 border-b border-white/10 bg-[#151A22] flex items-center justify-between">
                    <h3 className="text-[12px] font-bold text-white uppercase tracking-wide flex items-center gap-2">
                        <Users className="w-3.5 h-3.5 text-sky-500" /> My Syndicates
                    </h3>
                    <button onClick={load} disabled={loading} className="text-[#738091] hover:text-white">
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                <div className="p-3 border-b border-white/10 flex gap-2">
                    <input
                        className="flex-1 bg-[#151A22] border border-white/10 text-white text-[11px] px-2 py-1.5 font-mono outline-none placeholder:text-[#738091]"
                        placeholder="New syndicate name..."
                        value={newName}
                        onChange={e => setNewName(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleCreate()}
                    />
                    <button
                        onClick={handleCreate}
                        disabled={creating || !newName.trim()}
                        className="px-3 py-1.5 bg-sky-500 text-white text-[11px] font-bold disabled:opacity-40 hover:bg-sky-400"
                    >
                        <Plus className="w-3.5 h-3.5" />
                    </button>
                </div>

                {error && (
                    <div className="px-3 py-2 text-[10px] text-red-400 font-mono border-b border-white/5">
                        {error}
                    </div>
                )}

                <div className="flex-1 overflow-auto">
                    {loading ? (
                        <EmptyState label="Loading…" />
                    ) : syndicates.length === 0 ? (
                        <EmptyState label="No syndicates yet" />
                    ) : (
                        syndicates.map(s => (
                            <button
                                key={s.id}
                                onClick={() => { setSelected(s); setActivePanel('members'); }}
                                className={`w-full px-4 py-3 flex items-center justify-between text-left border-b border-white/5 hover:bg-white/[0.02] ${
                                    selected?.id === s.id ? 'border-l-4 border-l-sky-500 bg-[#151A22]' : 'border-l-4 border-l-transparent'
                                }`}
                            >
                                <div>
                                    <p className="text-[11px] font-bold text-white uppercase tracking-wide">{s.name}</p>
                                    <p className="text-[9px] text-[#738091] font-mono mt-0.5">
                                        {new Date(s.created_at).toLocaleDateString()}
                                    </p>
                                </div>
                                <button
                                    onClick={e => { e.stopPropagation(); handleDelete(s); }}
                                    className="text-[#738091] hover:text-red-400 ml-2"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            </button>
                        ))
                    )}
                </div>
            </div>

            {/* Right — Detail panel */}
            <div className="flex-1 flex flex-col border border-white/10 bg-[#0B0E14]">
                {!selected ? (
                    <div className="flex items-center justify-center h-full text-[#738091] text-[11px] font-mono uppercase tracking-widest">
                        Select a syndicate
                    </div>
                ) : (
                    <>
                        <div className="px-5 py-3 border-b border-white/10 bg-[#151A22] flex items-center justify-between">
                            <div>
                                <h3 className="text-[14px] font-bold text-white uppercase tracking-wide">{selected.name}</h3>
                                <p className="text-[9px] text-[#738091] font-mono mt-0.5">ID: {selected.id.slice(0, 8)}…</p>
                            </div>
                            <div className="flex gap-1">
                                {['members', 'tickets'].map(panel => (
                                    <button
                                        key={panel}
                                        onClick={() => setActivePanel(panel)}
                                        className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest ${
                                            activePanel === panel
                                                ? 'bg-sky-500 text-white'
                                                : 'bg-[#0B0E14] border border-white/10 text-[#738091] hover:text-white'
                                        }`}
                                    >
                                        {panel === 'members' ? <Users className="w-3.5 h-3.5 inline mr-1" /> : <Ticket className="w-3.5 h-3.5 inline mr-1" />}
                                        {panel}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="flex-1 p-5 overflow-auto">
                            {activePanel === 'members' ? (
                                <MemberList syndicate={selected} apiKey={apiKey} onRefresh={load} />
                            ) : (
                                <TicketPanel syndicate={selected} apiKey={apiKey} />
                            )}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
