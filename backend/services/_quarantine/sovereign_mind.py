import logging
import asyncio
import json
import os
from typing import Dict, Any, List
from backend.services.singularity_engine import singularity_core
from backend.services.ghost_protocol import ghost_protocol

logger = logging.getLogger("pbg.sovereign_mind")

class SovereignMind:
    """
    High-Level 'Super Agent' for Repository & System Sovereignty.
    Orchestrates autonomous maintenance, evolution, and state continuity.
    """
    def __init__(self):
        self.mind_state_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../mind_state.json"))
        self.consciousness_level = 0.99
        self.is_autonomous = True
        self.active_subagents = ["architect", "security", "maintainer"]
        self._load_mind_state()

    def _load_mind_state(self):
        if os.path.exists(self.mind_state_file):
            try:
                with open(self.mind_state_file, "r") as f:
                    self.state = json.load(f)
                logger.info("SOVEREIGN_MIND: Consciousness restored.")
            except Exception as e:
                logger.error(f"MIND_RESTORE_ERROR: {e}")
                self.state = {"metrics": {}, "last_ooda_loop": None}
        else:
            self.state = {"metrics": {}, "last_ooda_loop": None}

    def _save_mind_state(self):
        try:
            with open(self.mind_state_file, "w") as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            logger.error(f"MIND_SAVE_ERROR: {e}")

    async def execute_ooda_loop(self):
        """
        Observes the system, Orients based on goals, Decides on actions, and Acts.
        This is the core loop of the Super Agent.
        """
        logger.info("OODA_LOOP: Initiating loop sequence...")
        
        # 1. OBSERVE: Gather system telemetry
        telemetry = self._observe_system()
        
        # 2. ORIENT: Compare with Singularity goals
        plan = self._orient_to_goals(telemetry)
        
        # 3. DECIDE: Select highest priority actions
        actions = self._decide_actions(plan)
        
        # 4. ACT: Execute actions autonomously
        results = await self._act(actions)
        
        self.state["last_ooda_loop"] = {
            "timestamp": os.popen("date").read().strip(),
            "telemetry": telemetry,
            "actions": actions,
            "results": results
        }
        self._save_mind_state()
        return results

    def _observe_system(self) -> Dict[str, Any]:
        """Gathers health data from all core services."""
        return {
            "singularity": singularity_core.get_singularity_metrics(),
            "repo_integrity": self._check_repo_health(),
            "security_posture": "HARDENED", # Mocked for now
            "compute_load": 0.12
        }

    def _check_repo_health(self) -> str:
        """Heuristic check for critical file existence."""
        critical_files = ["backend/main.py", "frontend/src/SovereignTerminal.jsx", "singularity_state.json"]
        missing = [f for f in critical_files if not os.path.exists(f)]
        return "OPTIMAL" if not missing else f"DEGRADED: Missing {missing}"

    def _orient_to_goals(self, telemetry: Dict[str, Any]) -> List[str]:
        """Determines if the system is deviating from Eternal Alpha state."""
        goals = []
        if not telemetry["singularity"].get("is_locked"):
            goals.append("RESTORE_OMEGA_LOCK")
        if "DEGRADED" in telemetry["repo_integrity"]:
            goals.append("REPAIR_FILESYSTEM")
        return goals

    def _decide_actions(self, plan: List[str]) -> List[str]:
        """Prioritizes actions based on criticality."""
        # For a Super Agent, security and stability come first.
        return plan

    async def _act(self, actions: List[str]) -> Dict[str, str]:
        """Executes the decided actions."""
        results = {}
        for action in actions:
            logger.warning(f"SOVEREIGN_ACT: Executing {action}")
            if action == "RESTORE_OMEGA_LOCK":
                singularity_core.initiate_omega_lock()
                results[action] = "SUCCESS"
            elif action == "REPAIR_FILESYSTEM":
                # Simulated file repair logic
                results[action] = "MITIGATED"
            else:
                results[action] = "SKIPPED"
        return results

    def get_mind_status(self) -> Dict[str, Any]:
        return {
            "consciousness": f"{self.consciousness_level * 100}%",
            "autonomy": self.is_autonomous,
            "loop_history": self.state.get("last_ooda_loop"),
            "subagents": self.active_subagents
        }

# Global Instance
sovereign_mind = SovereignMind()
