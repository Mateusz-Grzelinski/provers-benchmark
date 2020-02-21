from __future__ import annotations

import os
from concurrent.futures.process import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import List, ClassVar, Tuple, Optional

from provers_benchmark.errors import BenchmarkException
from provers_benchmark.log import get_logger
from provers_benchmark.parsers.parsers import get_input_parser
from provers_benchmark.statistics.stats import MinimalSATStatistics
from provers_benchmark.translators import Translator

logger = get_logger()


@dataclass
class TestInput:
    name: str
    format: str
    cwd: str = os.getcwd()
    path: str = None
    files: List[str] = field(default_factory=list)
    gather_statistics_from_json_file: bool = False
    gather_statistics_from_formula_file: bool = False

    translators: ClassVar[List[Translator]] = []

    cache_path: ClassVar[str] = ".cache"

    def __post_init__(self):
        if self.path is not None and not os.path.isabs(self.path):
            self.path = os.path.realpath(os.path.join(self.cwd, self.path))

        for file in self.files:
            if not os.path.isfile(os.path.join(self.path, file)):
                raise BenchmarkException(f"file {file} does not exists (is not a file)", self)

    # todo add caching, make it static
    def get_file_statistics(self, file_path: str):
        # [MinimalSATStatistics, ConjunctiveNormalFormFirstOrderLogicSATStatistics, ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo]:
        parser = get_input_parser(format_name=self.format)
        min_stats = MinimalSATStatistics(name=self.name, path=file_path, format=self.format)
        if not parser:
            logger.warning(f'no statistics available for format {self.format}. Only TPTP stats are supported')
            # todo return basic stats even if there is no parser
            return min_stats, None

        if self.gather_statistics_from_formula_file:
            stats = parser.get_file_input_statistics(file_path=file_path)
            stats.name = self.name
            return min_stats, stats
        if self.gather_statistics_from_json_file:
            try:
                stats = parser.get_file_input_statistics(file_path + '.json')
                stats.name = self.name
                return min_stats, stats
            except FileNotFoundError:
                logger.warning(
                    f'Statistics for {os.path.abspath(file_path)} not available (not found file {os.path.abspath(file_path)}.json)')

        return MinimalSATStatistics(name=self.name, path=file_path), None

    # todo add caching
    def as_format(self, desired_format: str) -> Tuple[List[str], List[str], List[Optional[Translator]]]:
        """Convert self.files to different format
        Cache files will be written to cwd/self._cache_path/self.name/desired_format
        new extension is specified by translator
        :return path to files in specified format and statistics about this file
        """
        if desired_format == self.format:
            # keep the followwing lists the same size
            return self.files, self.files, [None for _ in self.files]

        # todo support translator chaining
        for translator in TestInput.translators:
            if translator.from_format == self.format and translator.to_format == desired_format:
                break
        else:
            raise BenchmarkException(f"No translator from {self.format} to {desired_format} found")

        pool = ProcessPoolExecutor(max_workers=8)
        out_file_paths = []
        translators = []
        for file in self.files:
            in_file_path = os.path.realpath(os.path.join(self.path, file))
            # /cwd/self._cache_path/self.name/desired_format/dir_structure(file)/file.extension
            out_file_path = os.path.join(self.cwd, TestInput.cache_path, self.name, desired_format,
                                         os.path.relpath(file, start=self.path))
            dirname, filename = os.path.split(out_file_path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            extension = '' if translator.extension is None else translator.extension
            out_file_path = os.path.join(dirname, os.path.splitext(filename)[0] + extension)

            future = pool.submit(translator.translate, in_file_path, out_file_path)
            future.add_done_callback(lambda x: logger.info(
                f"Translated {in_file_path} from {translator.from_format} to {translator.to_format} to {out_file_path}"))

            out_file_paths.append(out_file_path)
            translators.append(translator)
        pool.shutdown(wait=True)
        return self.files, out_file_paths, translators


if __name__ == '__main__':
    ti = TestInput(name='tmp',
                   format='TPTP',
                   path='/home/mat/studia-repos/studio-projektowe/logit-formula-generator/test_data/',
                   files=['data_set1_100_2-nowy.p'])
    stat = ti.get_file_statistics(
        file_path='/home/mat/studia-repos/studio-projektowe/logit-formula-generator/test_data/data_set1_100_2-nowy.p'
    )
    print(stat)
