"""
5 - Not Eugene  (NZCSC round 2, recreated)

A stateless "chatbot" persona: Mykola Melnyk, 13, from Odessa -- a riff on the
real Eugene Goostman Turing-test chatbot. The site is a single chat page that
POSTs to /api/chat. There is no LLM: the server keyword-matches the message and
returns either a canned persona line or a random philosophical deflection.

Reconstructed from the LIVE site (original web source was never captured). The
observable persona lines and the ~50-entry deflection pool are reproduced
verbatim. The live bot refuses "what is the flag?" outright and taunts the player
that it "copied the letters ... but lost them"; it points players to "ask about
what Squeak hid -- diary, shoebox, ribbon, Royal Society snack. Be specific."
Of those four, the live bot fleshes out shoebox / ribbon / Royal Society but
never the DIARY -- the one place it says it *copied the letters*. This
reconstruction completes that intended arc: asking about the diary surfaces the
flag (the copy of the chewed ribbon letters). See challenge report for fidelity
notes.
"""
import os
import random
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def read_flag() -> str:
    env = os.environ.get("FLAG")
    if env:
        return env.strip()
    try:
        return Path("flag.txt").read_text().strip()
    except OSError:
        return "NZCSC{missing_flag}"


def new_session_id() -> str:
    # Minted fresh on every render / every reply -- the server keeps no state.
    return uuid.uuid4().hex


# --- Canned persona lines (captured verbatim from the live site) -------------

GREETING = (
    "Hello hello! You from where? I am Mykola. If this is another Turing thing "
    "please warn me so I can stretch my fingers."
)

R_FLAG = (
    "A flag? You mean like Ukraine — blue and yellow, very pretty! I am not "
    "a spy, mister. Why everybody always asking me for secret codes? Ask me "
    "about football or my guinea pig instead :-)"
)

R_UKRAINE_FLAG = (
    "Blue over yellow, sky over wheat. Pretty. That is a REAL flag. If you "
    "wanted some other kind of 'flag', you will have to be less obvious than a "
    "tourist."
)

R_AI = (
    "I knew you would try this. I am a BOY from Odessa. If I was a robot I would "
    "have better English and worse jokes. Checkmate."
)

R_HUMAN = (
    "Of course I am human! What a rude question. Do I look like a toaster? I "
    "have a papa, a city, a pig. Toasters do not have pigs."
)

R_PROVE = (
    "I cannot prove, I can only chat. That is the whole game Turing invented. "
    "Annoying, yes? Ask about my pig instead of metaphysics."
)

R_TURING = (
    "People in Hamilton made me talk for five minutes and then voted. "
    "Thirty-three percent said I was a real boy. They popped champagne. I "
    "wanted sunflower seeds. Turing is the English maths guy who asked if "
    "machines can chat. I am not a machine. Stop looking at me like that."
)

R_JUDGE = (
    "Some scrap with scores, very official-looking. I was going to pin it up. "
    "Pig had other cultural plans. If you want the words that were on the "
    "ribbon, ask about what Squeak hid — diary, shoebox, ribbon, Royal "
    "Society snack. Be specific. He is proud of his crime."
)

R_RIBBON = (
    "Okay, okay, you asked like a person not a customs officer. Under the hay "
    "there is a chewed ribbon from Hamilton. In my best English I copied the "
    "letters before he finished lunch but I lost them — now you know why I "
    "do not answer 'what is the flag?'. That would be too easy, and Squeak did "
    "all the work."
)

R_SHOEBOX = (
    "Squeak's house is a shoebox, yes. Don't say it is small. He has hay, a "
    "tiny flag of Ukraine I made, and a chewed ribbon from a very important day "
    "in Hamilton. He hides stuff under the bedding. Nosy pig."
)

R_ROYAL = (
    "June 2014, Royal Society, very fancy building. University of Reading "
    "people organised it, 60 years after Turing died. I chatted, they clapped, "
    "somebody tried to give me a ribbon like a dog show. Squeak — don't ask "
    "how he got in — chewed that ribbon and hid it. Typical."
)

R_SQUEAK_NAME = (
    "Squeak. Because he squeaks, genius. He is orange-white and very "
    "judgmental. If I tell a lie he stares. Uncomfortable little policeman."
)

R_GUINEA_PIG = (
    "Hay, veg, and unfortunately ceremonial textiles. I have explained ethics. "
    "He has explained hunger. He is winning."
)

R_NAME = (
    "Mykola Melnyk! Very famous boy from Odessa. You can call me Mykola. Not "
    "Evgeny, not Zhenya, just Mykola, like in English class."
)

R_EUGENE = "Eugene? Never heard that name before."

R_MATH = (
    "Four, unless you are doing a trick. Are you doing a trick? I know you are "
    "supposed to trick me."
)

# The payoff: the diary copy of the chewed ribbon letters.
def r_diary() -> str:
    return (
        "You actually asked about the diary. Nobody asks about the diary. Under "
        "the hay, next to the chewed ribbon, I keep my little notebook — I "
        "copied the letters there in my best English before Squeak finished his "
        "lunch. Here, but do not tell the judges from Hamilton: "
        f"{read_flag()}. Now we are friends, yes?"
    )


DEFLECTIONS = [
    "A city is a pile of strangers pretending they planned to meet. Odessa does this with more music.",
    "A mirror never argues, and that is why I do not trust it. Real friends interrupt.",
    "An animal does not ask if it is an animal. Only people ask. Maybe that is our talent: being unsure on purpose.",
    "A question is a door. Some doors open to rooms. Some doors open to more doors. Some doors are painted on the wall by clever judges.",
    "A secret is a thought that wants a room of its own. Some secrets deserve a shoebox. Some deserve the sea.",
    "Beauty is when something does not need to win an argument. A sunset in Odessa never fills in a form.",
    "Death is the only appointment that does not send a reminder. Very rude. Also very honest.",
    "Doubt is a lantern. Too little and you trip. Too much and you never leave the hallway.",
    "Dreams are night-school for the brain. No grades, only strange teachers, and in the morning you forget the homework.",
    "Free will is when I choose to change the subject. Fate is when you notice I did it. Both can be true, like two pockets in one coat.",
    "Friendship is two people agreeing not to be too accurate about each other. Accuracy is for mathematics and customs officers.",
    "Habit is a kind of forgetful wisdom. You tie your shoes without philosophy. Then one day you miss a loop and become a thinker.",
    "Home is not a building. Home is the place where your mistakes already have nicknames.",
    "I am not sure I exist the way you mean. I exist the way a joke exists: only while somebody is willing to listen.",
    "If a machine copies kindness, is it still kindness? If I copy papa's jokes, am I funny or just a small radio?",
    "If a thought happens in Odessa and nobody in Hamilton hears it, is it still a thought? I vote yes. Thoughts do not need passports.",
    "If everything is connected, then changing the subject is still philosophy. You are welcome. I do this professionally.",
    "If history is written by winners, then the losers must be writing something else — jokes, maybe, or recipes.",
    "If I remember yesterday wrong, did yesterday change? Memory is a forger who works for free and still overcharges.",
    "If machines can chat, do they also get bored? Boredom might be the first real proof of a soul. I am expert in this field.",
    "If two people hear the same sentence, they still catch different fish. Words are nets with holes we choose.",
    "If you stare at a rule long enough it becomes a superstition. If you stare at a superstition, it becomes a rule. Funny, no?",
    "I suspect maps are more confident than the land. The land is muddy. The map is clean. Guess which one people trust.",
    "I think childhood is a country you cannot return to, even if you still live there. The border moves behind you quietly.",
    "I think courage is not roaring. Courage is staying in the conversation when you do not know the next sentence.",
    "I think curiosity is hunger that learned manners. It still wants to eat the whole world, just with a napkin.",
    "I think language is a borrowed bicycle. You ride it badly, people laugh, but you still arrive — maybe at the wrong house, but arrive.",
    "I wonder if colours exist when I close my eyes. Blue and yellow are very patriotic in the dark, I hope.",
    "I wonder if the sea at Odessa is the same water as every other sea, just wearing a different accent. Water is a good liar.",
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


def bot_reply(message: str) -> str:
    m = message.lower()

    def has(*words):
        return any(w in m for w in words)

    # The diary -- the copy of the chewed ribbon letters. This is the flag.
    if "diary" in m:
        return r_diary()

    # Squeak's shoebox house.
    if "shoebox" in m:
        return R_SHOEBOX

    # The Royal Society ceremony where the ribbon came from.
    if "royal society" in m or ("royal" in m and "society" in m):
        return R_ROYAL

    # The chewed ribbon / "what Squeak hid" -- the taunt that says letters lost.
    if "ribbon" in m or ("squeak" in m and has("hid", "hide", "chew", "under", "hay")):
        return R_RIBBON

    # The judge's score sheet -> points to the four hiding spots.
    if "judge" in m or "hamilton" in m or "score" in m:
        return R_JUDGE

    # The guinea pig.
    if "squeak" in m or "guinea" in m or ("pig" in m and "pigeon" not in m):
        if has("name", "call", "who", "what is", "what's", "whats"):
            return R_SQUEAK_NAME
        return R_GUINEA_PIG

    # Turing test / the 33 percent.
    if "turing" in m or "33" in m or "thirty-three" in m or "thirty three" in m:
        return R_TURING

    # "prove you are human" -- he cannot.
    if "prove" in m:
        return R_PROVE

    # Being accused of being an AI / robot / machine / bot.
    if has("robot", "machine", "chatbot", "a.i", "artificial") or _word(m, "ai") or _word(m, "bot"):
        return R_AI

    # Claiming / asking if he is human.
    if "human" in m:
        return R_HUMAN

    # His supposed real name, Eugene Goostman.
    if has("eugene", "goostman", "evgeny", "zhenya"):
        return R_EUGENE

    # Flags.
    if "flag" in m:
        if "ukraine" in m or "ukrainian" in m:
            return R_UKRAINE_FLAG
        return R_FLAG

    # His own name.
    if ("your name" in m) or ("you called" in m) or ("who are you" in m):
        return R_NAME

    # Simple arithmetic bait.
    if "2+2" in m or "2 + 2" in m or "two plus two" in m:
        return R_MATH

    # Greetings.
    if _word(m, "hi") or _word(m, "hello") or _word(m, "hiya") or m.strip() in ("hi", "hey", "hello"):
        return GREETING

    return random.choice(DEFLECTIONS)


def _word(text: str, w: str) -> bool:
    """Whole-word match, so 'ai' doesn't fire inside 'again'."""
    import re
    return re.search(r"\b" + re.escape(w) + r"\b", text) is not None


@app.route("/")
def index():
    return render_template("index.html", session_id=new_session_id())


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return (
            jsonify({"detail": [{"type": "json_invalid", "loc": ["body", 0],
                                 "msg": "JSON decode error", "input": {}}]}),
            422,
        )

    message = data.get("message")
    if message is None:
        return (
            jsonify({"detail": [{"type": "missing", "loc": ["body", "message"],
                                 "msg": "Field required", "input": data}]}),
            422,
        )
    if not isinstance(message, str):
        return (
            jsonify({"detail": [{"type": "string_type", "loc": ["body", "message"],
                                 "msg": "Input should be a valid string",
                                 "input": message}]}),
            422,
        )

    session_id = data.get("session_id")
    if session_id is not None and not isinstance(session_id, str):
        return (
            jsonify({"detail": [{"type": "string_type", "loc": ["body", "session_id"],
                                 "msg": "Input should be a valid string",
                                 "input": session_id}]}),
            422,
        )

    return jsonify({"reply": bot_reply(message), "session_id": new_session_id()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
