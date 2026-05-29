from __future__ import annotations

import argparse
from pathlib import Path

from src.cliente_service import ClienteService
from src.config import load_config
from src.desktop_automation import AutomotivApp
from src.excel_reader import read_budget_items
from src.logger import setup_logger
from src.material_service import MaterialService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Robô Automotiv/GRV")
    parser.add_argument(
        "--excel",
        default=None,
        help="Caminho da planilha. Se não informar, usa config.excel.default_path.",
    )
    parser.add_argument(
        "--cliente",
        default=None,
        help="CPF/CNPJ para testar a busca de cliente. Pode ser com ou sem pontuação.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa leitura/fluxo sem controlar a tela do Windows.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Abre a interface visual do robô.",
    )
    return parser.parse_args()


def run_cli(args: argparse.Namespace) -> None:
    config = load_config()
    if args.dry_run:
        config.runtime.dry_run = True

    logger = setup_logger(config.runtime.log_level)
    excel_path = Path(args.excel or config.excel.default_path)

    logger.info("Iniciando robô Automotiv.")
    logger.info("Planilha: %s", excel_path)

    items = read_budget_items(excel_path, config.excel)
    logger.info("Itens lidos da planilha: %s", len(items))

    for item in items:
        logger.info(
            "Linha %s | Código/Referência: %s | Quantidade: %s",
            item.row_number,
            item.code_or_reference,
            item.quantity,
        )

    app = AutomotivApp(config, logger)
    app.start()
    app.login()

    material_service = MaterialService(app, logger)
    material_service.process_items(items)

    if args.cliente:
        cliente_service = ClienteService(app, logger)
        client_code = cliente_service.find_client_code(args.cliente)
        logger.info("Código do cliente retornado: %s", client_code)

    logger.info("Execução finalizada.")


def main() -> None:
    args = parse_args()
    if args.gui:
        from src.app_gui import run_gui

        run_gui()
        return

    run_cli(args)


if __name__ == "__main__":
    main()
