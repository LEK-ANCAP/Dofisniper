import base64
from loguru import logger

class LiveViewManager:
    def __init__(self):
        self.frames = {}  # product_id -> b64_frame_string
        self.active_listeners = {} # product_id -> set of websocket receivers (facultativo)

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

live_view_manager = LiveViewManager()
