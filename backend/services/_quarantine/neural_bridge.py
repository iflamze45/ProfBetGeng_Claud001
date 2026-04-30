import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
from .execution_agent import sea_agent, ExecutionTask
from .vault_service import sovereign_vault

logger = logging.getLogger("pbg.neural_bridge")

class NeuralCommand(BaseModel):
    user_id: str
    platform: str # "telegram" | "discord"
    text: str
    context: Optional[Dict[str, Any]] = None

class NeuralResponse(BaseModel):
    text: str
    action_required: bool = False
    payload: Optional[Dict[str, Any]] = None

class NeuralBridge:
    """
    Handles natural language communication between Messaging Platforms 
    and the Sovereign Execution Agent (SEA).
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, str] = {}
        logger.info("NEURAL_BRIDGE_INITIALIZED: Ready for ubiquitous command distribution.")

    async def process_incoming(self, command: NeuralCommand) -> NeuralResponse:
        """
        Parses text commands like '/pnl', '/arbs', or '/exec [match_id]'
        """
        text = command.text.lower().strip()
        
        if text.startswith("/pnl"):
            return NeuralResponse(
                text="📊 PORTFOLIO_STATUS: Bankroll ₦1,240,500 | Alpha +2.4% | Sharpe 1.8. System at peak efficiency."
            )
            
        elif text.startswith("/arbs"):
            return NeuralResponse(
                text="⚡ CURRENT_ARBS: Found 2 windows. 1. Arsenal/Chelsea (3.2%). 2. Lakers/Nets (1.8%). Use /exec ARB_1 to lock."
            )
            
        elif text.startswith("/exec"):
            parts = text.split(" ")
            if len(parts) < 2:
                return NeuralResponse(text="BOT_ERR: Match ID required. Usage: /exec [match_id]")
            
            match_id = parts[1]
            
            # Simulated Execution Task
            task = ExecutionTask(
                match_id=match_id,
                selection="HOME",
                odds=1.95,
                stake=5000.0
            )
            
            try:
                # Trigger SEA (Sovereign Execution Agent)
                await sea_agent.execute_trade(task)
                return NeuralResponse(
                    text=f"✅ EXECUTION_SUCCESS: SEA has placed ₦5,000 on {match_id}. Credentials pulled from Sovereign Vault."
                )
            except Exception as e:
                return NeuralResponse(text=f"❌ EXECUTION_FAILED: {str(e)}")
            
        else:
            return NeuralResponse(
                text="PBG_BOT: Command not recognized. Available: /pnl, /arbs, /exec [ID]",
                action_required=False
            )

# Singleton
neural_bridge = NeuralBridge()
