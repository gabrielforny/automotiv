from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


def _get_base_dir() -> Path:
    """Retorna a pasta onde o executável (ou o script em dev) está localizado."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

from src.cliente_service import ClienteService
from src.config import load_config
from src.desktop_automation import AutomotivApp
from src.excel_reader import read_budget_items, read_company_name_from_excel, read_login_credentials_from_excel
from src.image_automation import log_cv2_status
from src.logger import setup_logger
from src.material_service import MaterialService
from src.site_search_service import SiteSearchService
from src.history_manager import HistoryManager
from src.orcamento_service import OrcamentoService


class QueueLogger:
    def __init__(self, log_queue: queue.Queue[str], base_logger):
        self.log_queue = log_queue
        self.base_logger = base_logger

    def _write(self, level: str, message: str, *args):
        text = message % args if args else message
        self.log_queue.put(f"[{level}] {text}")
        getattr(self.base_logger, level.lower())(message, *args)

    def info(self, message: str, *args):
        self._write("INFO", message, *args)

    def warning(self, message: str, *args):
        self._write("WARNING", message, *args)

    def error(self, message: str, *args):
        self._write("ERROR", message, *args)

    def debug(self, message: str, *args):
        self._write("DEBUG", message, *args)


class AutomotivBotGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Robô Automotiv")
        self.geometry("820x560")
        self.resizable(True, True)

        self.config_data = load_config()
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

        self.excel_path = tk.StringVar(value="")
        self.cliente = tk.StringVar(value="")

        self._try_auto_detect_excel()
        self._build_layout()
        self.after(200, self._consume_logs)

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="Robô Automotiv", font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            container,
            text="Coloque a planilha de orçamento nesta mesma pasta e clique em Iniciar.",
        )
        subtitle.pack(anchor="w", pady=(0, 12))

        form = ttk.LabelFrame(container, text="Planilha de orçamento", padding=12)
        form.pack(fill="x")

        detected = self.excel_path.get()
        hint = f"Detectada automaticamente: {Path(detected).name}" if detected else "Nenhuma planilha encontrada nesta pasta."
        self.file_hint = ttk.Label(form, text=hint, foreground="green" if detected else "red")
        self.file_hint.grid(row=0, column=0, sticky="w", pady=(0, 6))

        ttk.Entry(form, textvariable=self.excel_path).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(form, text="Trocar...", command=self._select_excel).grid(row=1, column=1, sticky="e")

        ttk.Label(form, text="CPF/CNPJ do cliente (opcional):").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(form, textvariable=self.cliente).grid(row=3, column=0, sticky="ew", padx=(0, 8))

        form.columnconfigure(0, weight=1)

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=12)
        self.start_button = ttk.Button(actions, text="Iniciar robô", command=self._start)
        self.start_button.pack(side="left")
        ttk.Button(actions, text="Sair", command=self.destroy).pack(side="left", padx=(8, 0))

        self.status = ttk.Label(container, text="Aguardando início.")
        self.status.pack(anchor="w")

        log_frame = ttk.LabelFrame(container, text="Acompanhamento", padding=8)
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.log_text = tk.Text(log_frame, height=18, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")


    def _try_auto_detect_excel(self) -> None:
        base = _get_base_dir()
        xlsx_files = sorted(
            (f for f in base.glob("*.xlsx") if not f.name.startswith("~")),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if xlsx_files:
            self.excel_path.set(str(xlsx_files[0]))

    def _resolve_excel_path(self) -> Path:
        typed_path = self.excel_path.get().strip()
        if typed_path:
            return Path(typed_path)
        return _get_base_dir()

    def _select_excel(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecione a planilha",
            filetypes=[("Planilhas Excel", "*.xlsx *.xlsm"), ("Todos os arquivos", "*.*")],
        )
        if path:
            self.excel_path.set(path)

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Robô Automotiv", "O robô já está em execução.")
            return

        excel = self._resolve_excel_path()
        if not excel.exists():
            messagebox.showerror("Planilha não encontrada", f"Não encontrei a planilha:\n{excel}")
            return

        self.start_button.configure(state="disabled")
        self.status.configure(text="Executando...", foreground="")
        self._append_log("[INFO] Execução iniciada.")

        self.worker = threading.Thread(target=self._run_bot, daemon=True)
        self.worker.start()

    def _run_bot(self) -> None:
        try:
            config = load_config()
            config.runtime.dry_run = False
            base_logger = setup_logger(config.runtime.log_level)
            logger = QueueLogger(self.log_queue, base_logger)

            import sys, platform
            logger.info("=== DIAGNOSTICO DE AMBIENTE ===")
            logger.info("Sistema operacional: %s %s", platform.system(), platform.version())
            logger.info("Resolucao de tela: %s x %s", *__import__('pyautogui').size())
            logger.info("Python: %s", sys.version)
            logger.info("Frozen (EXE): %s", getattr(sys, 'frozen', False))
            log_cv2_status(logger)
            logger.info("Assets dir: %s", config.images.assets_dir)
            logger.info("Confidence configurada: %s", config.images.confidence)
            logger.info("===============================")

            excel_path = self._resolve_excel_path()
            history = HistoryManager(config, logger)
            logger.info("Planilha usada: %s", excel_path)

            items = read_budget_items(excel_path, config.excel)
            logger.info("Itens lidos da planilha: %s", len(items))
            company_name = read_company_name_from_excel(excel_path, config.excel, logger=logger)
            logger.info("Nome da empresa lido da planilha: %s", company_name)
            login_nome, login_senha = read_login_credentials_from_excel(excel_path, config.excel)
            logger.info("Credenciais lidas da planilha: nome=%s senha=%s", login_nome, "***" if login_senha else None)
            for item in items:
                logger.info("Linha %s | Código/Referência: %s | Quantidade: %s", item.row_number, item.code_or_reference, item.quantity)

            app = AutomotivApp(config, logger)
            missing_images = app.find_missing_configured_images()
            if missing_images:
                logger.warning("Imagens configuradas sem arquivo: %s", len(missing_images))
                for image_key, image_name in missing_images[:30]:
                    logger.warning("Imagem ausente: %s -> %s", image_key, image_name)
                if len(missing_images) > 30:
                    logger.warning("Mais %s imagem(ns) ausente(s) omitidas do log.", len(missing_images) - 30)
            app.start()
            app.login(nome=login_nome, senha=login_senha)

            site_service = SiteSearchService(config, logger)
            material_service = MaterialService(app, site_service, logger)
            material_results = material_service.process_items(items)

            client_code = None
            carrier_code = None
            cliente = self.cliente.get().strip()
            if cliente:
                cliente_service = ClienteService(app, logger)
                client_code, carrier_code, client_company_name = cliente_service.find_client_code(cliente)
                # Nome do GRV tem prioridade; se não encontrado, mantém o do Excel de orçamento
                company_name = client_company_name or company_name
                logger.info(
                    "Cliente: código=%s | transportadora=%s | nome=%s",
                    client_code, carrier_code, company_name,
                )

            budget_number = None
            if config.workflow.enable_budget_flow:
                orcamento_service = OrcamentoService(app, logger)
                budget_number = orcamento_service.create_from_material_results(
                    material_results,
                    company_code=client_code,
                    company_name=company_name,
                    carrier_code=carrier_code,
                )
                logger.info("Orçamento retornado/gerado: %s", budget_number)
            else:
                logger.info("Fluxo de orçamento desabilitado em workflow.enable_budget_flow=false.")

            history.write_history(items, material_results, client_code=client_code, budget_number=budget_number)
            history.move_to_processed(excel_path)
            logger.info("Execução finalizada.")
            self.log_queue.put("__SUCCESS__")
        except Exception as exc:
            self.log_queue.put(f"[ERROR] {exc}")
            self.log_queue.put("__ERROR__")

    def _consume_logs(self) -> None:
        while not self.log_queue.empty():
            message = self.log_queue.get()
            if message == "__SUCCESS__":
                self.start_button.configure(state="normal")
                self.status.configure(
                    text="Concluido com sucesso!",
                    foreground="green",
                )
            elif message == "__ERROR__":
                self.start_button.configure(state="normal")
                self.status.configure(
                    text="Erro durante a execucao. Veja o log acima.",
                    foreground="red",
                )
            else:
                self._append_log(message)
        self.after(200, self._consume_logs)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def run_gui() -> None:
    app = AutomotivBotGui()
    app.mainloop()
