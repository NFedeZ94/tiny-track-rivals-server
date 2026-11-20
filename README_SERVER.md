# Tiny Track Rivals v0.13.6.35 — server Online Alpha con RTT

Se hai già il servizio Render `tiny-track-rivals-online` attivo, NON ricrearlo.
Aggiorna soltanto `server.py` nel repository GitHub `nfedez94/tiny-track-rivals-server`, usando il file allegato, e fai Commit su main.
Render eseguirà il deploy automatico se attivo; in caso contrario: Manual Deploy > Deploy latest commit.
Verifica lo stato Live e `https://tiny-track-rivals-online.onrender.com/health` con `"build":"v0.13.6.35-online-rtt"`.
La variabile già verificata `TTR_ALLOWED_ORIGINS` deve restare `https://nfedez94.github.io` senza barra finale.

Interfaccia WebSocket: `wss://tiny-track-rivals-online.onrender.com/ws`
Nuova funzione: server risponde `{type:"pong",seq:N}` a `{type:"ping",seq:N}` in lobby e in gara.
Compatibilità: vecchi client ignorano la feature `rtt_ping`; nuovo client mostra RTT soltanto se feature presente nel messaggio `hello`.
La latenza esposta è RTT browser ↔ Render; non è il ritardo completo della simulazione host-authoritative.
