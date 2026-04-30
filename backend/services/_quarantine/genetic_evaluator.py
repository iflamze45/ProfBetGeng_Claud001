import logging
import random
from typing import List, Dict
from pydantic import BaseModel

logger = logging.getLogger("pbg.genetic_optimizer")

class RegionalSpec(BaseModel):
    id: str
    region: str
    alpha_threshold: float
    retry_limit: int
    success_rate: float
    generation: int

class GeneticEvaluator:
    """
    Biological-style evolution for SGN Node configurations.
    Culls underperformers and breeds new 'Alpha Clusters'.
    """
    
    def __init__(self):
        self.generation = 1
        self.population: List[RegionalSpec] = [
            RegionalSpec(id="LAG-BASE", region="Lagos", alpha_threshold=0.05, retry_limit=3, success_rate=0.82, generation=1),
            RegionalSpec(id="NYC-HYPER", region="New York", alpha_threshold=0.02, retry_limit=5, success_rate=0.91, generation=1),
            RegionalSpec(id="LON-TURBO", region="London", alpha_threshold=0.08, retry_limit=2, success_rate=0.74, generation=1)
        ]

    def evolve_population(self):
        """
        Runs the crossover and mutation cycle for node parameters.
        """
        logger.info(f"GENETIC: Starting Evolution Cycle for Generation {self.generation}...")
        
        # Sort by success rate
        self.population.sort(key=lambda s: s.success_rate, reverse=True)
        winner = self.population[0]
        
        # Breed new spec from winner (Crossover/Mutation)
        mutation_factor = random.uniform(0.9, 1.1)
        new_spec = RegionalSpec(
            id=f"SHARD-G{self.generation+1}-{random.randint(100,999)}",
            region=winner.region,
            alpha_threshold=max(0.01, winner.alpha_threshold * mutation_factor),
            retry_limit=max(1, winner.retry_limit + random.randint(-1, 1)),
            success_rate=0.0, # New genotype starts zeroed
            generation=self.generation + 1
        )
        
        # Replace worst performer
        culled = self.population.pop()
        self.population.append(new_spec)
        
        self.generation += 1
        logger.info(f"GENETIC: Culled Underperformer {culled.id}. Spawning High-Yield Offspring {new_spec.id} based on {winner.id} success.")
        return new_spec

    def export_optimal_parameters(self, region: str) -> Dict:
        """
        Returns the evolved parameters for a specific region.
        Used by the main Odds Engine for execution logic.
        """
        regional_specs = [p for p in self.population if p.region == region]
        if not regional_specs:
            return {"alpha_threshold": 0.05, "retry_limit": 3}
        
        # Strategy: Best of region
        best = sorted(regional_specs, key=lambda x: x.success_rate, reverse=True)[0]
        return {
            "alpha_threshold": round(best.alpha_threshold, 4),
            "retry_limit": best.retry_limit,
            "gen_id": best.id
        }

# Singleton
genetic_core = GeneticEvaluator()
