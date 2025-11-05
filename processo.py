import threading
import requests
import time
from datetime import datetime

# === Cores ANSI ===
COLORS = {
    1: "\033[96m",   # ciano
    2: "\033[93m",   # amarelo
    3: "\033[92m",   # verde
    4: "\033[95m",   # magenta
    "END": "\033[0m"
}

def log(pid, msg):
    """Imprime log com cor e timestamp."""
    color = COLORS.get(pid, "")
    now = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{now}] [P{pid}] {msg}{COLORS['END']}")

class Processo:
    def __init__(self, id, peers):
        self.id = id
        self.peers = peers  # URLs dos outros processos
        self.esperando = False
        self.relogio = 0
        self.recebidos = set()
        self.fila = []

    # === Funções principais ===
    def request(self):
        self.esperando = True
        self.relogio += 1
        self.recebidos = set()
        log(self.id, f"🕓 quer entrar na SC (timestamp {self.relogio})")

        for url in self.peers:
            log(self.id, f"→ REQUEST({self.relogio}) → {url}")
            threading.Thread(
                target=requests.post,
                args=(f"{url}/request",),
                kwargs={"json": {"id": self.id, "timestamp": self.relogio}},
            ).start()

        self.wait_for_replies()

    def wait_for_replies(self):
        while len(self.recebidos) < len(self.peers):
            time.sleep(0.3)
        log(self.id, "✅ recebeu todos os REPLYs → entra na SC")
        log(self.id, "💾 executando na SC...")
        time.sleep(2)
        self.release()

    def release(self):
        self.esperando = False
        log(self.id, "🚪 saindo da SC e liberando processos...")
        for url in self.peers:
            requests.post(f"{url}/release", json={"id": self.id})
        while self.fila:
            remetente = self.fila.pop(0)
            log(self.id, f"📤 enviando REPLY atrasado para P{remetente}")
            peer_url = next((p for p in self.peers if p.endswith(f"p{remetente}:5000")), None)
            if peer_url:
                requests.post(f"{peer_url}/reply", json={"id": self.id})

    # === Recepção de mensagens ===
    def receive_request(self, remetente, timestamp):
        self.relogio = max(self.relogio, timestamp) + 1
        if not self.esperando:
            log(self.id, f"📩 recebeu REQUEST de P{remetente} → enviando REPLY")
            peer_url = next((p for p in self.peers if p.endswith(f"p{remetente}:5000")), None)
            if peer_url:
                requests.post(f"{peer_url}/reply", json={"id": self.id})
        else:
            log(self.id, f"🕒 está na SC → armazenando pedido de P{remetente}")
            if remetente not in self.fila:
                self.fila.append(remetente)

    def receive_reply(self, remetente):
        self.recebidos.add(remetente)
        log(self.id, f"📨 recebeu REPLY de P{remetente}")

    def receive_release(self, remetente):
        log(self.id, f"🔓 recebeu RELEASE de P{remetente}")
