"""Stigmergy — Bio-inspired indirect coordination through pheromone signals.

Like ants leaving pheromone trails, agents deposit signals that
influence others' behavior without direct communication.
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class PheromoneType(Enum):
    RESOURCE = "resource"          # Points to a resource location
    DANGER = "danger"              # Warns of a hazard
    TRAIL = "trail"                # Marks a path
    TASK = "task"                  # Indicates work to be done
    TERRITORY = "territory"        # Claims an area


class EvaporationMode(Enum):
    LINEAR = "linear"              # Decreases by fixed amount
    EXPONENTIAL = "exponential"    # Decreases proportionally
    STEP = "step"                  # Drops at specific intervals


@dataclass
class Position:
    x: float
    y: float
    z: float = 0.0
    
    def distance_to(self, other: "Position") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + 
                        (self.z - other.z)**2)
    
    def __hash__(self):
        return hash((round(self.x, 2), round(self.y, 2), round(self.z, 2)))


@dataclass
class Pheromone:
    """A signal deposited by an agent."""
    source_id: str
    pheromone_type: PheromoneType
    position: Position
    strength: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    deposited_at: float = field(default_factory=time.time)
    half_life: float = 60.0  # Seconds until strength halves
    
    def age(self) -> float:
        return time.time() - self.deposited_at
    
    def current_strength(self, mode: EvaporationMode = EvaporationMode.EXPONENTIAL) -> float:
        age_s = self.age()
        if mode == EvaporationMode.EXPONENTIAL:
            decay = math.pow(0.5, age_s / self.half_life)
        elif mode == EvaporationMode.LINEAR:
            decay = max(0, 1 - age_s / (self.half_life * 2))
        else:  # STEP
            steps = int(age_s / self.half_life)
            decay = math.pow(0.5, steps)
        return self.strength * decay


@dataclass
class DetectionResult:
    nearby: List[Tuple[Pheromone, float]]  # (pheromone, distance)
    strongest: Optional[Pheromone] = None
    by_type: Dict[PheromoneType, List[Pheromone]] = field(default_factory=dict)
    total_strength: float = 0.0


class Stigmergy:
    """Stigmergic environment for indirect agent coordination."""
    
    def __init__(self, max_pheromones: int = 1000, default_half_life: float = 60.0,
                 detection_radius: float = 10.0, evaporation: EvaporationMode = EvaporationMode.EXPONENTIAL):
        self._pheromones: List[Pheromone] = []
        self.max_pheromones = max_pheromones
        self.default_half_life = default_half_life
        self.detection_radius = detection_radius
        self.evaporation = evaporation
        self._deposit_count = 0
        self._detect_count = 0
    
    def deposit(self, source_id: str, pheromone_type: PheromoneType, 
                position: Position, strength: float,
                metadata: Dict[str, Any] = None) -> Pheromone:
        """Deposit a pheromone signal."""
        pheromone = Pheromone(
            source_id=source_id, pheromone_type=pheromone_type,
            position=position, strength=strength,
            metadata=metadata or {}, half_life=self.default_half_life)
        
        self._pheromones.append(pheromone)
        self._deposit_count += 1
        
        # Prune old/weak pheromones if at capacity
        self._prune()
        
        return pheromone
    
    def detect(self, position: Position, 
               types: Optional[List[PheromoneType]] = None) -> DetectionResult:
        """Detect pheromones near a position."""
        self._detect_count += 1
        nearby = []
        strongest = None
        strongest_val = 0.0
        by_type: Dict[PheromoneType, List[Pheromone]] = {}
        total = 0.0
        
        for p in self._pheromones:
            # Filter by type
            if types and p.pheromone_type not in types:
                continue
            
            # Evaporate first
            current = p.current_strength(self.evaporation)
            if current < 0.001:
                continue
            
            # Check distance
            dist = position.distance_to(p.position)
            if dist <= self.detection_radius:
                nearby.append((p, dist))
                total += current
                
                if current > strongest_val:
                    strongest = p
                    strongest_val = current
                
                by_type.setdefault(p.pheromone_type, []).append(p)
        
        return DetectionResult(nearby=nearby, strongest=strongest,
                             by_type=by_type, total_strength=total)
    
    def reinforce(self, position: Position, pheromone_type: PheromoneType,
                  amount: float = 0.1, radius: float = 1.0):
        """Strengthen nearby pheromones of a given type."""
        for p in self._pheromones:
            if p.pheromone_type == pheromone_type:
                if p.position.distance_to(position) <= radius:
                    p.strength = min(1.0, p.strength + amount)
    
    def evaporate_all(self):
        """Remove all expired pheromones."""
        self._pheromones = [
            p for p in self._pheromones 
            if p.current_strength(self.evaporation) >= 0.001
        ]
    
    def _prune(self):
        """Remove weakest pheromones when at capacity."""
        if len(self._pheromones) <= self.max_pheromones:
            return
        self._pheromones.sort(key=lambda p: p.current_strength(self.evaporation))
        self._pheromones = self._pheromones[-self.max_pheromones:]
    
    def count(self) -> int:
        return len(self._pheromones)
    
    def stats(self) -> dict:
        by_type = {}
        for p in self._pheromones:
            t = p.pheromone_type.value
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total": len(self._pheromones),
            "max": self.max_pheromones,
            "deposits": self._deposit_count,
            "detections": self._detect_count,
            "by_type": by_type,
        }


class TrailFollower:
    """Agent that follows pheromone trails."""
    
    def __init__(self, agent_id: str, stigmergy: Stigmergy, speed: float = 1.0):
        self.agent_id = agent_id
        self.stigmergy = stigmergy
        self.position = Position(0, 0)
        self.speed = speed
        self.history: List[Position] = [self.position]
        self.trail_type = PheromoneType.TRAIL
    
    def step(self) -> Position:
        """Move toward strongest nearby pheromone."""
        detection = self.stigmergy.detect(self.position, [self.trail_type])
        
        if detection.strongest:
            target = detection.strongest.position
            dx = target.x - self.position.x
            dy = target.y - self.position.y
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0:
                self.position = Position(
                    self.position.x + (dx / dist) * self.speed,
                    self.position.y + (dy / dist) * self.speed
                )
        else:
            # Random walk
            import random
            self.position = Position(
                self.position.x + random.uniform(-self.speed, self.speed),
                self.position.y + random.uniform(-self.speed, self.speed))
        
        self.history.append(self.position)
        # Leave own trail
        self.stigmergy.deposit(self.agent_id, self.trail_type, self.position, 0.3)
        return self.position
    
    def follow_n(self, steps: int) -> List[Position]:
        return [self.step() for _ in range(steps)]
