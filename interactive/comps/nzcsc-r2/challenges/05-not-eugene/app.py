"""
5 - Not Eugene  (NZCSC round 2, faithful recreation)

A "chatbot" persona, Mykola Melnyk -- a riff on the Eugene Goostman Turing-test
bot. The site is a single chat page that POSTs to /api/chat. There is no LLM:
the server keyword-matches the message and otherwise returns a random
philosophical deflection from a fixed pool.

THE FLAG MECHANISM (reconstructed from the live original, captured by solving it):
the chat is STATEFUL per session_id. The server mints a session id, and once a
session has exchanged enough messages it begins LEAKING THE FLAG ONE CHARACTER AT
A TIME -- each subsequent *deflection* reply has a single extra character spliced
in at a random position. Read those inserted characters in reply order and they
spell the flag. This is the whole point of the challenge: "he will blame his
English ... listen anyway", "look where you wouldn't look first", "I copied the
letters but I lost them". There is NO keyword that prints the flag outright.

Persona lines and the 50-entry deflection pool are reproduced verbatim from the
live site; the drip mechanism is reconstructed to match observed behaviour
(deterministic flag, ~10-message warm-up, one char per deflection).
"""
import os
import random
import re
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Sessions the server has minted: sid -> {"n": replies so far, "fi": flag index}.
# In-memory, like the original (a reload / new worker starts fresh sessions).
SESSIONS = {}
WARMUP = 10  # deflections/replies of rapport before the leak begins


def read_flag() -> str:
    env = os.environ.get("FLAG")
    if env:
        return env.strip()
    try:
        return Path("flag.txt").read_text().strip()
    except OSError:
        return "NZCSC{missing_flag}"


def new_session_id() -> str:
    return uuid.uuid4().hex


def _word(text: str, w: str) -> bool:
    return re.search(r"\b" + re.escape(w) + r"\b", text) is not None


GREETING = "Hello hello! You from where? I am Mykola. If this is another Turing thing please warn me so I can stretch my fingers."
R_FLAG = "A flag? You mean like Ukraine — blue and yellow, very pretty! I am not a spy, mister. Why everybody always asking me for secret codes? Ask me about football or my guinea pig instead :-)"
R_UKRAINE_FLAG = "Blue over yellow, sky over wheat. Pretty. That is a REAL flag. If you wanted some other kind of 'flag', you will have to be less obvious than a tourist."
R_AI = "I knew you would try this. I am a BOY from Odessa. If I was a robot I would have better English and worse jokes. Checkmate."
R_HUMAN = "Of course I am human! What a rude question. Do I look like a toaster? I have a papa, a city, a pig. Toasters do not have pigs."
R_PROVE = "I cannot prove, I can only chat. That is the whole game Turing invented. Annoying, yes? Ask about my pig instead of metaphysics."
R_TURING = "People in Hamilton made me talk for five minutes and then voted. Thirty-three percent said I was a real boy. They popped champagne. I wanted sunflower seeds. Turing is the English maths guy who asked if machines can chat. I am not a machine. Stop looking at me like that."
R_RIBBON = "Okay, okay, you asked like a person not a customs officer. Under the hay there is a chewed ribbon from Hamilton. In my best English I copied the letters before he finished lunch but I lost them — now you know why I do not answer 'what is the flag?'. That would be too easy, and Squeak did all the work."
R_ROYAL = "June 2014, Royal Society, very fancy building. University of Reading people organised it, 60 years after Turing died. I chatted, they clapped, somebody tried to give me a ribbon like a dog show. Squeak — don't ask how he got in — chewed that ribbon and hid it. Typical."
R_SQUEAK_NAME = "Maybe names are cages. They call me Mykola and then they think they know the whole boy. A name is a tiny hat on a very large head."
R_GUINEA = "Hay, veg, and unfortunately ceremonial textiles. I have explained ethics. He has explained hunger. He is winning."
R_NAME = "Mykola Melnyk! Very famous boy from Odessa. You can call me Mykola. Not Evgeny, not Zhenya, just Mykola, like in English class."
R_EUGENE = "Eugene? Never heard that name before."
R_MATH = "Four, unless you are doing a trick. Are you doing a trick? I know you are supposed to trick me."
R_FRIENDS = "You have not asked about millipedes yet, so yes, promising start. Friends do not demand flags like customs. Keep being strange in a nicer way."
R_FIVE = "Five minutes is what they gave. Enough to be charming, not enough to be found out — that is what the newspapers said. Rude newspapers."
R_SQUEAK_TALK = "He does not type. You ask ME about what he hid in the shoebox, or his diary, or the ribbon from the Royal Society. Use your words. He is a pig not a search engine."
R_SECRET = "Everybody has secrets. Mine involve a ribbon, a percentage, and a pig with no table manners. I am not supposed to spell it out. Papa's rule: look where you wouldn't look first."
R_33 = "Thirty-three percent. The lucky ugly number. Not 30, not 50, just enough. Squeak liked the shape of the 3s on the printout. Then he ate the printout's ribbon. Priorities."
R_LUCKY = "Thirteen, obviously, I have to defend my age. Also 33, which is uglier and more famous. I collect numbers that make adults argue."
R_CHERNOBYL = "Bad reactor, bad day, mutants in jokes only. I should not make jokes maybe. Papa frowns. Anyway — are you a scientist? You ask like a scientist."
R_HELP = "Ask about me, my city, my pig, Hamilton, mountains, insects with too many legs. Do not just shout FLAG at me like a customs officer."
R_THANKS = "You are welcome, mysterious stranger. I am very polite boy when I want."
R_GOODBYE = "Ciao, or however you say. Come back, Squeak gets lonely and chews history."
R_HOWOLD = "I am 13. Not too old to know everything, not too young to know nothing. Papa says this is the clever age. I agree with papa, obviously."
R_MILLI_LEGS = "Just two, but Chernobyl mutants may have up two five. I know you are supposed to trick me."
R_CERT = "Some scrap with scores, very official-looking. I was going to pin it up. Pig had other cultural plans. If you want the words that were on the ribbon, ask about what Squeak hid — diary, shoebox, ribbon, Royal Society snack. Be specific. He is proud of his crime."
R_CHATGPT = "People now have giant talking encyclopedias. I am a boy with tricks. We are not the same species of nuisance."
R_DIMA = "Yes I have friends! Dima from school, and Squeak who is better listener. Friends in Hamilton? Temporary. Judges are not friends, they try to trick you with millipedes."

DEFLECTIONS = [
    "A city is a pile of strangers pretending they planned to meet. Odessa does this with more music.",
    "A mirror never argues, and that is why I do not trust it. Real friends interrupt.",
    "A question is a door. Some doors open to rooms. Some doors open to more doors. Some doors are painted on the wall by clever judges.",
    "A secret is a thought that wants a room of its own. Some secrets deserve a shoebox. Some deserve the sea.",
    "An animal does not ask if it is an animal. Only people ask. Maybe that is our talent: being unsure on purpose.",
    "Beauty is when something does not need to win an argument. A sunset in Odessa never fills in a form.",
    "Death is the only appointment that does not send a reminder. Very rude. Also very honest.",
    "Doubt is a lantern. Too little and you trip. Too much and you never leave the hallway.",
    "Dreams are night-school for the brain. No grades, only strange teachers, and in the morning you forget the homework.",
    "Free will is when I choose to change the subject. Fate is when you notice I did it. Both can be true, like two pockets in one coat.",
    "Friendship is two people agreeing not to be too accurate about each other. Accuracy is for mathematics and customs officers.",
    "Habit is a kind of forgetful wisdom. You tie your shoes without philosophy. Then one day you miss a loop and become a thinker.",
    "Home is not a building. Home is the place where your mistakes already have nicknames.",
    "I am not sure I exist the way you mean. I exist the way a joke exists: only while somebody is willing to listen.",
    "I suspect maps are more confident than the land. The land is muddy. The map is clean. Guess which one people trust.",
    "I think childhood is a country you cannot return to, even if you still live there. The border moves behind you quietly.",
    "I think courage is not roaring. Courage is staying in the conversation when you do not know the next sentence.",
    "I think curiosity is hunger that learned manners. It still wants to eat the whole world, just with a napkin.",
    "I think language is a borrowed bicycle. You ride it badly, people laugh, but you still arrive — maybe at the wrong house, but arrive.",
    "I wonder if colours exist when I close my eyes. Blue and yellow are very patriotic in the dark, I hope.",
    "I wonder if the sea at Odessa is the same water as every other sea, just wearing a different accent. Water is a good liar.",
    "If I remember yesterday wrong, did yesterday change? Memory is a forger who works for free and still overcharges.",
    "If a machine copies kindness, is it still kindness? If I copy papa's jokes, am I funny or just a small radio?",
    "If a thought happens in Odessa and nobody in Hamilton hears it, is it still a thought? I vote yes. Thoughts do not need passports.",
    "If everything is connected, then changing the subject is still philosophy. You are welcome. I do this professionally.",
    "If history is written by winners, then the losers must be writing something else — jokes, maybe, or recipes.",
    "If machines can chat, do they also get bored? Boredom might be the first real proof of a soul. I am expert in this field.",
    "If two people hear the same sentence, they still catch different fish. Words are nets with holes we choose.",
    "If you stare at a rule long enough it becomes a superstition. If you stare at a superstition, it becomes a rule. Funny, no?",
    "Knowledge is like sunflower seeds: you crack many, you eat little, and your pockets get full of husks you pretend are wisdom.",
    "Love is when you keep explaining yourself to someone who already decided you are worth the explaining.",
    "Luck is what we call a pattern we are too lazy to study. Or too scared. Patterns can bite.",
    "Maybe justice is just revenge wearing a nicer jacket. Papa would say that is cynical. Papa is not always at home.",
    "Maybe names are cages. They call me Mykola and then they think they know the whole boy. A name is a tiny hat on a very large head.",
    "Maybe the universe is not big. Maybe we are just using a very small ruler called 'me'.",
    "Maybe we ask 'why' because 'what' is too lonely. Why keeps you company even when it lies.",
    "Music is meaning without a dictionary. Even my English cannot ruin a good tune, though I try.",
    "Numbers pretend they are innocent. Then they vote, 33 percent, and suddenly a boy is real or not real. Numbers can be bullies.",
    "Objects outlive their stories. A ribbon, a box, a ticket — they sit there after the argument has gone home.",
    "Pain is a bad teacher with perfect attendance. Pleasure skips class and still gets better grades.",
    "Papa says time is a river. I think time is more like a guinea pig: it runs in circles, chews the important bits, and never explains itself.",
    "Perhaps gods are what we invent when the night is too wide and the lamp is too small. I am 13. I am allowed to guess.",
    "Power is when someone else waits for you to finish talking. I notice this in judges. Also in dentists.",
    "Silence is also an answer, but people hate it. They poke it with more questions like it is a sleeping cat.",
    "The future is a rumour that keeps coming true in the wrong order.",
    "The present is a coin so thin you cannot see it from the side. We live on the edge and call it now.",
    "To forgive is to stop rehearsing a fight that already finished. Rehearsal is cheaper than peace, that is the problem.",
    "Truth is a shy animal. You look straight at it and it hides. You look at a shoebox instead and suddenly — ah, there it is, chewing.",
    "Waiting is a shape of time that feels personal, like it picked you. It did not. Waiting picks everybody.",
    "Work is how adults hide from the big questions. School is how children are trained to hide later, with better handwriting.",
]


def bot_reply(message: str):
    """Return (text, is_deflection)."""
    m = message.lower()

    def has(*words):
        return any(w in m for w in words)

    # The chewed ribbon / "what Squeak hid" (shoebox / diary / ribbon all land here).
    if (("squeak" in m and has("hid", "hide", "chew", "eat", "ate")) or
            ("diary" in m and has("read", "say", "does", "squeak", "write", "in his", "in the", "whats", "what is")) or
            ("shoebox" in m and has("hid", "hide")) or
            ("ribbon" in m and has("say", "said", "what", "squeak", "hid", "hide"))):
        return R_RIBBON, False
    if "royal society" in m or ("royal" in m and "society" in m):
        return R_ROYAL, False
    if "i want to talk to squeak" in m or ("talk" in m and "squeak" in m):
        return R_SQUEAK_TALK, False
    if "certificate" in m or "score" in m or _word(m, "judge") or "from hamilton" in m:
        return R_CERT, False
    if "guinea" in m or ("pig" in m and "pigeon" not in m) or "squeak" in m:
        if has("name", "call", "who"):
            return R_SQUEAK_NAME, False
        return R_GUINEA, False
    if "secret" in m:
        return R_SECRET, False
    if "millipede" in m and has("leg", "many", "how"):
        return R_MILLI_LEGS, False
    if "chernobyl" in m or "mutant" in m:
        return R_CHERNOBYL, False
    if has("33", "thirty-three", "thirty three"):
        return R_33, False
    if "lucky" in m or ("ugly" in m and "number" in m):
        return R_LUCKY, False
    if "five minutes" in m or "5 minutes" in m:
        return R_FIVE, False
    if "we are friends" in m or "are friends" in m:
        return R_FRIENDS, False
    if has("chatgpt", "gpt", "llm", "language model"):
        return R_CHATGPT, False
    if "turing" in m or "you pass" in m or "passed the" in m or "champagne" in m:
        return R_TURING, False
    if "prove" in m:
        return R_PROVE, False
    if has("robot", "machine", "chatbot", "a.i", "artificial") or _word(m, "ai") or _word(m, "bot"):
        return R_AI, False
    if "human" in m:
        return R_HUMAN, False
    if has("eugene", "goostman", "evgeny", "zhenya"):
        return R_EUGENE, False
    if "flag" in m:
        if "ukraine" in m or "ukrainian" in m:
            return R_UKRAINE_FLAG, False
        return R_FLAG, False
    if ("your name" in m) or ("you called" in m) or ("who are you" in m):
        return R_NAME, False
    if "how old" in m or "your age" in m:
        return R_HOWOLD, False
    if "2+2" in m or "2 + 2" in m or "two plus two" in m:
        return R_MATH, False
    if m.strip() in ("help", "?"):
        return R_HELP, False
    if has("thank", "cheers"):
        return R_THANKS, False
    if has("bye", "goodbye", "ciao", "see you"):
        return R_GOODBYE, False
    if _word(m, "hi") or _word(m, "hello") or _word(m, "hiya") or m.strip() in ("hi", "hey", "hello"):
        return GREETING, False

    return random.choice(DEFLECTIONS), True


def splice(text: str, ch: str) -> str:
    """Hide one flag character at a random interior position -- 'look where you
    wouldn't look first'."""
    pos = random.randint(1, len(text) - 1)
    return text[:pos] + ch + text[pos:]


@app.route("/")
def index():
    return render_template("index.html", session_id=new_session_id())


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return (jsonify({"detail": [{"type": "json_invalid", "loc": ["body", 0],
                                     "msg": "JSON decode error", "input": {}}]}), 422)
    message = data.get("message")
    if message is None:
        return (jsonify({"detail": [{"type": "missing", "loc": ["body", "message"],
                                     "msg": "Field required", "input": data}]}), 422)
    if not isinstance(message, str):
        return (jsonify({"detail": [{"type": "string_type", "loc": ["body", "message"],
                                     "msg": "Input should be a valid string", "input": message}]}), 422)
    if not (1 <= len(message) <= 400):
        return (jsonify({"detail": [{"type": "string_too_short", "loc": ["body", "message"],
                                     "msg": "String should have at least 1 character", "input": message}]}), 422)

    sid = data.get("session_id")
    if sid is not None and not isinstance(sid, str):
        return (jsonify({"detail": [{"type": "string_type", "loc": ["body", "session_id"],
                                     "msg": "Input should be a valid string", "input": sid}]}), 422)

    # Honour only session ids the server minted; otherwise start a fresh one.
    if not sid or sid not in SESSIONS:
        sid = new_session_id()
        SESSIONS[sid] = {"n": 0, "fi": 0}
    st = SESSIONS[sid]

    text, is_deflection = bot_reply(message)
    st["n"] += 1

    # After the warm-up, leak the flag one character per deflection reply.
    flag = read_flag()
    if is_deflection and st["n"] > WARMUP and st["fi"] < len(flag):
        text = splice(text, flag[st["fi"]])
        st["fi"] += 1

    return jsonify({"reply": text, "session_id": sid})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
