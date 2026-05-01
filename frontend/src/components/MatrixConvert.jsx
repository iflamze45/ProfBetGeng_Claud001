import { useState, useEffect } from 'react';
import { RefreshCw, Database, Activity, ChevronRight, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';
import { useApiKey } from '../hooks/useApiKey';
import { convertTicket, analyseTicketStream, getHistory, getArbWindows } from '../api/pbgClient';

function parseSelectionsText(text) {
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map((line, i) => {
      const parts = line.split('|').map(p => p.trim())
      if (parts.length < 4) return null
      const odds = parseFloat(parts[3])
      if (isNaN(odds)) return null
      return {
        event_id: String(i + 1),
        event_name: parts[0],
        market: parts[1],
        pick: parts[2],
        odds,
      }
    })
    .filter(Boolean)
}

export default function MatrixConvert() {
    const { apiKey, loading: keyLoading, error: keyError } = useApiKey();
    const [source, setSource] = useState('SportyBet');
    const [target, setTarget] = useState('Bet9ja');
    const [rawText, setRawText] = useState('');
    const [stake, setStake] = useState('');
    const [status, setStatus] = useState('IDLE');
    const [result, setResult] = useState(null);
    const [errorMsg, setErrorMsg] = useState('');
    const [narrative, setNarrative] = useState('');
    const [narrativeStreaming, setNarrativeStreaming] = useState(false);
    const [arbWindows, setArbWindows] = useState([]);
    const [history, setHistory] = useState([]);

    const platforms = ['SportyBet', '1xBet', 'Bet9ja', 'MSport', 'BetKing'];

    useEffect(() => {
        if (!apiKey) return;
        getArbWindows({ apiKey })
            .then(d => setArbWindows(d.windows || []))
            .catch(() => {});
    }, [apiKey]);

    useEffect(() => {
        refreshHistory();
    }, [apiKey]);

    async function refreshHistory() {
        if (!apiKey) return;
        try {
            const d = await getHistory(apiKey);
            setHistory((d.records || []).slice(0, 5));
        } catch (_) {}
    }

    async function startNarrativeStream(converted) {
        setNarrative('');
        setNarrativeStreaming(true);
        try {
            for await (const chunk of analyseTicketStream({ apiKey, converted })) {
                setNarrative(prev => prev + chunk);
            }
        } catch (_) {
            // ignore — keep whatever streamed
        } finally {
            setNarrativeStreaming(false);
        }
    }

    const handleConvert = async () => {
        const selections = parseSelectionsText(rawText);
        if (!selections.length) {
            setErrorMsg('Enter at least one selection: Team A vs Team B | Market | Pick | Odds');
            setStatus('ERROR');
            return;
        }
        if (stake && (isNaN(parseFloat(stake)) || parseFloat(stake) <= 0)) {
            setErrorMsg('Stake must be a positive number');
            setStatus('ERROR');
            return;
        }
        setStatus('CONVERTING');
        setErrorMsg('');
        setResult(null);
        setNarrative('');
        try {
            const bookingCode = `WEB-${Date.now()}`;
            const converted = await convertTicket({
                apiKey,
                bookingCode,
                stake: stake ? parseFloat(stake) : null,
                selections,
                includeAnalysis: true,
            });
            if (!converted.success) throw new Error('Conversion failed');
            setResult(converted);
            setStatus('SUCCESS');
            refreshHistory();
            if (converted.converted) {
                startNarrativeStream(converted.converted);
            }
        } catch (err) {
            setErrorMsg(err.message || 'Unknown error');
            setStatus('ERROR');
        }
    };

    const riskColor = (level) => {
        if (!level) return 'text-[#738091]';
        const l = level.toUpperCase();
        if (l === 'LOW' || l === 'STABLE') return 'text-emerald-400';
        if (l === 'MEDIUM') return 'text-yellow-400';
        return 'text-red-400';
    };

    const sidebarWarnings = result?.converted?.warnings || [];
    const showArbWindows = sidebarWarnings.length === 0;

    return (
        <div className="flex flex-col h-full space-y-6 animate-in fade-in duration-500 font-sans overflow-x-hidden">
            <div className="flex items-end justify-between border-b border-white/5 pb-4">
                <div>
                    <h2 className="text-2xl font-semibold tracking-tight text-white m-0 p-0">Matrix Translation</h2>
                    <p className="text-[10px] text-[#738091] uppercase tracking-[0.05em] mt-1.5 flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${keyLoading ? 'bg-yellow-500' : keyError ? 'bg-red-500' : 'bg-emerald-500'}`}></span>
                        {keyLoading ? 'AUTHENTICATING...' : keyError ? 'AUTH ERROR' : 'Cross-Broker Liquidity Routing'}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 h-full min-h-0">
                {/* Control Panel */}
                <div className="col-span-2 flex flex-col space-y-4 overflow-y-auto pr-2 pb-2">
                    <div className="glass-hud p-6 rounded flex flex-col relative overflow-hidden">
                        <div className="flex items-center justify-between mb-6 border-b border-white/5 pb-3">
                            <h3 className="font-medium text-[11px] uppercase text-[#738091] tracking-wide">Translation Vector</h3>
                            <div className="flex items-center gap-2 text-[10px] font-data text-emerald-400">
                                <Activity className="w-3 h-3" />
                                <span>ROUTING ACTIVE</span>
                            </div>
                        </div>

                        <div className="flex items-center gap-4 mb-6">
                            <div className="flex-1">
                                <label className="block text-[10px] uppercase text-[#738091] mb-2 font-medium tracking-wide">Origin Broker</label>
                                <div className="relative">
                                    <select
                                        className="w-full bg-[#151A22] border border-white/10 text-white text-[13px] font-medium rounded py-2.5 px-3 hover:border-white/20 transition-colors focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/20 appearance-none cursor-pointer"
                                        value={source}
                                        onChange={(e) => setSource(e.target.value)}
                                    >
                                        {platforms.map(p => <option key={p} value={p}>{p}</option>)}
                                    </select>
                                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-[#738091]">
                                        <ChevronRight className="w-4 h-4 rotate-90" />
                                    </div>
                                </div>
                            </div>
                            <div className="mt-6 flex items-center justify-center text-[#738091]">
                                <ArrowRight className="w-5 h-5 opacity-50" />
                            </div>
                            <div className="flex-1">
                                <label className="block text-[10px] uppercase text-[#738091] mb-2 font-medium tracking-wide">Destination Broker</label>
                                <div className="relative">
                                    <select
                                        className="w-full bg-[#151A22] border border-white/10 text-white text-[13px] font-medium rounded py-2.5 px-3 hover:border-white/20 transition-colors focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/20 appearance-none cursor-pointer"
                                        value={target}
                                        onChange={(e) => setTarget(e.target.value)}
                                    >
                                        {platforms.map(p => <option key={p} value={p}>{p}</option>)}
                                    </select>
                                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-[#738091]">
                                        <ChevronRight className="w-4 h-4 rotate-90" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="mb-4">
                            <label className="block text-[10px] uppercase text-[#738091] mb-2 font-medium tracking-wide">Selections (one per line)</label>
                            <textarea
                                rows={5}
                                className="w-full bg-[#0B0E14] border border-white/10 text-white font-data text-[13px] rounded py-3 px-4 placeholder-[#3A4350] transition-colors focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/20 resize-none"
                                placeholder={"Arsenal vs Chelsea | 1X2 | Home | 2.10\nMan City vs Liverpool | BTTS | Yes | 1.80"}
                                value={rawText}
                                onChange={(e) => setRawText(e.target.value)}
                            />
                        </div>

                        <div className="mb-6">
                            <label className="block text-[10px] uppercase text-[#738091] mb-2 font-medium tracking-wide">Stake (Optional)</label>
                            <input
                                type="number"
                                className="w-full bg-[#0B0E14] border border-white/10 text-white font-data text-[14px] rounded py-3 px-4 placeholder-[#3A4350] transition-colors focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/20"
                                placeholder="e.g. 5000"
                                value={stake}
                                onChange={(e) => setStake(e.target.value)}
                            />
                        </div>

                        <button
                            onClick={handleConvert}
                            disabled={!rawText.trim() || status === 'CONVERTING' || keyLoading || !!keyError}
                            className="w-full bg-white hover:bg-zinc-200 text-[#0B0E14] font-semibold uppercase text-[11px] tracking-wide py-3.5 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {status === 'CONVERTING' ? <RefreshCw className="w-4 h-4 animate-spin text-[#0B0E14]" /> : 'Execute Bridge Translation'}
                        </button>
                    </div>

                    {/* Result Panel */}
                    <div className={`glass-hud p-6 rounded flex flex-col relative overflow-hidden transition-all duration-300 min-h-[220px] ${status === 'SUCCESS' ? 'border-emerald-500/30' : status === 'ERROR' ? 'border-red-500/30' : ''}`}>
                        <div className="flex items-center justify-between mb-6 border-b border-white/5 pb-3">
                            <h3 className="font-medium text-[11px] uppercase text-[#738091] tracking-wide">Output Vector</h3>
                        </div>

                        {status === 'IDLE' && (
                            <div className="flex-1 flex flex-col items-center justify-center text-[#738091]">
                                <Database className="w-8 h-8 mb-4 opacity-20" />
                                <p className="text-[11px] font-medium tracking-wide">AWAITING TICKET INPUT</p>
                            </div>
                        )}

                        {status === 'CONVERTING' && (
                            <div className="flex-1 flex flex-col items-center justify-center">
                                <RefreshCw className="w-8 h-8 mb-4 animate-spin text-sky-400" />
                                <p className="text-[11px] font-medium tracking-wide text-sky-400 animate-pulse">BRIDGING LIQUIDITY POOLS...</p>
                            </div>
                        )}

                        {status === 'ERROR' && (
                            <div className="flex-1 flex flex-col items-center justify-center">
                                <AlertTriangle className="w-8 h-8 mb-4 text-red-500" />
                                <p className="text-[12px] font-semibold text-red-400 tracking-tight">TRANSLATION FAILED</p>
                                <p className="text-[11px] text-[#738091] mt-2 font-medium">{errorMsg || 'Invalid or malformed ticket.'}</p>
                            </div>
                        )}

                        {status === 'SUCCESS' && result && (
                            <div className="flex-1 flex flex-col animate-in fade-in duration-300 gap-4">
                                <div className="bg-[#0B0E14] border border-emerald-500/20 p-5 rounded flex flex-col items-center justify-center">
                                    <p className="text-[10px] uppercase text-[#738091] font-medium tracking-wide mb-2 flex items-center gap-1.5">
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                                        Conversion Complete
                                    </p>
                                    <p className="text-[13px] font-data text-emerald-400 tracking-tight text-center">
                                        {result.converted?.converted_count} legs converted · {result.converted?.skipped_count} skipped
                                    </p>
                                </div>
                                <div className="grid grid-cols-3 gap-3">
                                    <div className="bg-[#151A22] border border-white/5 rounded p-4 text-center">
                                        <p className="text-[10px] uppercase text-[#738091] tracking-wide font-medium mb-1.5">Total Odds</p>
                                        <p className="text-[14px] font-data text-white">{result.converted?.total_odds?.toFixed(2) ?? '—'}</p>
                                    </div>
                                    <div className="bg-[#151A22] border border-white/5 rounded p-4 text-center">
                                        <p className="text-[10px] uppercase text-[#738091] tracking-wide font-medium mb-1.5">Risk Score</p>
                                        <p className={`text-[14px] font-data ${riskColor(result.analysis?.pulse?.level)}`}>
                                            {result.analysis?.pulse?.score ?? '—'}
                                        </p>
                                    </div>
                                    <div className="bg-[#151A22] border border-white/5 rounded p-4 text-center">
                                        <p className="text-[10px] uppercase text-[#738091] tracking-wide font-medium mb-1.5">Risk Level</p>
                                        <p className={`text-[11px] font-data font-semibold tracking-wide ${riskColor(result.analysis?.pulse?.level)}`}>
                                            {result.analysis?.pulse?.level ?? '—'}
                                        </p>
                                    </div>
                                </div>

                                {result.converted?.selections?.length > 0 && (
                                    <div className="bg-[#0B0E14] border border-white/5 rounded overflow-hidden">
                                        <div className="px-4 py-2 border-b border-white/5 bg-[#151A22]">
                                            <p className="text-[10px] uppercase text-[#738091] font-medium tracking-wide">
                                                Bet9ja Selections ({result.converted.selections.length})
                                            </p>
                                        </div>
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="border-b border-white/5">
                                                    <th className="px-4 py-2 text-[10px] uppercase text-[#738091] font-medium">Match</th>
                                                    <th className="px-4 py-2 text-[10px] uppercase text-[#738091] font-medium">Market</th>
                                                    <th className="px-4 py-2 text-[10px] uppercase text-[#738091] font-medium">Pick</th>
                                                    <th className="px-4 py-2 text-[10px] uppercase text-[#738091] font-medium text-right">Odds</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/5">
                                                {result.converted.selections.map((sel, i) => (
                                                    <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                                                        <td className="px-4 py-2.5 text-[12px] text-white/80">{sel.event_name}</td>
                                                        <td className="px-4 py-2.5 text-[11px] text-[#738091]">{sel.market}</td>
                                                        <td className="px-4 py-2.5 text-[11px] text-sky-400 font-medium">{sel.pick}</td>
                                                        <td className="px-4 py-2.5 text-[12px] font-data text-emerald-400 text-right">{sel.odds.toFixed(2)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                        {result.converted.warnings?.length > 0 && (
                                            <div className="px-4 py-2 border-t border-white/5 bg-[#0B0E14]">
                                                {result.converted.warnings.map((w, i) => (
                                                    <p key={i} className="text-[10px] text-yellow-400 font-medium">{w.message}</p>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {(narrative || narrativeStreaming) && (
                                    <div className="bg-[#0B0E14] border border-white/5 rounded p-4">
                                        <div className="flex items-center gap-2 mb-2">
                                            <p className="text-[10px] uppercase text-[#738091] font-medium tracking-wide">AI Risk Narrative</p>
                                            {narrativeStreaming && <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />}
                                        </div>
                                        <p className="text-[12px] text-white/70 leading-relaxed whitespace-pre-wrap">
                                            {narrative || '...'}
                                        </p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Recent Conversions */}
                    {history.length > 0 && (
                        <div className="glass-hud p-4 rounded">
                            <h3 className="text-[10px] uppercase text-[#738091] font-medium tracking-wide mb-3">Recent Conversions</h3>
                            <div className="space-y-2">
                                {history.map((rec, i) => (
                                    <div key={i} className="flex justify-between items-center text-[11px]">
                                        <span className="text-white/60 font-data">{rec.source_booking_code}</span>
                                        <span className="text-[#738091]">{rec.selections_count} legs</span>
                                        <span className={`font-medium ${rec.risk_level === 'STABLE' || rec.risk_level === 'LOW' ? 'text-emerald-400' : rec.risk_level === 'CRITICAL' ? 'text-red-400' : 'text-yellow-400'}`}>
                                            {rec.risk_level || '—'}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Market Anomalies Sidebar */}
                <div className="glass-hud rounded overflow-hidden flex flex-col min-h-0 max-h-[280px] md:max-h-none">
                    <div className="px-5 py-4 border-b border-white/5 bg-[#151A22] flex justify-between items-center shrink-0">
                        <h3 className="text-[11px] font-medium text-white tracking-wide uppercase">Detected Inefficiencies</h3>
                        <span className="text-[9px] text-[#738091] border border-white/10 rounded px-1.5 py-0.5 uppercase tracking-wide">Preview</span>
                    </div>

                    <div className="flex-1 overflow-y-auto w-full">
                        {sidebarWarnings.length > 0 ? (
                            <table className="w-full text-left border-collapse">
                                <tbody className="divide-y divide-white/5">
                                    {sidebarWarnings.map((w, i) => (
                                        <tr key={i} className="hover:bg-white/[0.02] cursor-pointer transition-colors">
                                            <td className="px-5 py-3">
                                                <div className="text-[11px] text-yellow-400 font-medium">{w.code}</div>
                                                <div className="text-[11px] text-[#738091] mt-0.5">{w.message}</div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : showArbWindows && arbWindows.length > 0 ? (
                            <table className="w-full text-left border-collapse">
                                <tbody className="divide-y divide-white/5">
                                    {arbWindows.map((arb, i) => (
                                        <tr key={i} className="hover:bg-white/[0.02] cursor-pointer transition-colors">
                                            <td className="px-5 py-3">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-[10px] text-[#738091] font-medium uppercase tracking-wide">{arb.match_id}</span>
                                                </div>
                                                <div className="text-[11px] text-[#738091]">{arb.teams}</div>
                                            </td>
                                            <td className="px-5 py-3 text-right text-[11px] font-data font-medium text-emerald-400">
                                                +{(arb.profit_margin * 100).toFixed(1)}%
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="px-5 py-4 text-[11px] text-[#738091]">No anomalies detected.</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
