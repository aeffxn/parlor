import json, sys, time, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Room, ROOM, host_is_authorized
from parlor.games.catalog import Game, GAMES

def player(pid, name): return {"id":pid,"name":name,"color":0,"seen":time.time(),"status":"connected"}
def begin(game):
    for pid in list(game.players): game.ready(pid)
    return game

class RoomTests(unittest.TestCase):
    def setUp(self): self.room=Room()
    def test_code_validation_and_name_validation(self):
        with self.assertRaisesRegex(ValueError,"code"): self.room.join("NOPE","Ada")
        with self.assertRaisesRegex(ValueError,"name"): self.room.join(self.room.code,"  ")
        pid,p=self.room.join(self.room.code,"Ada"); self.assertEqual(p["name"],"Ada")
    def test_unique_names_limit_and_reconnect(self):
        first,p=self.room.join(self.room.code,"Ada")
        again,p2=self.room.join(self.room.code,"Different name",first)
        self.assertEqual(first,again); self.assertEqual(p2["name"],"Ada")
        second,p=self.room.join(self.room.code,"Ada")
        self.assertEqual(p["name"],"Ada 2")
        for i in range(6): self.room.join(self.room.code,"Guest"+str(i))
        with self.assertRaisesRegex(ValueError,"full"): self.room.join(self.room.code,"Late")
    def test_sessions_are_removed_after_timeout(self):
        pid,_=self.room.join(self.room.code,"Ada"); self.room.players[pid]["seen"]-=100
        self.assertEqual(self.room.state()["players"],[])
    def test_game_changes_and_score_carry_forward(self):
        pid,_=self.room.join(self.room.code,"Ada")
        self.room.host_action("start",{"game":"quiz"}); self.assertEqual(self.room.game.phase,"instructions")
        self.room.game.players[pid]["score"]=125
        self.room.host_action("restart",{}); self.assertEqual(self.room.game.players[pid]["score"],125)
        with self.assertRaisesRegex(ValueError,"available games"): self.room.host_action("start",{"game":"fake"})
    def test_unknown_player_and_input_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"Session expired"): self.room.player_action("nope","tap",None)
        pid,_=self.room.join(self.room.code,"Ada"); self.room.host_action("start",{"game":"quickdraw"})
        with self.assertRaisesRegex(ValueError,"not allowed"): self.room.player_action(pid,"change_score",999)
    def test_host_management_key_is_required(self):
        self.assertTrue(host_is_authorized(ROOM.host_token))
        self.assertFalse(host_is_authorized("wrong-key"))
        self.assertFalse(host_is_authorized(None))
    def test_rapid_inputs_are_rate_limited(self):
        pid,_=self.room.join(self.room.code,"Ada");self.room.host_action("start",{"game":"quiz"})
        self.room.player_action(pid,"ready",None);answer=self.room.game.question["correct"]
        self.room.player_action(pid,"answer",answer)
        with self.assertRaisesRegex(ValueError,"moment"): self.room.player_action(pid,"answer",answer)
    def test_stale_player_is_removed_during_a_round(self):
        pid,_=self.room.join(self.room.code,"Ada");self.room.host_action("start",{"game":"quiz"})
        self.room.players[pid]["seen"]-=100
        self.assertEqual(self.room.state()["players"],[])
        self.assertNotIn(pid,self.room.game.players)

class GameTests(unittest.TestCase):
    def game(self,key,n=2): return Game(key,[player("p"+str(i),"Player "+str(i)) for i in range(n)])
    def test_quickdraw_false_start_and_valid_reaction(self):
        g=begin(self.game("quickdraw")); g.signal_at=time.monotonic()+10
        g.input("p0","tap",None,{})
        self.assertTrue(g.players["p0"]["data"]["false_start"])
        g.phase="signal";g.signal_at=time.monotonic()-.15
        g.input("p1","tap",None,{})
        self.assertGreaterEqual(g.players["p1"]["data"]["reaction"],100)
        g.finish({}); self.assertGreater(g.players["p1"]["score"],0)
    def test_quiz_validates_answer_and_scores_correct_choice(self):
        g=begin(self.game("quiz"));q=g.question
        g.input("p0","answer",q["correct"],{})
        g.input("p0","answer",(q["correct"]+1)%4,{})
        self.assertTrue(g.players["p0"]["data"]["correct"])
        self.assertGreater(g.players["p0"]["score"],99)
        before=g.players["p1"]["score"];g.input("p1","answer",99,{})
        self.assertEqual(g.players["p1"]["score"],before)
    def test_word_correct_answer_scores_once(self):
        g=begin(self.game("word"));g.input("p0","guess","wrong",{})
        self.assertNotIn("solved",g.players["p0"]["data"])
        g.input("p0","guess",g.answer,{})
        score=g.players["p0"]["score"];g.input("p0","guess",g.answer,{})
        self.assertTrue(g.players["p0"]["data"]["solved"]);self.assertEqual(score,g.players["p0"]["score"])
    def test_color_clash_turns_and_claim_limit(self):
        g=begin(self.game("color"));g.input("p1","claim",0,{})
        self.assertIsNone(g.board[0]);g.input("p0","claim",0,{})
        self.assertEqual(g.board[0],"p0");g.input("p1","claim",0,{})
        self.assertEqual(g.turn,1)
        for i in range(1,24):
            pid=g.active_player;g.input(pid,"claim",i,{})
        self.assertEqual(g.phase,"results");self.assertEqual(g.turn,24)
    def test_meteor_bounds_collision_and_round_end(self):
        g=begin(self.game("meteor",2));x=g.players["p0"]["data"]["x"]
        g.input("p0","left",None,{})
        self.assertLess(g.players["p0"]["data"]["x"],x)
        g.players["p0"]["data"]["x"]=.5;g.hazards=[{"x":.5,"y":.9,"speed":0}]
        g.last_update=time.monotonic();g.update({})
        self.assertFalse(g.players["p0"]["data"]["alive"])
        self.assertEqual(g.phase,"results")
    def test_single_meteor_runner_gets_the_full_survival_round(self):
        g=begin(self.game("meteor",1));g.update({})
        self.assertEqual(g.phase,"active")
        g.deadline=time.monotonic()-1;g.update({})
        self.assertEqual(g.phase,"results")
    def test_all_catalog_games_have_playable_rules(self):
        self.assertEqual(set(GAMES),{"quickdraw","quiz","word","color","meteor"})
        for key in GAMES:self.assertTrue(GAMES[key]["rules"])

if __name__=="__main__": unittest.main(verbosity=2)

