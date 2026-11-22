"""
Módulo de auditoría en memoria para registro de transacciones recientes.
Permite a la consola web interactiva y a los analistas visualizar el historial de decisiones en tiempo real.
"""

from typing import List, Dict, Any
from collections import deque
import threading

class TransactionAuditBuffer:
    def __init__(self, max_capacity: int = 200):
        self.buffer = deque(maxlen=max_capacity)
        self.lock = threading.Lock()

    def record(self, item: Dict[str, Any]):
        with self.lock:
            self.buffer.appendleft(item)

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.buffer)[:limit]


audit_buffer = TransactionAuditBuffer()
