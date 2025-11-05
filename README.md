# Exclusão Mútua Distribuída

Este repositório contém uma implementação didática do algoritmo Ricart‑Agrawala para exclusão mútua sem coordenador central, usando trocas de mensagens HTTP entre processos. É destinado a demonstração e aprendizado, não produção.

[Explicação aprofundada no Google Docs](https://docs.google.com/document/d/1aYuY9yKUYu7AuOilrdxTzrVwknRVSDElsaJVPGlA11U/edit?usp=sharing)

## 1. Visão geral (resumo rápido)

Ricart‑Agrawala é um protocolo distribuído em que cada processo pede permissão a todos os outros antes de entrar na seção crítica. Peers respondem com um REPLY imediatamente ou diferem a resposta se tiverem prioridade para entrar primeiro. Quando um processo recebe REPLYs de todos os demais, ele entra na seção crítica.

### Por que usar

- Remove necessidade de um coordenador central (menor ponto único de falha).
- Simples conceitualmente e fácil de demonstrar com mensagens REQUEST/REPLY.
- Garante exclusão mútua e evita deadlock sob as suposições clássicas.

### Contrato de mensagens

- REQUEST: { sender, timestamp } — pedido de acesso.
- REPLY: { sender } — autorização.
Timestamps lógicos (Lamport) são usados para ordenar pedidos; em empate usa‑se um tie‑breaker (id do processo).

## 2. O que há em cada arquivo

- [server.py](server.py) — serviço principal (endpoints HTTP e lógica do protocolo).
  - Implementa endpoints `POST /request` e `POST /reply`. Veja funções centrais como [`enter_critical_section`](server.py) e [`send_request`](server.py).
  - Estado global: `timestamp`, `reply_count`, `deferred_requests`, `requesting_sc`, `in_cs`.
  - Observações: comparação (timestamp, id) depende de ordering lexicográfica de `PROCESS_ID`. Não há locks em variáveis compartilhadas; race conditions são possíveis. Busy-wait usado para aguardar replies; pode-se melhorar com `threading.Event`/`Condition`.

- [processo.py](processo.py) — versão orientada a objetos, exemplo local/educacional.
  - Contém a classe [`Processo`](processo.py) com método [`request`](processo.py), `receive_request`, `receive_reply`, `release`.
  - Usa chaves JSON e endpoints que diferem de `server.py` (por exemplo, `id` vs `sender`, `/release`), portanto não é um cliente drop‑in para `server.py`. Serve como material didático.

- [dockerfile](dockerfile) — imagem mínima (Python 3.11-slim) que copia o projeto, instala `flask` e `requests` e executa `server.py` em modo unbuffered.
- [docker-compose.yml](docker-compose.yml) — orquestra três instâncias (p1, p2, p3). Cada serviço define `PROCESS_ID` e `PEERS`; Docker Compose fornece resolução de nomes (ex.: `http://p2:5000`).

## 3. Passo a passo do algoritmo (comportamento observado)

### Quando P quer entrar na SC

1. Incrementa relógio lógico e cria REQUEST (timestamp, P).
2. Envia REQUEST a todos os peers (N-1 mensagens).
3. Aguarda REPLY de cada peer.
4. Entra na SC quando recebe todos os REPLYs.

### Ao receber REQUEST (ts_q, Q)

1. Atualiza relógio: timestamp = max(timestamp, ts_q) + 1.
2. Se não está interessado → envia REPLY imediatamente.
3. Se está na SC → difere (armazena em deferred list).
4. Se também pediu, compara prioridades (ts_q, Q) vs (ts_r, R): o menor ganha; caso contrário difere.

### Ao sair da SC

- Envia REPLYs para todos os pedidos diferidos e limpa a lista.

### Exemplo (3 processos: p1, p2, p3)

- p1 envia REQUEST a p2 e p3.
- p2 envia REPLY a menos que também tenha pedido e tenha prioridade.
- p1 entra na SC ao receber 2 REPLYs e, ao sair, libera pedidos diferdos.

## 4. Complexidade, garantias e limitações

- Mensagens por entrada na SC: 2*(N-1).
- Latência: pelo menos um round‑trip por peer.
- Estado local: lista de pedidos diferidos (O(N)), contador/deduplicador de replies.
- Garantias: exclusão mútua e ordenação por timestamps + tie‑breaker; liveness sob suposições (mensagens entregues, peers respondendo).
- Limitações e riscos:
  - Conjunto de participantes conhecido e estático.
  - Mensagens consideradas confiáveis (implementação tem retries simples).
  - Falha de peer pode bloquear solicitantes (nenhuma recuperação automática).
  - Race conditions: `reply_count`, `timestamp`, `deferred_requests` não são protegidos por locks.
  - Comparação por `PROCESS_ID` lexicográfica é frágil fora do formato pN.
  - Busy‑wait para aguardar replies (ineficiente).
  - `processo.py` e `server.py` usam formatos/endereços diferentes — incompatibilidade.

## 5. Operação com Docker Compose

Para rodar:

```powershell
docker-compose up --build
