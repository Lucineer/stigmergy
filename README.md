# Stigmergy

Bio-inspired indirect coordination through pheromone signals. Like ants leaving trails.

## Pheromone Types

- **RESOURCE**: Points to a resource location
- **DANGER**: Warns of a hazard
- **TRAIL**: Marks a path
- **TASK**: Indicates work to be done
- **TERRITORY**: Claims an area

## Usage

```python
from stigmergy import Stigmergy, PheromoneType, Position, TrailFollower

env = Stigmergy(max_pheromones=100, default_half_life=60)
env.deposit('ant-1', PheromoneType.RESOURCE, Position(10, 20), 0.8)

detection = env.detect(Position(8, 15), [PheromoneType.RESOURCE])
follower = TrailFollower('ant-4', env, speed=1.0)
trail = follower.follow_n(10)
```

Part of the [Lucineer ecosystem](https://github.com/Lucineer/the-fleet).