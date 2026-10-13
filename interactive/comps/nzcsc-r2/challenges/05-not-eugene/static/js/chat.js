(function () {
  // Minted fresh by the server on every page render, so a reload starts a new session.
  let sessionId = document.body.dataset.sessionId || null;
  const log = document.getElementById("log");
  const form = document.getElementById("composer");
  const input = document.getElementById("message");

  function addMessage(role, name, text) {
    const wrap = document.createElement("div");
    wrap.className = "msg " + role;
    const who = document.createElement("small");
    who.textContent = name;
    const body = document.createElement("div");
    body.textContent = text;
    wrap.appendChild(who);
    wrap.appendChild(body);
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
  }

  addMessage(
    "mykola",
    "Mykola",
    "Hello! I am Mykola, from Odessa. You are not another judge from Hamilton, are you? Ask something. I am very interesting boy, papa says so."
  );

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMessage("you", "You", text);
    input.value = "";
    input.focus();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });
      const data = await res.json();
      if (data.session_id) sessionId = data.session_id;
      if (!res.ok) {
        addMessage("mykola", "Mykola", data.error || "Something broke. Not my fault.");
        return;
      }
      addMessage("mykola", "Mykola", data.reply);
    } catch (err) {
      addMessage("mykola", "Mykola", "The internet ate my answer. Try again?");
    }
  });
})();
