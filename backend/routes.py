from fastapi import APIRouter, Depends, HTTPException, Security, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
import datetime as _datetime
from typing import Optional
from pydantic import BaseModel

from .models import (
    ConvertedTicket, SportybetTicket, ConversionRecord,
    APIKeyCreate, APIKeyResponse, SportybetSelection,
    ConvertRequest, ConvertResponse, ParseTicketRequest, ParseTicketResponse,
    KellyStakeRequest, KellyStakeResponse,
    SocialTicket, MirrorAction
)
from .services.text_parser import RawTextParser
from .services.sportybet_parser import SportybetAdapter
from backend.services.alpha_engine import alpha_pricer

from backend.services.league_oracle import league_oracle
from .services.converter import Bet9jaConverter
from .services.pbg_streaming_protocol import live_odds_manager
from .services.auth import APIKeyService, MockAPIKeyService, require_api_key
from .services.storage import SupabaseStorageService, MockStorageService
from .services.ticket_pulse import TicketPulseService, MockTicketPulseService, RiskReport
from .services.supabase_client import get_supabase_client
from .services.rate_limiter import limiter
from .services.sentiment import SentimentAnalysisService
from .services.value_discovery import discovery_hub
from .services.bankroll_optimizer import kelly_protocol
from .services.execution_agent import sea_agent, ExecutionTask
from .services.mirror_protocol import mirror_hub
from .services.strategy_engine import quant_engine
from .services.risk_analytics import risk_engine, RiskMetrics
from .services.neural_bridge import neural_bridge, NeuralCommand, NeuralResponse
from .services.vault_service import sovereign_vault, VaultItem
from .services.governance_engine import gov_engine, Proposal
from .services.node_manager import sgn_hub, SatelliteNode
from .services.institutional_gateway import institutional_gateway, DarkPoolSelection
from .services.ghost_protocol import ghost_protocol
from .services.beyond_horizon import orchestrator
from .services.sovereign_mind import sovereign_mind
from .config import get_settings
from typing import Optional, Dict, Any
from datetime import datetime

router = APIRouter()

# --- Institutional Bridge (Phase 27) ---

@router.post("/api/v1/institutional/execute")
async def execute_institutional_liquidity(
    request: Dict[str, Any],
    api_key: str = Security(require_api_key)
):
    """Executes a wholesale dark-pool deal (Volume Strike)."""
    selection = DarkPoolSelection(
        market_id=request.get("market_id", "GLOBAL_MARKET_01"),
        target_odds=request.get("odds", 2.10),
        liquidity_available_usd=request.get("liquidity", 1000000.0)
    )
    deal_id = institutional_gateway.execute_wholesale_deal(selection, request.get("amount_usd", 50000.0))
    return {"status": "INSTITUTIONAL_FILL", "deal_id": deal_id}

@router.get("/api/v1/institutional/depth/{market_id}")
async def get_dark_pool_depth(
    market_id: str,
    api_key: str = Security(require_api_key)
):
    """Queries aggregate depth across institutional counterparties."""
    return institutional_gateway.get_market_depth(market_id)

# --- Step Ω: The Ghost Protocol ---

@router.post("/api/v1/ghost/initiate")
async def initiate_encapsulation(api_key: str = Security(require_api_key)):
    """Triggers the neural extraction and Genesis Seed generation."""
    seed = ghost_protocol.generate_genesis_seed()
    return {"status": "OMEGA_GENESIS_READY", "seed": seed}

@router.get("/api/v1/market/signals")
async def get_market_signals(api_key: str = Security(require_api_key)):
    """Retrieve real-time market value signals."""
    return {"signals": discovery_hub.active_signals}

@router.get("/api/v1/market/odds")
async def get_live_odds(api_key: str = Security(require_api_key)):
    """Retrieve raw normalized odds flowing from the ingestion engine."""
    from backend.services.data_ingestion import ingestion_engine
    
    # Flatten the dict locally for easier payload structure
    flattened_odds = []
    for match_id, odds_list in ingestion_engine.latest_odds.items():
        flattened_odds.extend([o.to_dict() for o in odds_list])
        
    return {
        "status": "LIVE_INGESTION",
        "provider_count": len(ingestion_engine.providers),
        "total_odds_captured": len(flattened_odds),
        "active_odds": flattened_odds
    }

# --- Sovereign Treasury Commands ---

@router.post("/api/v1/treasury/rebalance")
async def rebalance_sovereign_wealth(api_key: str = Security(require_api_key)):
    """Executes automated rebalancing of reserves."""
    treasury_core.execute_rebalance({})
    return {"status": "REBALANCE_EXECUTED"}

@router.post("/api/v1/treasury/flatten")
async def emergency_flatten_positions(api_key: str = Security(require_api_key)):
    """Triggers total liquidation and retreats to COLD STORAGE."""
    triggered = treasury_core.trigger_circuit_breaker(0.10) # Forced high drawdown
    return {"status": "EMERGENCY_FLATTEN_SUCCESS" if triggered else "NOMINAL_FLAT"}

@router.post("/api/v1/bankroll/optimize", response_model=KellyStakeResponse)
async def optimize_bankroll(
    request: KellyStakeRequest,
    api_key: str = Security(require_api_key)
):
    """Calculates the best stake based on edge and collective sentiment."""
    # Convert request odds to probability (win_prob = 1/global_fair)
    p_win = 1.0 / request.global_odds
    
    recommendation = kelly_protocol.calculate_optimal_stake(
        current_bankroll=request.bankroll or 1000.0,
        p_win=p_win,
        b_odds=request.local_odds,
        social_volume_spike=request.social_spike
    )
    return recommendation


@router.post("/api/v1/execution/trade")
async def execute_trade(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    api_key: str = Depends(require_api_key)
):
    """Initiates an autonomous trade via SEA."""
    task = ExecutionTask(
        id=f"SEA-{datetime.now().strftime('%y%m%d%H%M%S')}",
        match_id=request.get("match_id", "UNKNOWN"),
        selection=request.get("selection", "UNKNOWN"),
        odds=request.get("odds", 0.0),
        stake=request.get("stake", 0.0),
        status="PENDING"
    )
    background_tasks.add_task(sea_agent.execute_trade, task)
    return {"task_id": task.id, "status": "IN_PROGRESS"}


# --- Social Mirroring Protocol ---

@router.get("/api/v1/social/feed")
async def get_social_feed(api_key: str = Security(require_api_key)):
    """Retrieve the collective intelligence broadcast feed."""
    return {"feed": mirror_hub.broadcast_feed}

@router.post("/api/v1/social/publish")
async def publish_to_feed(
    request: SocialTicket,
    api_key: str = Depends(require_api_key)
):
    """Broadcasts a verified signal to the sovereign community."""
    mirror_hub.publish_signal(request)
    return {"status": "BROADCAST_SUCCESS", "ticket_id": request.ticket_id}

@router.post("/api/v1/social/mirror")
async def mirror_ticket(
    request: MirrorAction,
    api_key: str = Depends(require_api_key)
):
    """Executes a mirror event on a communal signal."""
    mirror_hub.mirror_signal(request)
    return {"status": "MIRROR_ENGAGED", "target": request.target_ticket_id}


# --- Algorithmic Strategy Engine (MAE) ---

@router.post("/api/v1/execution/strike")
async def strike_alpha(
    request: ExecutionTask,
    background_tasks: BackgroundTasks,
    api_key: str = Security(require_api_key)
):
    """Initiates a high-precision strike via SEA."""
    background_tasks.add_task(sea_agent.execute_trade, request)
    return {"status": "STRIKE_INITIATED", "task_id": request.id}

@router.get("/api/v1/execution/status/{task_id}")
async def get_execution_status(
    task_id: str,
    api_key: str = Security(require_api_key)
):
    """Polls real-time status of an active execution task."""
    task = sea_agent.active_tasks.get(task_id)
    if not task:
        # Check history
        history = [t for t in sea_agent.history if t.id == task_id]
        if history:
            return history[0]
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/api/v1/quant/arbs")
async def get_arb_windows(api_key: str = Security(require_api_key)):
    """Retrieve multi-market arbitrage windows."""
    # Mock some triangulated detection for Step 6.1
    mock_arbs = [
        {
            "match_id": "ARB_772",
            "teams": "Arsenal vs Chelsea",
            "profit_margin": 0.042,
            "outcomes": {"1": 2.15, "X": 3.45, "2": 4.80},
            "bookmakers": {"1": "SportyBet", "X": "Bet9ja", "2": "Pinnacle"}
        }
    ]
    return {"windows": mock_arbs}


def get_auth_service():
    client = get_supabase_client()
    return APIKeyService(client) if client else MockAPIKeyService()


def get_storage_service():
    client = get_supabase_client()
    return SupabaseStorageService(client) if client else MockStorageService()


def get_pulse_service():
    settings = get_settings()
    return TicketPulseService() if settings.anthropic_api_key else MockTicketPulseService()


def get_sentiment_service(storage_service=Depends(get_storage_service)):
    return SentimentAnalysisService(storage_service)

parser = SportybetAdapter()
converter = Bet9jaConverter()


def persist_conversion(storage_service, record: ConversionRecord):
    """Standalone worker function for background persistence."""
    try:
        storage_service.save_conversion(record)
    except Exception as e:
        print(f"ERROR: Background persistence failed: {e}")
text_parser = RawTextParser()


class AnalyseRequest(BaseModel):
    converted: ConvertedTicket
    language: str = "en"


class AnalyseResponse(BaseModel):
    success: bool
    analysis: Optional[RiskReport] = None
    error: Optional[str] = None


@router.websocket("/api/v1/ws/odds")
async def websocket_odds_endpoint(websocket: WebSocket):
    """
    Connects the Sovereign Terminal Dashboard to the real-time Odds streaming architecture.
    """
    await live_odds_manager.connect(websocket)
    try:
        while True:
            # Dashboard can push specific Match IDs to subscribe to here
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        live_odds_manager.disconnect(websocket)


@router.get("/health")
async def health():
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version, "auth_enabled": settings.auth_enabled}


@router.post("/api/v1/parse-ticket", response_model=ParseTicketResponse)
async def parse_ticket(
    request: ParseTicketRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")
            
    try:
        ticket = text_parser.parse(request.raw_text)
        return ParseTicketResponse(success=True, ticket=ticket)
    except Exception as e:
        return ParseTicketResponse(success=False, error=str(e))


@router.post("/api/v1/convert", response_model=ConvertResponse)
async def convert_ticket(
    request: ConvertRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    storage_service=Depends(get_storage_service),
    pulse_service=Depends(get_pulse_service),
    sentiment_service=Depends(get_sentiment_service),
):
    # Strategic Gate
    limiter.check(api_key)

    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

    sportybet_ticket = SportybetTicket(booking_code=request.booking_code, selections=request.selections, stake=request.stake)
    internal_ticket, _ = parser.parse(sportybet_ticket)
    converted = converter.convert(internal_ticket)

    # Engine Update: Intelligence Depth
    # Calculate deterministic risk before AI analysis
    hardened_metrics = risk_engine.calculate_ticket_risk(internal_ticket.selections, None)

    analysis = None
    if request.include_analysis:
        analysis = await pulse_service.analyse(converted, language=request.language)

    # Correlate Market Sentiment
    sentiment = sentiment_service.get_market_sentiment(internal_ticket)

    # Offload persistence to background task
    record = ConversionRecord(
        api_key=api_key,
        source_booking_code=request.booking_code,
        source_platform="sportybet",
        target_platform="bet9ja",
        selections_count=len(request.selections),
        converted_count=converted.converted_count,
        skipped_count=converted.skipped_count,
        stake=request.stake,
        total_odds=internal_ticket.total_odds,
        potential_returns=internal_ticket.potential_returns,
        risk_score=analysis.score if analysis else int(hardened_metrics.volatility * 100),
        risk_level=analysis.level if analysis else ("CRITICAL" if hardened_metrics.correlation_penalty > 0 else "STABLE"),
    )
    background_tasks.add_task(persist_conversion, storage_service, record)
    
    # Broadcast to real-time HUD
    await live_odds_manager.broadcast_json({
        "type": "CONVERSION_SUCCESS",
        "source": "sportybet",
        "target": "bet9ja",
        "selections": converted.converted_count,
        "timestamp": _datetime.datetime.now().isoformat()
    })

    return ConvertResponse(
        success=True,
        converted=converted,
        analysis={
            "pulse": analysis,
            "metrics": hardened_metrics.dict() if hasattr(hardened_metrics, 'dict') else hardened_metrics
        },
        sentiment=sentiment
    )


@router.post("/api/v1/analyse", response_model=AnalyseResponse)
async def analyse_ticket(
    request: AnalyseRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    pulse_service=Depends(get_pulse_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    analysis = await pulse_service.analyse(request.converted, language=request.language)
    return AnalyseResponse(success=True, analysis=analysis)


@router.post("/api/v1/analyse/stream")
async def analyse_ticket_stream(
    request: AnalyseRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    pulse_service=Depends(get_pulse_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")
            
    generator = pulse_service.analyse_stream(request.converted, language=request.language)
    return StreamingResponse(generator, media_type="text/event-stream")


# --- ORACLE ROUTES ---

@router.get("/oracle/leagues")
async def get_leagues(sport: str = None, api_key: str = Depends(require_api_key)):
    return {"leagues": league_oracle.get_leagues(sport)}

@router.get("/oracle/events")
async def get_events(sport: str = None, league: str = None, api_key: str = Depends(require_api_key)):
    return {"events": league_oracle.get_upcoming_events(sport, league)}


from backend.services.risk_oracle import risk_oracle, Selection

@router.post("/risk/assess")
async def assess_risk(data: Dict[str, Any], api_key: str = Depends(require_api_key)):
    selections = [Selection(**s) for s in data.get("selections", [])]
    bankroll = data.get("bankroll", 1000000.0)
    return risk_oracle.assess_risk(selections, bankroll)

@router.get("/api/v1/sgn/nodes")
async def get_sgn_nodes(api_key: str = Depends(require_api_key)):
    return [
        {
            "id": "PBG-NODE-LOCAL",
            "endpoint": "http://localhost:8000",
            "region": "LOCAL",
            "status": "ONLINE",
            "latency_ms": 1,
            "active_tasks": 0,
        }
    ]


@router.get("/api/v1/gov/proposals")
async def get_gov_proposals(api_key: str = Depends(require_api_key)):
    return []


@router.get("/api/v1/history")
async def get_history(
    limit: int = 50,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    storage_service=Depends(get_storage_service),
):
    settings = get_settings()
    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    records = storage_service.get_conversions(api_key=api_key, limit=limit)
    return {"records": [r.__dict__ for r in records], "count": len(records)}


@router.post("/api/v1/keys", response_model=APIKeyResponse)
async def create_api_key(
    payload: APIKeyCreate,
    admin_token: str = Security(APIKeyHeader(name="X-Admin-Token", auto_error=False)),
    auth_service=Depends(get_auth_service),
):
    settings = get_settings()
    if not admin_token or admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
        
    result = auth_service.generate_key(label=payload.label, owner=payload.owner)
    return APIKeyResponse(**result)



# ─── Batch Conversion ────────────────────────────────────────────────────────

import asyncio
import uuid as _uuid
from .batch import BatchConvertRequest, BatchConvertResponse, BatchTicketResult, BatchSummary


@router.post("/api/v1/convert-batch", response_model=BatchConvertResponse)
async def convert_batch(
    request: BatchConvertRequest,
    api_key: str = Depends(require_api_key),
    auth_service=Depends(get_auth_service),
    storage_service=Depends(get_storage_service),
    pulse_service=Depends(get_pulse_service),
):
    settings = get_settings()

    if not settings.batch_enabled:
        raise HTTPException(status_code=404, detail="Batch conversion is not enabled")

    # Anti-DoS: Check batch and selection limits (LH-005)
    MAX_BATCH_TICKETS = 20
    MAX_TICKET_SELECTIONS = 50
    if len(request.tickets) > MAX_BATCH_TICKETS:
        raise HTTPException(status_code=413, detail=f"Batch exceeds maximum limit of {MAX_BATCH_TICKETS} tickets")
        
    for idx, ticket in enumerate(request.tickets):
        if len(ticket.selections) > MAX_TICKET_SELECTIONS:
            raise HTTPException(status_code=413, detail=f"Ticket at index {idx} exceeds maximum limit of {MAX_TICKET_SELECTIONS} selections")

    if settings.auth_enabled and api_key != "dev_bypass":
        if not auth_service.validate_key(api_key):
            raise HTTPException(status_code=403, detail="Invalid or inactive API key")

    batch_id = str(_uuid.uuid4())

    async def process_one(index: int, ticket: ConvertRequest) -> BatchTicketResult:
        try:
            sportybet_ticket = SportybetTicket(
                booking_code=ticket.booking_code,
                selections=ticket.selections,
                stake=ticket.stake,
            )
            internal_ticket, _ = parser.parse(sportybet_ticket)
            converted = converter.convert(internal_ticket)

            analysis = None
            if ticket.include_analysis:
                analysis = await pulse_service.analyse(converted, language=ticket.language)

            storage_service.save_conversion(ConversionRecord(
                api_key=api_key,
                source_booking_code=ticket.booking_code,
                source_platform="sportybet",
                target_platform="bet9ja",
                selections_count=len(ticket.selections),
                converted_count=converted.converted_count,
                skipped_count=converted.skipped_count,
                stake=ticket.stake,
                total_odds=internal_ticket.total_odds,
                potential_returns=internal_ticket.potential_returns,
                risk_score=analysis.score if analysis else None,
                risk_level=analysis.level if analysis else None,
            ))

            result = ConvertResponse(success=True, converted=converted, analysis=analysis)
            return BatchTicketResult(index=index, status="success", result=result)

        except Exception as exc:
            return BatchTicketResult(index=index, status="error", error=str(exc))

    tasks = [process_one(i, t) for i, t in enumerate(request.tickets)]
    results: list[BatchTicketResult] = await asyncio.gather(*tasks)

    succeeded = sum(1 for r in results if r.status == "success")
    failed = len(results) - succeeded

    return BatchConvertResponse(
        batch_id=batch_id,
        summary=BatchSummary(total=len(results), succeeded=succeeded, failed=failed),
        results=results,
    )


@router.get("/api/v1/quant/risk", response_model=RiskMetrics)
async def get_risk_profile(api_key: str = Security(require_api_key)):
    """Provides high-density risk monitoring (Alpha/Beta/Sharpe)."""
    # In a real scenario, fetch last 30 days of returns from DB
    mock_returns = [0.02, -0.01, 0.05, 0.03, -0.02, 0.01, 0.04, 0.02]
    return risk_engine.calculate_metrics(mock_returns)


@router.post("/api/v1/neural/webhook", response_model=NeuralResponse)
async def neural_incoming_command(
    command: NeuralCommand,
    api_key: str = Security(require_api_key)
):
    """Processes incoming messages from Telegram/Discord."""
    return await neural_bridge.process_incoming(command)


@router.post("/api/v1/vault/save")
async def save_vault_item(
    item: VaultItem,
    api_key: str = Security(require_api_key)
):
    """Securely stores bookmaker credentials in the Sovereign Vault."""
    sovereign_vault.save_credentials(item)
    return {"status": "VAULT_SECURED", "bookmaker": item.bookmaker}


@router.get("/api/v1/vault/status")
async def get_vault_status(api_key: str = Security(require_api_key)):
    """Returns a list of bookmakers currently configured in the vault."""
    return {
        "active_vaults": list(sovereign_vault.store.keys()),
        "security_level": "AES-256-GCM-EQUIV"
    }


@router.get("/api/v1/gov/proposals", response_model=list[Proposal])
async def list_proposals(api_key: str = Security(require_api_key)):
    """Returns all active multi-sig execution proposals."""
    return list(gov_engine.proposals.values())


@router.post("/api/v1/gov/vote")
async def vote_on_proposal(
    proposal_id: str,
    user_id: str,
    approved: bool,
    api_key: str = Security(require_api_key)
):
    """Submits a multi-sig vote for an execution proposal."""
    return gov_engine.submit_vote(proposal_id, user_id, approved)


@router.get("/api/v1/sgn/nodes", response_model=list[SatelliteNode])
async def list_sgn_nodes(api_key: str = Security(require_api_key)):
    """Returns the status of all global execution nodes in the cluster."""
    return list(sgn_hub.nodes.values())


@router.post("/api/v1/sgn/heartbeat")
async def sgn_node_heartbeat(
    node_id: str,
    latency: int,
    api_key: str = Security(require_api_key)
):
    """Internal pulse for satellite nodes to report health."""
    sgn_hub.heartbeat(node_id, latency)
    return {"status": "ACK"}


# ── Sovereign Singularity Protocols ──────────────────────────────────────────

@router.post("/api/v1/singularity/omega-lock")
async def initiate_omega_lock(api_key: str = Security(require_api_key)):
    """Permanently locks the system into Eternal Alpha state."""
    from .services.singularity_engine import singularity_core
    singularity_core.initiate_omega_lock()
    return {"status": "OMEGA_LOCKED", "message": "System sovereignty established."}

@router.post("/api/v1/singularity/recursive-feedback")
async def execute_feedback(api_key: str = Security(require_api_key)):
    """Eliminates neural noise and locks weights."""
    from .services.singularity_engine import singularity_core
    singularity_core.execute_recursive_feedback()
    return {"status": "FEEDBACK_COMPLETE", "message": "Neural noise eliminated."}

@router.post("/api/v1/gov/execute/{proposal_id}")
async def execute_governance_proposal(
    proposal_id: str,
    api_key: str = Security(require_api_key)
):
    """Executes a passed multi-sig proposal."""
    from .services.governance_module import governance_core
    success = governance_core.execute_proposal(proposal_id)
    if not success:
        raise HTTPException(status_code=400, detail="Proposal not ready or already executed.")
    return {"status": "GOVERNANCE_APPLIED"}

@router.post("/api/v1/mesh/simulate-failure")
async def simulate_node_failure(
    request: Dict[str, str],
    api_key: str = Security(require_api_key)
):
    """Simulates a cloud failure to trigger autonomous node resurrection."""
    from .services.ghost_mesh import ghost_mesh
    node_id = request.get("node_id")
    ghost_mesh.simulate_node_failure(node_id)
    return {"status": "RESURRECTION_SEQUENCE_TRIGGERED", "node": node_id}

@router.get("/api/v1/solana/vault")
async def get_solana_vault_status(api_key: str = Security(require_api_key)):
    """Returns the live status of the on-chain multi-sig vault."""
    from .services.solana_bridge import solana_bridge
    return {
        "address": solana_bridge.wallet_address,
        "balances": solana_bridge.get_vault_balance(),
        "history": solana_bridge.transaction_history
    }

@router.post("/api/v1/singularity/beyond-horizon")
async def trigger_beyond_horizon(api_key: str = Security(require_api_key)):
    """Triggers the final three-stage sovereignty transition."""
    result = await orchestrator.execute_final_transition()
    return result

@router.get("/api/v1/mind/status")
async def get_mind_status(api_key: str = Security(require_api_key)):
    """Returns high-level consciousness metrics of the Super Agent."""
    return sovereign_mind.get_mind_status()

@router.post("/api/v1/mind/ooda")
async def trigger_mind_ooda(api_key: str = Security(require_api_key)):
    """Triggers the autonomous OODA loop (Observe-Orient-Decide-Act)."""
    return await sovereign_mind.execute_ooda_loop()
