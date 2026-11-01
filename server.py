"""Start Parlor with: python server.py [--port 8765]"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse, json, secrets, socket, threading, time, urllib.parse, webbrowser
from parlor.games.catalog import Game, GAMES

ROOT=Path(__file__).resolve().parent
CODE_CHARS="ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
class Room:
    def __init__(self):
        self.code="".join(secrets.choice(CODE_CHARS) for _ in range(4))
        self.host_token=secrets.token_urlsafe(24); self.players={}; self.game=None
        self.lock=threading.RLock(); self.last_event="Room is ready."
    def clean(self):
        now=time.time()
        for pid,p in list(self.players.items()):
            if now-p["seen"]>90: del self.players[pid]
        if self.game:
            names={pid:p["name"] for pid,p in self.players.items()}
            self.game.players={pid:v for pid,v in self.game.players.items() if pid in self.players}
            if self.game.key=="color" and self.game.phase=="active":
                self.game.turn_order=[pid for pid in self.game.turn_order if pid in self.players]
                if self.game.turn_order: self.game._color_turn()
            self.game.update(names)
    def join(self, code, name, token=None):
        with self.lock:
            self.clean()
            if str(code).upper()!=self.code: raise ValueError("That room code doesn’t match. Check the host screen.")
            name=" ".join(str(name).split())[:18]
            if not name: raise ValueError("Add a name before joining.")
            if token and token in self.players:
                p=self.players[token]; p["seen"]=time.time(); return token,p
            if self.game and self.game.phase!="results": raise ValueError("A round is underway. Ask the host to return to the lobby.")
            if len(self.players)>=8: raise ValueError("This room is full (8 players max).")
            pid=secrets.token_urlsafe(18)
            used={p["name"].casefold() for p in self.players.values()}
            base=name; n=2
            while name.casefold() in used:
                suffix=f" {n}"; name=base[:18-len(suffix)]+suffix; n+=1
            p={"id":pid,"name":name,"color":len(self.players)%8,"seen":time.time(),"status":"connected"}
            p["last_input"]=0.0
            self.players[pid]=p; self.last_event=f"{name} joined the room."; return pid,p
    def state(self):
        with self.lock:
            self.clean()
            players=[{k:v for k,v in p.items() if k!="seen"} for p in self.players.values()]
            return {"code":self.code,"players":players,"game":self.game.key if self.game else None,"gameState":self.game.public({p["id"]:p["name"] for p in self.players.values()}) if self.game else None,"event":self.last_event}
    def host_action(self, action, body):
        with self.lock:
            self.clean(); names={pid:p["name"] for pid,p in self.players.items()}
            if action=="start":
                key=body.get("game")
                if key not in GAMES: raise ValueError("Choose one of the available games.")
                if not self.players: raise ValueError("At least one player needs to join first.")
                self.game=Game(key,list(self.players.values())); self.last_event=f"{GAMES[key]['name']} is starting."
            elif action=="lobby": self.game=None; self.last_event="Back in the lobby. Choose another game."
            elif action=="restart":
                if not self.game: raise ValueError("There is no round to restart.")
                old=self.game; self.game=Game(old.key,list(self.players.values())); self.game.round=old.round
                for pid,p in self.game.players.items(): p["score"]=old.players.get(pid,{}).get("score",0)
                self.last_event="Round restarted."
            elif action=="next":
                if not self.game or self.game.phase!="results": raise ValueError("The current round is not finished.")
                if self.game.round>=self.game.total_rounds: self.game=None; self.last_event="Game complete. Back in the lobby."
                else:
                    old=self.game; self.game=Game(old.key,list(self.players.values())); self.game.round=old.round+1
                    for pid,p in self.game.players.items(): p["score"]=old.players.get(pid,{}).get("score",0)
                    self.last_event=f"Round {self.game.round} is up."
            else: raise ValueError("Unknown host action.")
    def player_action(self, pid, action, value):
        with self.lock:
            self.clean()
            if pid not in self.players: raise ValueError("Session expired. Rejoin with your name.")
            self.players[pid]["seen"]=time.time()
            if not self.game: raise ValueError("The host has not started a game yet.")
            if action=="ready": self.game.ready(pid); return
            if action not in {"tap","answer","guess","claim","left","right"}: raise ValueError("That controller action is not allowed.")
            now=time.monotonic()
            if now-self.players[pid]["last_input"]<.045: raise ValueError("Easy there — give the controller a moment.")
            self.players[pid]["last_input"]=now
            self.game.input(pid,action,value,{i:p["name"] for i,p in self.players.items()})

ROOM=Room()
def host_is_authorized(candidate):
    return isinstance(candidate,str) and candidate.isascii() and secrets.compare_digest(candidate,ROOM.host_token)
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/"web"),**kwargs)
    def log_message(self,fmt,*args): pass
    def send_json(self, obj, status=200):
        data=json.dumps(obj).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(data)
    def body(self):
        size=min(int(self.headers.get("Content-Length","0")),4096)
        return json.loads(self.rfile.read(size) or b"{}")
    def do_GET(self):
        parsed=urllib.parse.urlparse(self.path)
        if parsed.path in ("/","/host"):
            if not self.client_address[0].startswith("127.") and self.client_address[0]!="::1":
                self.send_response(302); self.send_header("Location","/controller.html"); self.end_headers(); return
            data=(ROOT/"web"/"host.html").read_text(encoding="utf-8").replace("__HOST_TOKEN__",ROOM.host_token).encode()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(data); return
        if parsed.path=="/api/config":
            host=f"http://{lan_ip()}:{self.server.server_port}"
            return self.send_json({"host":host,"code":ROOM.code,"games":GAMES})
        if parsed.path=="/api/state":
            q=urllib.parse.parse_qs(parsed.query); role=q.get("role",[""])[0]
            if role=="host" and not host_is_authorized(q.get("key",[""])[0]): return self.send_json({"error":"Host session expired."},403)
            if role=="player":
                pid=q.get("id",[""])[0]
                with ROOM.lock:
                    if pid not in ROOM.players: return self.send_json({"error":"Session expired."},401)
                    ROOM.players[pid]["seen"]=time.time()
            return self.send_json(ROOM.state())
        return super().do_GET()
    def do_POST(self):
        route=urllib.parse.urlparse(self.path).path
        try:
            body=self.body()
            if route=="/api/join":
                pid,p=ROOM.join(body.get("code"),body.get("name"),body.get("token"))
                return self.send_json({"id":pid,"token":pid,"name":p["name"]})
            if route.startswith("/api/host/"):
                if not host_is_authorized(body.get("key")): return self.send_json({"error":"Host session expired."},403)
                ROOM.host_action(route.rsplit("/",1)[-1],body); return self.send_json({"ok":True})
            if route=="/api/input":
                ROOM.player_action(str(body.get("id","")),str(body.get("action","")),body.get("value")); return self.send_json({"ok":True})
            return self.send_json({"error":"Unknown endpoint."},404)
        except (ValueError,TypeError,json.JSONDecodeError) as e: return self.send_json({"error":str(e)},400)
        except Exception as e: return self.send_json({"error":"Couldn’t process that request."},500)
def lan_ip():
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try: sock.connect(("192.0.2.1",80)); return sock.getsockname()[0]
    except OSError: return "127.0.0.1"
    finally: sock.close()
def main():
    parser=argparse.ArgumentParser(description="Host a Parlor game night on your local network")
    parser.add_argument("--port",type=int,default=8765); args=parser.parse_args()
    httpd=ThreadingHTTPServer(("0.0.0.0",args.port),Handler)
    ip=lan_ip(); print("\n  PARLOR // ROOM READY\n  -------------------------\n  Host screen: http://localhost:%d\n  Join on Wi-Fi: http://%s:%d\n  Room code: %s\n  Keep this terminal open. Ctrl+C ends the session.\n"%(args.port,ip,args.port,ROOM.code))
    webbrowser.open(f"http://localhost:{args.port}")
    try: httpd.serve_forever()
    except KeyboardInterrupt: print("\nParlor session closed.")
    finally: httpd.server_close()
if __name__=="__main__": main()

