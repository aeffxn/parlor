"""Game rules and state transitions kept separate from HTTP handling."""
import random
import time

QUIZ = [
    {"q":"Which planet has the most moons currently confirmed?", "a":["Earth","Saturn","Mars","Venus"], "correct":1},
    {"q":"What is the chemical symbol for gold?", "a":["Ag","Gd","Au","Go"], "correct":2},
    {"q":"How many sides does a dodecagon have?", "a":["10","11","12","14"], "correct":2},
    {"q":"Which ocean is the largest?", "a":["Atlantic","Indian","Arctic","Pacific"], "correct":3},
    {"q":"What does the ‘HTTP’ in a web address stand for?", "a":["HyperText Transfer Protocol","High Tech Text Program","Home Tool Transfer Process","Hyperlink Type Terminal Page"], "correct":0},
    {"q":"Which instrument measures atmospheric pressure?", "a":["Hygrometer","Barometer","Anemometer","Seismograph"], "correct":1},
    {"q":"What is the smallest prime number?", "a":["0","1","2","3"], "correct":2},
    {"q":"Which artist painted The Starry Night?", "a":["Claude Monet","Vincent van Gogh","Pablo Picasso","Georgia O’Keeffe"], "correct":1},
    {"q":"What is the capital city of New Zealand?", "a":["Auckland","Christchurch","Wellington","Hamilton"], "correct":2},
    {"q":"In computing, what does ‘RAM’ stand for?", "a":["Random Access Memory","Readily Available Module","Rapid Array Machine","Run Access Mode"], "correct":0},
]
WORDS = [
    ("PIXEL", "A tiny square in a digital picture"), ("PLANET", "A world orbiting a star"),
    ("ARCADE", "A place full of cabinets and high scores"), ("ROCKET", "A speedy ride to space"),
    ("PUZZLE", "A problem made for solving"), ("GALAXY", "A huge neighborhood of stars"),
    ("JUNGLE", "A thick, tropical forest"), ("POCKET", "A small pouch sewn into clothes"),
    ("GUITAR", "A six-string instrument"), ("CANDLE", "A little light with a wick"),
]
TAKES = [
    {"q":"A hot dog is a sandwich.","a":["Absolutely","No chance"]},
    {"q":"The best pizza topping is pineapple.","a":["Absolutely","No chance"]},
    {"q":"A movie is better with subtitles.","a":["Absolutely","No chance"]},
    {"q":"Breakfast food is good at any time of day.","a":["Absolutely","No chance"]},
    {"q":"Board games are better than video games.","a":["Absolutely","No chance"]},
    {"q":"The middle seat gets the armrests.","a":["Absolutely","No chance"]},
]
LIST_CATEGORIES = ["Things you pack for a beach day", "Things that are louder than they need to be", "Foods you can eat with your hands", "Things found in a kitchen", "Fictional characters with a great outfit"]
GAMES = {
 "quickdraw": {"name":"Quickdraw", "tag":"REFLEXES", "description":"Wait for the flash. Beat the room.", "rules":"A signal arrives after a secret delay. Tap only after it turns green. Early taps are false starts; fastest valid reactions win."},
 "quiz": {"name":"Quiz Show", "tag":"TRIVIA", "description":"A little knowledge goes a long way.", "rules":"Pick the correct answer before the timer runs out. Correct answers score points, with a small bonus for being quick."},
 "word": {"name":"Word Rush", "tag":"WORDPLAY", "description":"Unjumble the word before the clock does.", "rules":"Unscramble the letters using your controller. The first correct answer scores; each player can score once per word."},
 "color": {"name":"Color Clash", "tag":"TERRITORY", "description":"Claim the board, one tile at a time.", "rules":"Take turns claiming any open tile. Each player gets one claim per turn. After 24 turns, the largest territory wins."},
 "meteor": {"name":"Meteor Run", "tag":"SURVIVAL", "description":"Move, dodge, and outlast the sky.", "rules":"Use the left and right buttons to steer your runner away from falling meteors. Stay alive for 35 seconds or be the last player standing."},
 "rps": {"name":"Rock Paper Scissors", "tag":"SHOWDOWN", "description":"Pick in secret. Reveal together.", "rules":"Choose rock, paper, or scissors before the clock runs out. Score for every opponent you beat when all picks are revealed."},
 "closest": {"name":"Closest Wins", "tag":"NUMBER GAME", "description":"Guess the hidden number. Get closest.", "rules":"Enter a whole number from 1 to 100. The closest guess takes the round; ties share the win."},
 "hottake": {"name":"Hot Take", "tag":"CROWD CHECK", "description":"Agree with the room or go your own way.", "rules":"Pick a side on a questionable opinion. The players on the less popular side score; a tied room scores together."},
 "listblitz": {"name":"List Blitz", "tag":"QUICK THINKING", "description":"Name three things. Avoid the same answers.", "rules":"Enter up to three answers that fit the category. Each answer nobody else repeats earns points."},
 "memory": {"name":"Memory Mix", "tag":"MEMORY", "description":"Watch the pattern, then repeat it.", "rules":"Watch the short sequence on the big screen, then tap the matching arrows in order. Complete it to score."},
}

class Game:
    def __init__(self, key, players):
        self.key, self.started = key, time.monotonic()
        self.players = {p["id"]: {"score": 0, "status":"waiting", "data":{}} for p in players}
        self.phase, self.round = "instructions", 1
        self.total_rounds = 3 if key in ("quickdraw", "quiz", "word", "rps", "hottake") else 1
        self.message, self.deadline, self.events = "Read the rules, then ready up.", 0, []
        self.message = "Read the rules, then ready up."
    def _setup_round(self):
        now = time.monotonic()
        self.started = now
        for p in self.players.values(): p["data"] = {}
        if self.key == "quickdraw":
            self.signal_at = now + random.uniform(3.2, 6.2)
            self.phase, self.deadline = "waiting", self.signal_at + 6
            self.message = "Hold steady… the signal is a surprise."
        elif self.key == "quiz":
            q = random.choice(QUIZ); self.question = q
            self.phase, self.deadline, self.message = "active", now + 16, "Lock in your answer."
        elif self.key == "word":
            self.answer, self.hint = random.choice(WORDS)
            chars = list(self.answer)
            while "".join(chars) == self.answer: random.shuffle(chars)
            self.scramble = "".join(chars)
            self.phase, self.deadline, self.message = "active", now + 24, "First correct answer gets the points."
        elif self.key == "color":
            self.board, self.turn, self.turn_limit = [None]*36, 0, 24
            self.phase, self.deadline, self.message = "active", now + 1000, "Take turns. Choose any open tile."
            self.turn_order = list(self.players)
            self._color_turn()
        elif self.key == "meteor":
            self.phase, self.deadline = "active", now + 35
            self.hazards, self.last_spawn = [], now
            for i, pid in enumerate(self.players): self.players[pid]["data"] = {"x": (i+1)/(len(self.players)+1), "alive": True, "survival": 0}
            self.message = "Stay in the gaps. Last runner standing wins."
        elif self.key == "rps":
            self.phase, self.deadline, self.message = "active", now + 18, "Choose in secret. Picks reveal together."
        elif self.key == "closest":
            self.target = random.randint(1, 100)
            self.phase, self.deadline, self.message = "active", now + 25, "Guess a whole number from 1 to 100."
        elif self.key == "hottake":
            self.take = random.choice(TAKES)
            self.phase, self.deadline, self.message = "active", now + 20, "Pick a side. The minority takes the points."
        elif self.key == "listblitz":
            self.category = random.choice(LIST_CATEGORIES)
            self.phase, self.deadline, self.message = "active", now + 35, "List up to three answers. Unique answers score."
        elif self.key == "memory":
            self.pattern = [random.choice(("up", "right", "down", "left")) for _ in range(5)]
            self.phase, self.deadline, self.message = "memorize", now + 4, "Watch the big screen. The pattern is coming."
    def _color_turn(self):
        active = self.turn_order[self.turn % len(self.turn_order)] if self.turn_order else None
        self.active_player = active
        self.message = "Take turns claiming open tiles."
    def ready(self, pid):
        if self.phase != "instructions": return
        self.players[pid]["status"] = "ready"
        if all(p["status"] == "ready" for p in self.players.values()): self._setup_round()
    def input(self, pid, action, value, player_names):
        if pid not in self.players or self.phase in ("instructions", "results"): return
        now = time.monotonic(); p = self.players[pid]
        if self.key == "quickdraw" and action == "tap":
            if p["data"].get("done"): return
            p["data"]["done"] = True
            if self.phase == "waiting" and now < self.signal_at:
                p["data"].update(false_start=True, reaction=None); p["status"] = "false start"
            elif self.phase == "waiting":
                self.phase = "signal"; self.signal_at = now
                p["data"]["reaction"] = 0; p["status"] = "finished"
            else:
                p["data"]["reaction"] = round((now-self.signal_at)*1000); p["status"] = "finished"
        elif self.key == "quiz" and action == "answer" and not p["data"].get("answered"):
            try: choice = int(value)
            except (ValueError, TypeError): return
            if not 0 <= choice < len(self.question["a"]): return
            p["data"].update(answered=True, correct=choice == self.question["correct"])
            if p["data"]["correct"]: p["score"] += 100 + max(0, int((self.deadline-now)*3))
        elif self.key == "word" and action == "guess" and not p["data"].get("solved"):
            guess = str(value)[:20].strip().upper()
            if guess and guess == self.answer:
                p["data"]["solved"] = True; p["score"] += 100 + max(0, int((self.deadline-now)*2)); p["status"] = "solved"
        elif self.key == "color" and action == "claim" and self.phase == "active":
            try: tile = int(value)
            except (ValueError, TypeError): return
            if pid != self.active_player or not 0 <= tile < len(self.board) or self.board[tile] is not None: return
            self.board[tile] = pid; self.turn += 1; self.players[pid]["score"] += 1
            self._color_turn()
            if self.turn >= self.turn_limit: self.finish(player_names)
        elif self.key == "meteor":
            d = p["data"]
            if not d.get("alive"): return
            if action in ("left", "right"):
                d["x"] = max(.04, min(.96, d["x"] + (-.07 if action == "left" else .07)))
        elif self.key == "rps" and action == "rps" and value in ("rock", "paper", "scissors") and "choice" not in p["data"]:
            p["data"]["choice"] = value
        elif self.key == "closest" and action == "number" and "guess" not in p["data"]:
            try: guess = int(value)
            except (ValueError, TypeError): return
            if 1 <= guess <= 100: p["data"]["guess"] = guess
        elif self.key == "hottake" and action == "vote" and value in (0, 1) and "vote" not in p["data"]:
            p["data"]["vote"] = int(value)
        elif self.key == "listblitz" and action == "list" and "submitted" not in p["data"]:
            answers = [" ".join(str(item).split())[:30] for item in str(value or "").split(",")[:3]]
            answers = [answer for answer in answers if answer]
            if answers:
                p["data"].update(answers=answers, submitted=True)
        elif self.key == "memory" and action == "pattern" and self.phase == "active" and not p["data"].get("failed") and not p["data"].get("complete"):
            try: index = int(value)
            except (ValueError, TypeError): return
            arrows = ("up", "right", "down", "left")
            if not 0 <= index < len(arrows): return
            inputs = p["data"].setdefault("inputs", [])
            position = len(inputs)
            if arrows[index] != self.pattern[position]:
                p["data"]["failed"] = True
            else:
                inputs.append(arrows[index])
                if len(inputs) == len(self.pattern):
                    p["data"]["complete"] = True
                    p["score"] += 250
    def update(self, player_names):
        now = time.monotonic()
        if self.phase == "waiting" and now >= self.signal_at:
            self.phase, self.signal_at = "signal", now
            self.message = "GO! Tap now."
        if self.key == "memory" and self.phase == "memorize" and now >= self.deadline:
            self.phase, self.deadline, self.message = "active", now + 25, "Repeat the pattern on your controller."
        if self.key == "meteor" and self.phase == "active":
            if now-self.last_spawn > max(.34, 1.05-(now-self.started)/48):
                self.hazards.append({"x":random.random(), "y":0, "speed":random.uniform(.24,.38)+(now-self.started)*.002}); self.last_spawn=now
            dt = min(.12, max(0, now-getattr(self,"last_update",now))); self.last_update=now
            for h in self.hazards: h["y"] += h["speed"]*dt
            self.hazards = [h for h in self.hazards if h["y"] < 1.05]
            for pid, p in self.players.items():
                d=p["data"]
                if d.get("alive"):
                    d["survival"] = round(now-self.started,1)
                    if any(abs(h["x"]-d["x"])<.055 and .83<h["y"]<.96 for h in self.hazards): d["alive"]=False; p["status"]="out"
            alive=sum(1 for p in self.players.values() if p["data"].get("alive"))
            if (len(self.players)>1 and alive<=1) or now>=self.deadline: self.finish(player_names)
        elif self.phase in ("active","signal") and now >= self.deadline: self.finish(player_names)
        if self.phase == "active" and self.key in ("rps", "closest", "hottake", "listblitz"):
            field = {"rps":"choice", "closest":"guess", "hottake":"vote", "listblitz":"submitted"}[self.key]
            if self.players and all(field in p["data"] for p in self.players.values()): self.finish(player_names)
    def finish(self, player_names):
        if self.phase == "results": return
        if self.key == "quickdraw":
            times = sorted((p["data"].get("reaction") for p in self.players.values() if p["data"].get("reaction") is not None))
            for p in self.players.values():
                t=p["data"].get("reaction")
                if t is not None and t > 0: p["score"] += max(10, 500-(times.index(t)*100))
        if self.key == "color":
            for i, pid in enumerate(self.turn_order):
                count = self.board.count(pid); self.players[pid]["data"]["territory"] = count
                self.players[pid]["score"] += count*5
        if self.key == "meteor":
            for p in self.players.values(): p["score"] += int(p["data"].get("survival",0)*10)
        if self.key == "rps":
            beats = {"rock":"scissors", "paper":"rock", "scissors":"paper"}
            for pid, player in self.players.items():
                choice = player["data"].get("choice")
                wins = sum(1 for other in self.players.values() if choice and other["data"].get("choice") == beats[choice])
                player["score"] += wins * 100
                player["data"]["wins"] = wins
        if self.key == "closest":
            guesses = [(abs(p["data"]["guess"]-self.target), pid) for pid,p in self.players.items() if "guess" in p["data"]]
            if guesses:
                best = min(distance for distance,_ in guesses)
                for distance,pid in guesses:
                    if distance == best: self.players[pid]["score"] += 250
                for p in self.players.values():
                    if "guess" in p["data"]: p["data"]["distance"] = abs(p["data"]["guess"]-self.target)
        if self.key == "hottake":
            counts = [sum(1 for p in self.players.values() if p["data"].get("vote") == choice) for choice in (0,1)]
            for p in self.players.values():
                vote=p["data"].get("vote")
                if vote is not None and (sum(counts) < 2 or counts[0] == counts[1] or vote == (0 if counts[0] < counts[1] else 1)): p["score"] += 100
                p["data"]["crowd"] = counts[p["data"].get("vote",0)] if "vote" in p["data"] else 0
        if self.key == "listblitz":
            counts = {}
            for p in self.players.values():
                for answer in p["data"].get("answers",[]): counts[answer.casefold()] = counts.get(answer.casefold(),0)+1
            for p in self.players.values():
                unique = sum(1 for answer in p["data"].get("answers",[]) if counts[answer.casefold()] == 1)
                p["data"]["unique"] = unique
                p["score"] += unique * 100
        self.phase, self.message = "results", "Round over. See how the room stacked up."
    def public(self, player_names):
        now=time.monotonic()
        data={"phase":self.phase,"round":self.round,"total_rounds":self.total_rounds,"message":self.message,"scores":{pid:p["score"] for pid,p in self.players.items()},"players":{pid:{**p["data"],"status":p["status"]} for pid,p in self.players.items()},"remaining":max(0, round(self.deadline-now,1))}
        if self.key=="quickdraw": data.update(signal=getattr(self,"phase","")=="signal")
        if self.key=="quiz" and hasattr(self,"question"): data.update(question={"q":self.question["q"],"a":self.question["a"]})
        if self.key=="word" and hasattr(self,"scramble"): data.update(scramble=self.scramble,hint=self.hint)
        if self.key=="color" and hasattr(self,"board"): data.update(board=self.board,turn=self.turn,turn_limit=self.turn_limit,active_player=self.active_player,active_player_name=player_names.get(self.active_player,""))
        if self.key=="meteor" and hasattr(self,"hazards"): data.update(hazards=self.hazards)
        if self.key=="rps": data["reveal"] = self.phase == "results"
        if self.key=="closest" and self.phase == "results": data["target"] = self.target
        if self.key=="hottake" and hasattr(self,"take"):
            data["prompt"] = self.take
            if self.phase == "results": data["votes"] = [sum(1 for p in self.players.values() if p["data"].get("vote")==choice) for choice in (0,1)]
        if self.key=="listblitz" and hasattr(self,"category"): data["category"] = self.category
        if self.key=="memory" and hasattr(self,"pattern") and self.phase == "memorize": data["pattern"] = self.pattern
        return data
