from __future__ import annotations

import tempfile
import time
import os
from pathlib import Path
from typing import Optional

import pyautogui

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except Exception:
    _CV2_AVAILABLE = False

# Escalas a tentar quando a escala 1.0 não encontrar a imagem.
# Cobre DPI 100%→125%→150% do Windows e variações inversas.
_FALLBACK_SCALES = (0.75, 1.25, 0.875, 1.5, 0.67)


def log_cv2_status(logger) -> None:
    """Loga se cv2 está disponível ou não. Chame no startup para diagnóstico."""
    if _CV2_AVAILABLE:
        logger.info("cv2 (OpenCV) disponível: SIM → matching com confidence ativo (tolerante a variações).")
    else:
        logger.info("cv2 (OpenCV) disponível: NAO → matching exato pixel-perfect (pode falhar em outras resolucoes).")


def _resize_image_temp(image_path: Path, scale: float) -> str | None:
    """Redimensiona a imagem e salva num arquivo temporário. Retorna o path ou None."""
    if not _CV2_AVAILABLE:
        return None
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    h, w = img.shape[:2]
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    suffix = image_path.suffix or ".png"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    cv2.imwrite(tmp.name, resized)
    tmp.close()
    return tmp.name


class ImageAutomation:
    """Utilitário de automação por imagem usando PyAutoGUI."""

    def __init__(self, assets_dir: str | Path, confidence: float = 0.85, logger=None) -> None:
        self.assets_dir = Path(assets_dir)
        self.confidence = confidence
        self.logger = logger
        self._scaled_image_cache: dict[tuple[str, float], str] = {}

    def _resolve_image_path(self, image_name: str | Path) -> Path:
        image_path = Path(image_name)
        if image_path.is_absolute():
            return image_path
        return self.assets_dir / image_path

    def image_exists_on_disk(self, image_name: str | Path) -> bool:
        return self._resolve_image_path(image_name).exists()

    def _get_scaled_image_path(self, image_path: Path, scale: float) -> str | None:
        """Retorna uma imagem redimensionada em cache para evitar custo repetido no matching."""
        if scale == 1.0:
            return str(image_path)
        key = (str(image_path.resolve()), scale)
        cached = self._scaled_image_cache.get(key)
        if cached and Path(cached).exists():
            return cached
        tmp_path = _resize_image_temp(image_path, scale)
        if tmp_path:
            self._scaled_image_cache[key] = tmp_path
        return tmp_path

    def _try_locate_at_scale(self, image_path: Path, scale: float, confidence: float | None):
        """Tenta localizar a imagem na escala dada. Retorna center ou None."""
        target = self._get_scaled_image_path(image_path, scale)
        if not target:
            return None
        try:
            kwargs = {"confidence": confidence} if confidence is not None else {}
            center = pyautogui.locateCenterOnScreen(target, **kwargs)
            return center
        except Exception:
            return None

    def cleanup_cache(self) -> None:
        for tmp_path in self._scaled_image_cache.values():
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        self._scaled_image_cache.clear()

    def __del__(self) -> None:
        self.cleanup_cache()

    def locate_center(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
    ):
        image_path = self._resolve_image_path(image_name)
        if not image_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        raw_confidence = confidence if confidence is not None else self.confidence
        final_confidence = raw_confidence if _CV2_AVAILABLE else None
        deadline = time.time() + timeout
        last_error: Exception | None = None

        while time.time() < deadline:
            try:
                center = self._try_locate_at_scale(image_path, 1.0, final_confidence)
                if center:
                    return center

                # Fallback multi-escala: cobre DPI diferente entre máquinas
                if _CV2_AVAILABLE:
                    for scale in _FALLBACK_SCALES:
                        center = self._try_locate_at_scale(image_path, scale, final_confidence)
                        if center:
                            if self.logger:
                                self.logger.debug(
                                    "Imagem %s encontrada com escala %.2fx (DPI diferente detectado).",
                                    image_path.name, scale,
                                )
                            return center
            except Exception as error:
                last_error = error
            time.sleep(0.5)

        if last_error and self.logger:
            self.logger.debug("Último erro ao buscar imagem %s: %s", image_path, last_error)
        return None

    def locate(self, image_name: str | Path, timeout: int = 10, confidence: float | None = None):
        return self.locate_center(image_name=image_name, timeout=timeout, confidence=confidence)

    def exists(self, image_name: str | Path, timeout: int = 3, confidence: float | None = None) -> bool:
        return self.locate_center(image_name=image_name, timeout=timeout, confidence=confidence) is not None

    def click(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
        clicks: int = 1,
        interval: float = 0.05,
        button: str = "left",
    ) -> bool:
        center = self.locate_center(image_name=image_name, timeout=timeout, confidence=confidence)
        if not center:
            return False
        pyautogui.click(x=center.x, y=center.y, clicks=clicks, interval=interval, button=button)
        return True

    def double_click(self, image_name: str | Path, timeout: int = 10, confidence: Optional[float] = None) -> bool:
        return self.click(image_name=image_name, timeout=timeout, confidence=confidence, clicks=2)

    def click_if_exists(self, image_name: str | Path, timeout: int = 3, confidence: float | None = None) -> bool:
        return self.click(image_name=image_name, timeout=timeout, confidence=confidence)

    def click_bottommost(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: float | None = None,
    ) -> bool:
        image_path = self._resolve_image_path(image_name)
        if not image_path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        raw_confidence = confidence if confidence is not None else self.confidence
        final_confidence = raw_confidence if _CV2_AVAILABLE else None
        deadline = time.time() + timeout
        last_error: Exception | None = None

        while time.time() < deadline:
            try:
                kwargs = {"confidence": final_confidence} if final_confidence is not None else {}
                matches = list(pyautogui.locateAllOnScreen(str(image_path), **kwargs))
                if matches:
                    bottom_match = max(matches, key=lambda box: box.top)
                    center_x = bottom_match.left + bottom_match.width // 2
                    center_y = bottom_match.top + bottom_match.height // 2
                    pyautogui.click(center_x, center_y)
                    return True
            except Exception as error:
                last_error = error
            time.sleep(0.5)

        if last_error and self.logger:
            self.logger.debug("Último erro ao clicar imagem inferior %s: %s", image_path, last_error)
        return False

    def wait_until_visible(self, image_name: str | Path, timeout: int = 10, confidence: Optional[float] = None) -> bool:
        return self.exists(image_name=image_name, timeout=timeout, confidence=confidence)

    def click_with_offset(
        self,
        image_name: str | Path,
        offset_x: int = 0,
        offset_y: int = 0,
        timeout: int = 10,
        confidence: float | None = None,
    ) -> bool:
        """Localiza a imagem e clica com deslocamento em pixels a partir do centro."""
        center = self.locate_center(image_name=image_name, timeout=timeout, confidence=confidence)
        if not center:
            return False
        pyautogui.click(x=center.x + offset_x, y=center.y + offset_y)
        return True

    def click_or_raise(
        self,
        image_name: str | Path,
        timeout: int = 10,
        confidence: Optional[float] = None,
        error_message: str | None = None,
    ) -> None:
        if self.click(image_name=image_name, timeout=timeout, confidence=confidence):
            return
        image_path = self._resolve_image_path(image_name)
        raise RuntimeError(error_message or f"Não foi possível localizar/clicar na imagem: {image_path}")
