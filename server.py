import threading
import time
import requests
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

process_id = os.environ.get("PROCESS_ID", "P?")
peers = os.environ.get("PEERS", "").split(",")

# Estados
timestamp = 0
reply_count = 0
deferred_requests = []
requesting_sc = False
in_cs = False

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] [{process_id}] {msg}", flush=True)

@app.route('/request', methods=['POST'])
def on_request():
    global timestamp, deferred_requests, in_cs, requesting_sc
    data = request.get_json()
    sender = data["sender"]
    ts = data["timestamp"]

    timestamp = max(timestamp, ts) + 1

    if in_cs or (requesting_sc and (ts, sender) > (timestamp, process_id)):
        deferred_requests.append(sender)
        log(f"🕒 está na SC → armazenando pedido de {sender}")
    else:
        log(f"📩 recebeu REQUEST de {sender} → enviando REPLY")
        try:
            requests.post(f"http://{sender}:5000/reply", json={"sender": process_id})
        except Exception as e:
            log(f"⚠️ erro ao enviar REPLY para {sender}: {e}")
    return jsonify({"ok": True})

@app.route('/reply', methods=['POST'])
def on_reply():
    global reply_count
    data = request.get_json()
    sender = data["sender"]
    reply_count += 1
    log(f"📨 recebeu REPLY de {sender}")
    return jsonify({"ok": True})

def enter_critical_section():
    global requesting_sc, in_cs, reply_count, timestamp

    time.sleep(int(process_id[-1]) * 2)  # tempo aleatório baseado no id
    timestamp += 1
    requesting_sc = True
    reply_count = 0
    log(f"🕓 quer entrar na SC (timestamp {timestamp})")

    for peer in peers:
        if not peer:
            continue
        t = threading.Thread(target=send_request, args=(peer,))
        t.start()

    while reply_count < len(peers):
        time.sleep(0.5)

    in_cs = True
    log("🔒 entrou na Seção Crítica!")
    time.sleep(3)
    in_cs = False
    requesting_sc = False
    log("✅ saiu da Seção Crítica")

    # libera os pedidos pendentes
    for p in deferred_requests:
        try:
            requests.post(f"http://{p}:5000/reply", json={"sender": process_id})
        except Exception as e:
            log(f"⚠️ erro ao enviar REPLY atrasado para {p}: {e}")
    deferred_requests.clear()

def send_request(peer):
    global timestamp
    url = f"http://{peer}:5000/request"
    payload = {"sender": process_id, "timestamp": timestamp}

    for _ in range(5):
        try:
            log(f"→ REQUEST({timestamp}) → {url}")
            requests.post(url, json=payload, timeout=2)
            return
        except Exception as e:
            log(f"⚠️ {peer} indisponível, tentando novamente em 2s...")
            time.sleep(2)
    log(f"❌ falha ao contatar {peer} após 5 tentativas")

if __name__ == '__main__':
    log("🚀 iniciado. Aguardando peers ficarem prontos...")
    threading.Thread(target=lambda: (time.sleep(5), enter_critical_section())).start()
    app.run(host='0.0.0.0', port=5000)
