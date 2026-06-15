from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

from openpyxl import Workbook

from src.config import BotConfig
from src.excel_reader import BudgetItem
from src.material_service import MaterialProcessResult


class HistoryManager:
    """Cuida das pastas: a processar, processados e histórico."""

    def __init__(self, config: BotConfig, logger: Any):
        self.config = config
        self.logger = logger
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.pending_dir = Path(config.paths.pending_dir)
        self.processed_dir = Path(config.paths.processed_dir)
        self.history_dir = Path(config.paths.history_dir)
        self.export_dir = Path(config.paths.export_dir)
        self.pdf_dir = Path(config.paths.pdf_dir)
        self.ensure_directories()

    def ensure_directories(self) -> None:
        for path in [self.pending_dir, self.processed_dir, self.history_dir, self.export_dir, self.pdf_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def copy_input_to_pending(self, excel_path: Path) -> Path:
        target = self.pending_dir / f"{self.execution_id}_{excel_path.name}"
        if excel_path.exists():
            shutil.copy2(excel_path, target)
            self.logger.info("Cópia da planilha salva em A processar: %s", target)
        return target

    def copy_input_to_processed(self, excel_path: Path) -> Path:
        target = self.processed_dir / f"{self.execution_id}_{excel_path.name}"
        if excel_path.exists():
            shutil.copy2(excel_path, target)
            self.logger.info("Cópia da planilha salva em Processados: %s", target)
        return target

    def move_to_processed(self, excel_path: Path) -> Path:
        processed_dir = _get_base_dir() / "processados"
        processed_dir.mkdir(parents=True, exist_ok=True)
        target = processed_dir / f"{self.execution_id}_{excel_path.name}"
        if excel_path.exists():
            shutil.move(str(excel_path), target)
            self.logger.info("Planilha movida para processados: %s", target)
        return target

    def write_history(
        self,
        items: Iterable[BudgetItem],
        material_results: Iterable[MaterialProcessResult],
        client_code: str | None = None,
        budget_number: str | None = None,
    ) -> Path:
        result_by_code = {result.item.code_or_reference: result for result in material_results}
        path = self.history_dir / f"historico_execucao_{self.execution_id}.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Histórico"
        sheet.append([
            "Execução",
            "Linha origem",
            "Código/Referência",
            "Quantidade",
            "Item planilha",
            "Status",
            "Mensagem",
            "Código interno GRV",
            "Item GRV",
            "Família",
            "Grupo",
            "Código cliente/empresa",
            "Orçamento gerado",
        ])

        for item in items:
            result = result_by_code.get(item.code_or_reference)
            material = result.material if result else None
            sheet.append([
                self.execution_id,
                item.row_number,
                item.code_or_reference,
                item.quantity,
                item.item,
                result.status if result else "NAO_PROCESSADO",
                result.message if result else "Item não processado.",
                material.get("codigo_interno") if material else None,
                material.get("item") if material else None,
                material.get("familia") if material else None,
                material.get("grupo") if material else None,
                client_code,
                budget_number,
            ])

        for column in sheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column)
            sheet.column_dimensions[column[0].column_letter].width = min(max_length + 2, 60)

        workbook.save(path)
        workbook.close()
        self.logger.info("Histórico salvo em: %s", path)
        return path
