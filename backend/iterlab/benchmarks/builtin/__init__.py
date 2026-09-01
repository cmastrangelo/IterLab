"""Built-in, deployment-agnostic benchmark adapters."""

from iterlab.benchmarks.builtin.candidate_labels import CandidateLabelsAdapter
from iterlab.benchmarks.builtin.sql_leaderboard import SqlLeaderboardAdapter
from iterlab.benchmarks.registry import register_adapter

register_adapter(SqlLeaderboardAdapter)
register_adapter(CandidateLabelsAdapter)

__all__ = ["CandidateLabelsAdapter", "SqlLeaderboardAdapter"]
