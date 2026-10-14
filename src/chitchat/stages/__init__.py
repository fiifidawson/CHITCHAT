"""Pipeline stages. Each one reads and writes files inside runs/<run>/."""


class StageError(RuntimeError):
    """A stage can't run, e.g. its input is missing."""
