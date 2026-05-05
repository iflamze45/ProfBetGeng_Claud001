import { useEffect, useMemo, useState } from 'react';
import {
    Activity,
    AlertTriangle,
    CircleDot,
    Database,
    Ghost,
    Globe,
    Lock,
    Play,
    RefreshCw,
    Server,
    Shield,
    TrendingUp,
    Zap,
} from 'lucide-react';
import { useApiKey } from '../hooks/useApiKey';
import { getArbWindows, getMarketSignals } from '../api/pbgClient';

const stub = () => Promise.reject(new Error('Endpoint not available'));
const executeInstitutionalTrade = stub;
const executeRecursiveFeedback = stub;
const getDarkPoolDepth = stub;
const getMindStatus = stub;
const getRiskProfile = stub;
const getSgnNodes = () => Promise.resolve([]);
const getSolanaVault = stub;
const getVaultStatus = stub;
const initiateGhostProtocol = stub;
const initiateOmegaLock = stub;
const simulateMeshFailure = stub;
const triggerBeyondHorizon = stub;
const triggerMindOoda = stub;

function ModuleShell({ title, eyebrow, status = 'CONNECTED', children, actions }) {
    return (
        <div className="flex flex-col h-full space-y-6 font-sans">
            <div className="flex flex-col gap-4 border-b border-white/10 pb-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <h2 className="m-0 p-0 text-2xl font-bold uppercase tracking-tight text-white">{title}</h2>
                    <p className="mt-1.5 flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[#738091]">
                        <span className="h-2 w-2 bg-sky-500" />
                        {eyebrow}
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <span className="border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                        {status}
                    </span>
                    {actions}
                </div>
            </div>
            {children}
        </div>
    );
}

function StatCard({ label, value, trend, icon: Icon = Activity, tone = 'text-sky-400' }) {
    return (
        <div className="border border-white/10 bg-[#0B0E14] p-5">
            <div className="mb-4 flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-widest text-[#738091]">{label}</span>
                <Icon className={`h-4 w-4 ${tone}`} />
            </div>
            <div className="flex items-baseline justify-between gap-4">
                <p className="truncate font-mono text-3xl font-bold tracking-tighter text-white">{value}</p>
                <span className="truncate text-right font-mono text-[11px] font-bold uppercase text-[#738091]">{trend}</span>
            </div>
        </div>
    );
}

function DataTable({ columns, rows, empty = 'No live data returned' }) {
    return (
        <div className="min-h-0 flex-1 overflow-hidden border border-white/10 bg-[#0B0E14]">
            <div className="overflow-auto">
                <table className="w-full border-collapse text-left">
                    <thead className="sticky top-0 z-10 border-b border-white/10 bg-[#151A22]">
                        <tr>
                            {columns.map((column) => (
                                <th key={column.key} className={`px-5 py-2 text-[10px] font-bold uppercase tracking-widest text-[#738091] ${column.align === 'right' ? 'text-right' : ''}`}>
                                    {column.label}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/10">
                        {rows.length === 0 ? (
                            <tr>
                                <td colSpan={columns.length} className="px-5 py-8 text-center text-[11px] font-bold uppercase tracking-widest text-[#738091]">
                                    {empty}
                                </td>
                            </tr>
                        ) : rows.map((row, index) => (
                            <tr key={row.id || index} className="hover:bg-[#151A22]">
                                {columns.map((column) => (
                                    <td key={column.key} className={`px-5 py-3 text-[12px] font-bold text-white ${column.align === 'right' ? 'text-right font-mono tracking-tighter' : ''}`}>
                                        {column.render ? column.render(row) : row[column.key]}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function ActionButton({ children, onClick, tone = 'sky', disabled }) {
    const classes = tone === 'red'
        ? 'border-red-600 bg-red-500 text-white hover:bg-red-600'
        : tone === 'dark'
            ? 'border-white/10 bg-[#0B0E14] text-white hover:bg-white/5'
            : 'border-sky-600 bg-sky-500 text-white hover:bg-sky-600';
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`flex items-center gap-2 border px-4 py-2 text-[11px] font-bold uppercase tracking-widest disabled:cursor-not-allowed disabled:opacity-50 ${classes}`}
        >
            {children}
        </button>
    );
}

function useModuleData(loader, deps) {
    const { apiKey, loading: keyLoading, error: keyError } = useApiKey();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const refresh = async () => {
        if (!apiKey) return;
        setLoading(true);
        setError('');
        try {
            setData(await loader(apiKey));
        } catch (err) {
            setError(err.message || 'Request failed');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        refresh();
    }, [apiKey, ...deps]);

    return { apiKey, data, loading: loading || keyLoading, error: error || keyError, refresh };
}

function StatusLine({ loading, error, children }) {
    if (loading) {
        return <div className="text-[11px] font-bold uppercase tracking-widest text-[#738091]"><RefreshCw className="mr-2 inline h-4 w-4 animate-spin" />Loading module data...</div>;
    }
    if (error) {
        return <div className="text-[11px] font-bold uppercase tracking-widest text-red-400"><AlertTriangle className="mr-2 inline h-4 w-4" />{error}</div>;
    }
    return children || null;
}

export function MarketScannerModule() {
    const { data, loading, error, refresh } = useModuleData(async (apiKey) => {
        const [signals, arbs] = await Promise.all([
            getMarketSignals(apiKey).catch(() => ({ signals: [] })),
            getArbWindows({ apiKey }).catch(() => ({ windows: [] })),
        ]);
        return { signals: signals.signals || [], arbs: arbs.windows || [] };
    }, []);

    const rows = useMemo(() => [
        ...(data?.signals || []).map((signal, index) => ({
            id: `SIG-${index + 1}`,
            market: signal.market,
            teams: signal.teams,
            edge: `+${((signal.value_score || 0) * 100).toFixed(1)}%`,
            source: signal.signal_type || 'VALUE',
        })),
        ...(data?.arbs || []).map((arb) => ({
            id: arb.match_id,
            market: 'Arbitrage Window',
            teams: arb.teams,
            edge: `+${((arb.profit_margin || 0) * 100).toFixed(1)}%`,
            source: Object.values(arb.bookmakers || {}).join(' / '),
        })),
    ], [data]);

    return (
        <ModuleShell title="Market Scanner" eyebrow="Signals, arbitrage windows, and value-gap discovery" actions={<ActionButton tone="dark" onClick={refresh}><RefreshCw className="h-3.5 w-3.5" />Refresh</ActionButton>}>
            <StatusLine loading={loading} error={error} />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard label="Signals" value={String(data?.signals?.length || 0)} trend="market feed" icon={CircleDot} tone="text-emerald-400" />
                <StatCard label="Arb Windows" value={String(data?.arbs?.length || 0)} trend="cross-book" icon={TrendingUp} tone="text-sky-400" />
                <StatCard label="Top Edge" value={rows[0]?.edge || '—'} trend={rows[0]?.teams || 'none'} icon={Zap} tone="text-amber-400" />
            </div>
            <DataTable
                columns={[
                    { key: 'id', label: 'ID' },
                    { key: 'market', label: 'Market' },
                    { key: 'teams', label: 'Event' },
                    { key: 'source', label: 'Source' },
                    { key: 'edge', label: 'Edge', align: 'right' },
                ]}
                rows={rows}
                empty="No scanner signals are active"
            />
        </ModuleShell>
    );
}

export function ExecutionModule() {
    const { data, loading, error, refresh } = useModuleData(async (apiKey) => {
        const [history, risk] = await Promise.all([
            fetch('/api/v1/history', { headers: { 'X-API-Key': apiKey } }).then((res) => res.json()).catch(() => ({ records: [], count: 0 })),
            getRiskProfile(apiKey),
        ]);
        return { history, risk };
    }, []);

    const rows = (data?.history?.records || []).map((record, index) => ({
        id: record.source_booking_code || `REC-${index + 1}`,
        selections: record.selections_count,
        converted: record.converted_count,
        risk: record.risk_level || '—',
        odds: record.total_odds ? Number(record.total_odds).toFixed(2) : '—',
    }));

    return (
        <ModuleShell title="Execution SEA" eyebrow="Conversion history, execution health, and risk telemetry" actions={<ActionButton tone="dark" onClick={refresh}><RefreshCw className="h-3.5 w-3.5" />Refresh</ActionButton>}>
            <StatusLine loading={loading} error={error} />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard label="History Records" value={String(data?.history?.count || 0)} trend="local storage" icon={Database} />
                <StatCard label="Sharpe" value={data?.risk?.sharpe_ratio?.toFixed?.(3) || '—'} trend="risk engine" icon={Activity} tone="text-emerald-400" />
                <StatCard label="Max Drawdown" value={data?.risk?.max_drawdown != null ? `${(data.risk.max_drawdown * 100).toFixed(1)}%` : '—'} trend="portfolio" icon={Shield} tone="text-amber-400" />
            </div>
            <DataTable
                columns={[
                    { key: 'id', label: 'Booking' },
                    { key: 'selections', label: 'Legs', align: 'right' },
                    { key: 'converted', label: 'Converted', align: 'right' },
                    { key: 'odds', label: 'Odds', align: 'right' },
                    { key: 'risk', label: 'Risk', align: 'right' },
                ]}
                rows={rows}
                empty="No conversions have been stored for this API key"
            />
        </ModuleShell>
    );
}

export function InstitutionalModule() {
    const [marketId, setMarketId] = useState('GLOBAL_MARKET_01');
    const [actionResult, setActionResult] = useState(null);
    const { apiKey, data, loading, error, refresh } = useModuleData((key) => getDarkPoolDepth({ apiKey: key, marketId }), [marketId]);

    const executeDeal = async () => {
        setActionResult(await executeInstitutionalTrade({ apiKey, marketId, amountUsd: 50000 }));
        refresh();
    };

    const depthRows = Object.entries(data || {}).map(([book, amount]) => ({ id: book, book, amount: `$${Number(amount).toLocaleString()}` }));

    return (
        <ModuleShell title="Institutional Oracle" eyebrow="Dark-pool depth and wholesale execution bridge" actions={<ActionButton onClick={executeDeal} disabled={!apiKey}><Play className="h-3.5 w-3.5" />Execute Test Fill</ActionButton>}>
            <div className="flex max-w-sm flex-col gap-2">
                <label className="text-[10px] font-bold uppercase tracking-widest text-[#738091]">Market ID</label>
                <input value={marketId} onChange={(event) => setMarketId(event.target.value)} className="border border-white/10 bg-[#0B0E14] px-4 py-3 font-mono text-[13px] text-white outline-none focus:border-sky-500" />
            </div>
            <StatusLine loading={loading} error={error} />
            {actionResult && <pre className="overflow-auto border border-emerald-500/30 bg-emerald-500/10 p-4 text-[11px] text-emerald-100">{JSON.stringify(actionResult, null, 2)}</pre>}
            <DataTable columns={[{ key: 'book', label: 'Counterparty' }, { key: 'amount', label: 'Depth', align: 'right' }]} rows={depthRows} empty="No institutional depth returned" />
        </ModuleShell>
    );
}

export function TreasuryModule() {
    const { data, loading, error, refresh } = useModuleData(async (apiKey) => {
        const [vault, secureVault, risk] = await Promise.all([getSolanaVault(apiKey), getVaultStatus(apiKey), getRiskProfile(apiKey)]);
        return { vault, secureVault, risk };
    }, []);

    const balances = Object.entries(data?.vault?.balances || {}).map(([asset, amount]) => ({ id: asset, asset, amount: Number(amount).toLocaleString() }));

    return (
        <ModuleShell title="Sovereign Wealth" eyebrow="Vault balances, credential vault, and risk posture" actions={<ActionButton tone="dark" onClick={refresh}><RefreshCw className="h-3.5 w-3.5" />Refresh</ActionButton>}>
            <StatusLine loading={loading} error={error} />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard label="Vault Address" value={data?.vault?.address || '—'} trend="solana bridge" icon={Lock} />
                <StatCard label="Credential Vaults" value={String(data?.secureVault?.active_vaults?.length || 0)} trend={data?.secureVault?.security_level || '—'} icon={Shield} tone="text-emerald-400" />
                <StatCard label="Portfolio Alpha" value={data?.risk?.alpha != null ? `${(data.risk.alpha * 100).toFixed(1)}%` : '—'} trend="risk profile" icon={TrendingUp} tone="text-amber-400" />
            </div>
            <DataTable columns={[{ key: 'asset', label: 'Asset' }, { key: 'amount', label: 'Balance', align: 'right' }]} rows={balances} empty="No vault balances returned" />
        </ModuleShell>
    );
}

export function MeshModule() {
    const { apiKey, data, loading, error, refresh } = useModuleData(getSgnNodes, []);
    const [result, setResult] = useState(null);
    const nodes = Array.isArray(data) ? data : [];

    const simulateFirstNode = async () => {
        if (!nodes[0]) return;
        setResult(await simulateMeshFailure({ apiKey, nodeId: nodes[0].id }));
        refresh();
    };

    return (
        <ModuleShell title="Neural Mesh" eyebrow="Satellite node registry and failover simulation" actions={<ActionButton tone="red" onClick={simulateFirstNode} disabled={!nodes.length}><AlertTriangle className="h-3.5 w-3.5" />Simulate Failure</ActionButton>}>
            <StatusLine loading={loading} error={error} />
            {result && <pre className="overflow-auto border border-red-500/30 bg-red-500/10 p-4 text-[11px] text-red-100">{JSON.stringify(result, null, 2)}</pre>}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard label="Nodes" value={String(nodes.length)} trend="registered" icon={Server} />
                <StatCard label="Online" value={String(nodes.filter((node) => node.status === 'ONLINE').length)} trend="active" icon={Globe} tone="text-emerald-400" />
                <StatCard label="Avg Latency" value={nodes.length ? `${Math.round(nodes.reduce((sum, node) => sum + (node.latency_ms || 0), 0) / nodes.length)}ms` : '—'} trend="mesh" icon={Activity} />
            </div>
            <DataTable
                columns={[
                    { key: 'id', label: 'Node' },
                    { key: 'region', label: 'Region' },
                    { key: 'endpoint', label: 'Endpoint' },
                    { key: 'latency_ms', label: 'Latency', align: 'right', render: (row) => `${row.latency_ms || 0}ms` },
                    { key: 'status', label: 'Status', align: 'right' },
                ]}
                rows={nodes}
            />
        </ModuleShell>
    );
}

export function GhostModule() {
    const { apiKey } = useApiKey();
    const [seed, setSeed] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const generateSeed = async () => {
        setLoading(true);
        setError('');
        try {
            setSeed(await initiateGhostProtocol({ apiKey }));
        } catch (err) {
            setError(err.message || 'Ghost protocol failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <ModuleShell title="Ghost Protocol" eyebrow="Genesis seed generation and sovereign extraction" actions={<ActionButton onClick={generateSeed} disabled={!apiKey || loading}><Ghost className="h-3.5 w-3.5" />Generate Seed</ActionButton>}>
            <StatusLine loading={loading} error={error} />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard label="Protocol" value="OMEGA" trend="ready" icon={Ghost} />
                <StatCard label="Seed Status" value={seed ? 'READY' : 'WAITING'} trend="genesis" icon={Lock} tone="text-emerald-400" />
                <StatCard label="Mode" value="LOCAL" trend="non-custodial" icon={Shield} />
            </div>
            <pre className="min-h-[260px] overflow-auto border border-white/10 bg-[#0B0E14] p-5 text-[12px] text-white/80">
                {seed ? JSON.stringify(seed, null, 2) : 'Press Generate Seed to initiate the backend Ghost Protocol endpoint.'}
            </pre>
        </ModuleShell>
    );
}

export function SingularityModule() {
    const { apiKey, data, loading, error, refresh } = useModuleData(getMindStatus, []);
    const [result, setResult] = useState(null);

    const runAction = async (action) => {
        setResult(await action(apiKey));
        refresh();
    };

    return (
        <ModuleShell
            title="Singularity Core"
            eyebrow="Mind status, OODA loop, and final transition controls"
            actions={
                <>
                    <ActionButton tone="dark" onClick={() => runAction(triggerMindOoda)} disabled={!apiKey}><Play className="h-3.5 w-3.5" />OODA</ActionButton>
                    <ActionButton onClick={() => runAction(triggerBeyondHorizon)} disabled={!apiKey}><Zap className="h-3.5 w-3.5" />Beyond Horizon</ActionButton>
                    <ActionButton tone="red" onClick={() => runAction(initiateOmegaLock)} disabled={!apiKey}><Lock className="h-3.5 w-3.5" />Omega Lock</ActionButton>
                    <ActionButton tone="dark" onClick={() => runAction(executeRecursiveFeedback)} disabled={!apiKey}><RefreshCw className="h-3.5 w-3.5" />Feedback</ActionButton>
                </>
            }
        >
            <StatusLine loading={loading} error={error} />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <StatCard label="Consciousness" value={data?.consciousness || '—'} trend={data?.autonomy ? 'autonomous' : 'manual'} icon={Zap} tone="text-emerald-400" />
                <StatCard label="Subagents" value={String(data?.subagents?.length || 0)} trend={(data?.subagents || []).join(', ') || 'none'} icon={Server} />
                <StatCard label="Security" value={data?.loop_history?.telemetry?.security_posture || '—'} trend="posture" icon={Shield} tone="text-amber-400" />
            </div>
            {result && <pre className="overflow-auto border border-sky-500/30 bg-sky-500/10 p-4 text-[11px] text-sky-100">{JSON.stringify(result, null, 2)}</pre>}
            <pre className="min-h-[260px] overflow-auto border border-white/10 bg-[#0B0E14] p-5 text-[12px] text-white/80">{JSON.stringify(data || {}, null, 2)}</pre>
        </ModuleShell>
    );
}
