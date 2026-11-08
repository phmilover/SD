import csv
import os
from collections.abc import Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TextIO

from pos.application.ports import ResultsExporter
from pos.application.reports import StudentResult


class CsvResultsExporter(ResultsExporter):
    def export(self, results: Sequence[StudentResult], destination: str) -> None:
        path = Path(destination).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8-sig",
                newline="",
                dir=path.parent,
                prefix=".pos-",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                self._write_rows(stream, results)
                stream.flush()
                os.fsync(stream.fileno())
            # Оба файла на одном файловом разделе; прежний CSV заменяется только после успеха.
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _write_rows(stream: TextIO, results: Sequence[StudentResult]) -> None:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(
            ["Код", "Студент", "Группа", "Итог из 10", "Оценено", "Критериев", "Правило"]
        )
        for result in results:
            student, final = result.student, result.final
            writer.writerow(
                [
                    student.code,
                    student.name,
                    student.group,
                    f"{final.value:.2f}",
                    final.assessed,
                    final.total,
                    final.policy,
                ]
            )
