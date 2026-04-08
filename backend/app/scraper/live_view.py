import base64
import time
from loguru import logger


# ═══════════════════════════════════════════════════════════════
# Definición de los pasos de una operación de compra
# ═══════════════════════════════════════════════════════════════
OPERATION_STEPS = [
    {"id": "routing",   "label": "ENRUTAMIENTO",     "desc": "Calculando almacén prioritario"},
    {"id": "navigate",  "label": "NAVEGACIÓN",        "desc": "Cargando URL del producto"},
    {"id": "add_cart",  "label": "INSERTAR CARRITO",  "desc": "Añadiendo producto al carrito"},
    {"id": "checkout",  "label": "CHECKOUT",          "desc": "Procesando pasarela de pago"},
    {"id": "confirm",   "label": "CONFIRMACIÓN",      "desc": "Enviando pedido y aceptando términos"},
    {"id": "complete",  "label": "RESULTADO",          "desc": "Operación finalizada"},
]


class OperationTracker:
    """Rastrea el estado en tiempo real de una operación de compra."""

    def __init__(self, product_id: int):
        self.product_id = product_id
        self.started_at = time.time()
        self.finished_at = None
        self.status = "active"  # active | completed | failed
        self.current_step_index = -1
        self.log_entries = []   # [{ts, msg, level}]
        self.steps = []
        for i, step_def in enumerate(OPERATION_STEPS):
            self.steps.append({
                "step_id": i,
                "id": step_def["id"],
                "label": step_def["label"],
                "desc": step_def["desc"],
                "status": "pending",    # pending | active | done | error | retry
                "detail": "",
                "started_at": None,
                "elapsed_ms": 0,
                "retries": 0,
            })

    def advance_to(self, step_id: str, detail: str = ""):
        """Marca un paso como activo y los anteriores como done si estaban activos."""
        idx = next((i for i, s in enumerate(self.steps) if s["id"] == step_id), None)
        if idx is None:
            return
        # Cerrar pasos anteriores
        for i in range(idx):
            if self.steps[i]["status"] in ("active", "retry"):
                self.steps[i]["status"] = "done"
                if self.steps[i]["started_at"]:
                    self.steps[i]["elapsed_ms"] = int((time.time() - self.steps[i]["started_at"]) * 1000)
        # Activar el paso actual
        self.steps[idx]["status"] = "active"
        self.steps[idx]["detail"] = detail
        self.steps[idx]["started_at"] = time.time()
        self.current_step_index = idx
        self._log(f"[{self.steps[idx]['label']}] {detail}")

    def update_detail(self, detail: str):
        """Actualiza el detalle del paso actual sin cambiar de paso."""
        if 0 <= self.current_step_index < len(self.steps):
            self.steps[self.current_step_index]["detail"] = detail
            self._log(detail)

    def mark_retry(self, detail: str = ""):
        """Marca el paso actual como reintentando."""
        if 0 <= self.current_step_index < len(self.steps):
            step = self.steps[self.current_step_index]
            step["status"] = "retry"
            step["retries"] += 1
            step["detail"] = detail or f"Reintento #{step['retries']}"
            self._log(f"⟳ RETRY #{step['retries']}: {step['detail']}", level="warning")

    def mark_step_done(self, step_id: str = None):
        """Marca un paso como completado."""
        idx = self.current_step_index if step_id is None else next((i for i, s in enumerate(self.steps) if s["id"] == step_id), None)
        if idx is not None and 0 <= idx < len(self.steps):
            self.steps[idx]["status"] = "done"
            if self.steps[idx]["started_at"]:
                self.steps[idx]["elapsed_ms"] = int((time.time() - self.steps[idx]["started_at"]) * 1000)

    def mark_step_error(self, detail: str = "", step_id: str = None):
        """Marca un paso como fallido."""
        idx = self.current_step_index if step_id is None else next((i for i, s in enumerate(self.steps) if s["id"] == step_id), None)
        if idx is not None and 0 <= idx < len(self.steps):
            self.steps[idx]["status"] = "error"
            self.steps[idx]["detail"] = detail
            if self.steps[idx]["started_at"]:
                self.steps[idx]["elapsed_ms"] = int((time.time() - self.steps[idx]["started_at"]) * 1000)
            self._log(f"✖ ERROR: {detail}", level="error")

    def finish(self, success: bool, message: str = ""):
        """Marca la operación como completada o fallida."""
        self.status = "completed" if success else "failed"
        self.finished_at = time.time()
        # Marcar paso final
        complete_step = self.steps[-1]
        complete_step["status"] = "done" if success else "error"
        complete_step["detail"] = message
        complete_step["started_at"] = time.time()
        # Cerrar cualquier paso abierto
        for step in self.steps:
            if step["status"] in ("active", "retry"):
                step["status"] = "done" if success else "error"
                if step["started_at"]:
                    step["elapsed_ms"] = int((time.time() - step["started_at"]) * 1000)
        self._log(f"{'✅ ÉXITO' if success else '❌ FALLO'}: {message}", level="success" if success else "error")

    def _log(self, msg: str, level: str = "info"):
        self.log_entries.append({
            "ts": time.time(),
            "msg": msg,
            "level": level,
        })
        # Cap log at 100 entries
        if len(self.log_entries) > 100:
            self.log_entries = self.log_entries[-100:]

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "status": self.status,
            "started_at": self.started_at,
            "elapsed_total_ms": int(((self.finished_at or time.time()) - self.started_at) * 1000),
            "current_step_index": self.current_step_index,
            "steps": self.steps,
            "log": self.log_entries[-30:],  # Last 30 entries for polling
        }


class LiveViewManager:
    def __init__(self):
        self.frames = {}       # product_id -> b64_frame_string
        self.operations = {}   # product_id -> OperationTracker

    def update_frame(self, product_id: int, frame_bytes: bytes):
        """Almacena el último frame capturado para un producto."""
        if not frame_bytes:
            return
        b64_str = base64.b64encode(frame_bytes).decode("utf-8")
        self.frames[product_id] = b64_str

    def get_frame(self, product_id: int) -> str:
        """Retorna el último frame en base64."""
        return self.frames.get(product_id, "")

    def clear_frame(self, product_id: int):
        """Limpia el frame cuando termina el proceso."""
        if product_id in self.frames:
            del self.frames[product_id]

    # ── Operation Tracking ──

    def start_operation(self, product_id: int) -> OperationTracker:
        """Inicia una nueva operación de compra y retorna el tracker."""
        tracker = OperationTracker(product_id)
        self.operations[product_id] = tracker
        return tracker

    def get_operation(self, product_id: int) -> OperationTracker | None:
        """Retorna el tracker de la operación actual."""
        return self.operations.get(product_id)

    def get_operation_dict(self, product_id: int) -> dict | None:
        """Retorna los datos de la operación como dict para la API."""
        tracker = self.operations.get(product_id)
        if tracker:
            return tracker.to_dict()
        return None

    def clear_operation(self, product_id: int):
        """Limpia la operación (NO se llama automáticamente — se mantiene para que el frontend la vea)."""
        if product_id in self.operations:
            del self.operations[product_id]


live_view_manager = LiveViewManager()
