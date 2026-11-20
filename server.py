"""Tiny Track Rivals v0.13.6.32 -- real WebSocket rooms / HOST-authoritative preview.
This is NOT an anti-cheat/server-physics implementation. Only relay accepted commands.
Run: pip install -r requirements.txt && python server.py
"""
import asyncio
import json
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from aiohttp import web, WSMsgType

PORT = int(os.getenv('PORT', '8765'))
ROOMS: dict[str, 'Room'] = {}
MAX_MSG = 24000
ALLOWED = set(filter(None, (s.strip() for s in os.getenv('TTR_ALLOWED_ORIGINS', '').split(','))))
ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

@dataclass
class Player:
    ws: web.WebSocketResponse
    slot: int
    name: str
    car: int
    ready: bool = False
    last_input: float = 0.0

@dataclass
class Room:
    code: str
    public: bool
    capacity: int
    host: web.WebSocketResponse
    players: dict[int, Player] = field(default_factory=dict)
    started: bool = False
    created_at: float = field(default_factory=time.time)
    last_frame: float = 0.0

async def send(ws, obj):
    if not ws.closed:
        try:
            await ws.send_json(obj, dumps=lambda value: json.dumps(value, separators=(',', ':'), ensure_ascii=False))
        except (ConnectionError, RuntimeError):
            pass

async def broadcast(room, obj, exclude=None):
    await asyncio.gather(*(send(p.ws,obj) for p in room.players.values() if p.ws is not exclude), return_exceptions=True)

def room_state(room):
    return {'type':'room_state', 'code':room.code, 'public':room.public, 'capacity':room.capacity, 'started':room.started,
            'members':[{'slot':slot,'name':p.name,'car':p.car,'ready':p.ready,'host':p.ws is room.host} for slot,p in sorted(room.players.items())]}

def locate(ws):
    for room in ROOMS.values():
        for player in room.players.values():
            if player.ws is ws: return room,player
    return None,None

async def leave(ws):
    room, player = locate(ws)
    if not room:return
    room.players.pop(player.slot,None)
    if ws is room.host:
        ROOMS.pop(room.code,None)
        await broadcast(room,{'type':'room_closed','reason':'L’organizzatore ha lasciato la sala.'})
    else:
        if room.started:
            await broadcast(room,{'type':'player_left','slot':player.slot})
        await broadcast(room,room_state(room))
        if not room.players:
            ROOMS.pop(room.code,None)

async def handler(request):
    origin=request.headers.get('Origin','')
    if ALLOWED and origin not in ALLOWED:
        return web.Response(status=403,text='Origin non autorizzata')
    ws=web.WebSocketResponse(heartbeat=25,max_msg_size=MAX_MSG,autoping=True)
    await ws.prepare(request)
    await send(ws,{'type':'hello','protocol':1,'message':'TTR WebSocket lobby + host simulation relay'})
    try:
        async for msg in ws:
            if msg.type!=WSMsgType.TEXT:continue
            try:
                d=json.loads(msg.data)
                if not isinstance(d,dict):continue
            except (ValueError,TypeError):continue
            op=d.get('type','')
            room,player=locate(ws)
            if op in ('create','find_public','join') and not room:
                name=re.sub(r'[^\w .-]','',str(d.get('name','Pilota')))[:18].strip() or 'Pilota'
                car=max(0,min(4,int(d.get('car',0))))
                capacity=int(d.get('capacity',4))
                capacity=capacity if capacity in (2,4,6,8) else 4
                if op=='create' or op=='find_public':
                    public=op=='find_public'
                    if public:
                        target=next((r for r in ROOMS.values() if r.public and not r.started and len(r.players)<r.capacity),None)
                    else:target=None
                    if target is None:
                        if len(ROOMS)>=120:
                            await send(ws,{'type':'error','message':'Server pieno'});continue
                        code=''.join(secrets.choice(ALPHABET) for _ in range(6))
                        while code in ROOMS:code=''.join(secrets.choice(ALPHABET) for _ in range(6))
                        target=Room(code,public,capacity,ws);ROOMS[code]=target
                else:
                    code=str(d.get('code','')).upper().strip()
                    target=ROOMS.get(code)
                    if target is None or target.started or len(target.players)>=target.capacity:
                        await send(ws,{'type':'error','message':'Sala inesistente, già avviata o piena.'});continue
                slot=next((i for i in range(target.capacity) if i not in target.players),None)
                if slot is None:await send(ws,{'type':'error','message':'Sala piena'});continue
                target.players[slot]=Player(ws,slot,name,car)
                await send(ws,{'type':'joined','slot':slot,'code':target.code,'host':ws is target.host})
                await broadcast(target,room_state(target))
            elif op=='ready' and room and not room.started:
                player.ready=bool(d.get('ready',True))
                await broadcast(room,room_state(room))
            elif op=='car' and room and not room.started:
                try:player.car=max(0,min(4,int(d.get('car',0))))
                except:continue
                player.ready=False
                await broadcast(room,room_state(room))
            elif op=='start' and room and ws is room.host and not room.started:
                if len(room.players)<2 or not all(p.ready for p in room.players.values()):
                    await send(ws,{'type':'error','message':'Servono almeno due giocatori e tutti pronti.'});continue
                room.started=True
                members=room_state(room)['members']
                await broadcast(room,{'type':'race_start','members':members,'capacity':room.capacity,'code':room.code,'mode':'race'})
            elif op=='input' and room and room.started and ws is not room.host:
                now=time.monotonic()
                if now-player.last_input<.027:continue  # 37 Hz max
                player.last_input=now
                try:steer=max(-1,min(1,float(d.get('steer',0))))
                except:steer=0
                if not -1<=steer<=1:steer=0
                await send(room.host,{'type':'remote_input','slot':player.slot,'steer':steer,'gas':bool(d.get('gas',True)),'brake':bool(d.get('brake',False))})
            elif op=='action' and room and room.started and ws is not room.host and d.get('action')=='item':
                await send(room.host,{'type':'remote_action','slot':player.slot,'action':'item'})
            elif op=='snapshot' and room and room.started and ws is room.host:
                now=time.monotonic()
                if now-room.last_frame<.035:continue
                room.last_frame=now
                state=d.get('state')
                if not isinstance(state,dict) or len(json.dumps(state))>18000:continue
                await broadcast(room,{'type':'snapshot','state':state},exclude=ws)
            elif op=='finish' and room and room.started and ws is room.host:
                await broadcast(room,{'type':'finish','time':d.get('time',0),'results':d.get('results',[])},exclude=ws)
            elif op=='leave':
                await leave(ws)
            else:
                await send(ws,{'type':'error','message':'Operazione non valida in questo stato.'})
    finally:
        await leave(ws)
    return ws

async def health(_):
    return web.json_response({'ok':True,'protocol':1,'rooms':len(ROOMS),'simulation':'host-authoritative-preview',
                              'online_modes':['race']})

async def cleanup(app):
    for r in list(ROOMS.values()):
        for p in r.players.values():
            await p.ws.close(message=b'server shutdown')
    ROOMS.clear()

app=web.Application(client_max_size=MAX_MSG)
app.router.add_get('/health',health)
app.router.add_get('/ws',handler)
app.on_cleanup.append(cleanup)
if __name__=='__main__':web.run_app(app,host='0.0.0.0',port=PORT)
