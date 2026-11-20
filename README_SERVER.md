# Backend WebSocket TTR v0.13.6.33 — ALPHA

Per le sale online **vere** serve un servizio dedicato. Questo backend esegue sala/lobby e inoltra dati di guida tra browser, ma **la fisica è calcolata dal client host** (non ancora server-autoritativa).

## Docker (consigliato)
```bash
docker build -t ttr-online .
docker run -p 8765:8765 -e PORT=8765 -e TTR_ALLOWED_ORIGINS=https://TUO-UTENTE.github.io ttr-online
```
In produzione usa il dominio HTTPS del servizio: il browser collegherà `wss://TUO-SERVER/ws`.

## Python
```bash
pip install -r requirements.txt
PORT=8765 python server.py
```
Endpoint salute: `GET /health`.
WebSocket: `/ws`.

## Hosting
Utilizza un servizio web Docker/Python con supporto WebSocket. Per esempio su Render: crea servizio web dalla directory `backend`, scegli Docker, esponi via dominio HTTPS, imposta la variabile `TTR_ALLOWED_ORIGINS` al dominio del sito GitHub Pages. Il servizio può avere costi o condizioni che cambiano: verifica il piano prima di pubblicare.

## Limiti e sicurezza
- Non ancora simulazione autoritativa del server, non usare per tornei competitivi o premi
- Sale temporanee solo in RAM, nessun salvataggio o storico; senza persistenza la riconnessione non ripristina una gara
- I client si collegano a un solo processo server; l'hosting deve lasciare attiva la connessione WebSocket
- Gli input sono limitati e il numero di posti è controllato, ma sono necessarie ulteriori verifiche di sicurezza prima di una pubblicazione pubblica su larga scala
- Un host che chiude la pagina termina la stanza

Supporto v0.13.6.33: 5 profili auto, inclusa Aero R (car=4).
