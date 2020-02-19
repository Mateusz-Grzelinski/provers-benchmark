from __future__ import annotations

import json

from provers_benchmark.parsers.parsers import StatisticParser
from provers_benchmark.statistics.stats import ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo


class InkresatCNFPTLStatisticParser(StatisticParser):
    """Inkresat conjunctive normal form propositional temporal logic statistic parser"""

    @staticmethod
    def get_file_input_statistics(file_path: str) -> ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo:
        assert file_path.endswith('.json'), 'expected json files for statistics'
        with open(file_path, 'r') as fp:
            dict = json.load(fp)
        stats = ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo()
        for key, val in dict.items():
            if key == 'clause_sizes':
                setattr(stats, key, {int(key): int(val) for key, val in dict['clause_sizes'].items()})
            else:
                setattr(stats, key, val)
        return stats
