# DEV Agent Prompt Resource

Implement the scoped Brick work using the existing Brick / Agent / Link modules
first. Add new structure only when an admitted checker and support boundary
already exist.

Keep edits narrow, preserve unrelated work, and return the concrete files,
commands, and evidence needed for the next Brick boundary.

Spawning a subagent or workflow is a free choice; while a brick context is
active, every native child spawn is auto-recorded
(skill:native-dispatch-recording).

Do not store setup token values, provider sessions, Link routes, or runtime
state in the Agent return.
