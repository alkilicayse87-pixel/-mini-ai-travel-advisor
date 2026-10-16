"use strict";

// Backend URL comes from config.js; override with ?api=http://127.0.0.1:8000 for local testing.
const API = (
  new URLSearchParams(location.search).get("api") ||
  (window.APP_CONFIG && window.APP_CONFIG.apiBase) ||
  ""
).replace(/\/$/, "");

const $ = (id) => document.getElementById(id);
const messagesEl = $("messages");
const form = $("form");
const input = $("input");
const sendBtn = $("send");
const itineraryBtn = $("itinerary-btn");
const itineraryEl = $("itinerary");

let responseId = null; // conversation state lives here (client-managed)
let busy = false;

function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}

// Inline **bold** only; everything is inserted as text nodes (never as HTML).
function appendInline(parent, text) {
  text.split(/(\*\*[^*]+\*\*)/g).forEach((part) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      parent.appendChild(el("strong", part.slice(2, -2)));
    } else if (part) {
      parent.appendChild(document.createTextNode(part));
    }
  });
}

// Small, safe Markdown subset: headings, bullet lists, bold, paragraphs.
function renderMarkdown(container, text) {
  let list = null;
  text.split("\n").forEach((raw) => {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[-*]\s+(.*)/);
    if (bullet) {
      if (!list) { list = el("ul"); container.appendChild(list); }
      const li = el("li");
      appendInline(li, bullet[1]);
      list.appendChild(li);
      return;
    }
    list = null;
    const heading = line.match(/^#{1,6}\s+(.*)/);
    if (heading) {
      const h = el("h3");
      appendInline(h, heading[1]);
      container.appendChild(h);
    } else if (line.trim()) {
      const p = el("p");
      appendInline(p, line);
      container.appendChild(p);
    }
  });
}

function addMessage(role, text) {
  const div = el("div", undefined, `msg ${role}`);
  if (role === "bot") renderMarkdown(div, text);
  else div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function setBusy(value) {
  busy = value;
  sendBtn.disabled = value;
  input.disabled = value;
  itineraryBtn.disabled = value || !responseId;
}

function showUsage(u) {
  $("usage").textContent =
    `Tokens: ${u.input_tokens} in / ${u.output_tokens} out · est. cost $${u.cost_usd.toFixed(4)}`;
}

async function post(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (res.status === 429) detail = "Too many requests, please wait a moment.";
      else if (typeof data.detail === "string") detail = data.detail;
      else if (res.status === 422) detail = "Invalid message.";
    } catch (_) { /* keep default */ }
    throw new Error(detail);
  }
  return res.json();
}

async function sendMessage(text) {
  addMessage("user", text);
  const typing = addMessage("bot", "Thinking…");
  typing.classList.add("typing");
  setBusy(true);
  try {
    const body = { message: text };
    if (responseId) body.previous_response_id = responseId;
    const data = await post("/chat", body);
    typing.remove();
    addMessage("bot", data.answer);
    responseId = data.response_id;
    showUsage(data.conversation_usage);
  } catch (err) {
    typing.remove();
    addMessage("error", err.message);
  } finally {
    setBusy(false);
    input.focus();
  }
}

function table(headers, rows, numericCols = []) {
  const t = el("table");
  const head = el("tr");
  headers.forEach((h) => head.appendChild(el("th", h)));
  t.appendChild(head);
  rows.forEach((r) => {
    const tr = el("tr");
    r.forEach((c, i) => tr.appendChild(el("td", String(c), numericCols.includes(i) ? "num" : "")));
    t.appendChild(tr);
  });
  return t;
}

function renderItinerary(it) {
  itineraryEl.replaceChildren();
  const cur = it.budget.currency;
  itineraryEl.appendChild(el("h2", it.title));
  itineraryEl.appendChild(el("p", `${it.destination} · ${it.duration_days} days`));
  itineraryEl.appendChild(el("p", it.summary));
  it.days.forEach((d) => {
    itineraryEl.appendChild(el("h3", `Day ${d.day}: ${d.theme}`));
    itineraryEl.appendChild(table(
      ["When", "Activity", "Details", `Cost (${cur})`],
      d.activities.map((a) => [a.time_of_day, a.title, a.description, a.estimated_cost.toFixed(2)]),
      [3],
    ));
  });
  itineraryEl.appendChild(el("h3", "Practical tips"));
  const ul = el("ul");
  it.tips.forEach((t) => ul.appendChild(el("li", t)));
  itineraryEl.appendChild(ul);
  itineraryEl.appendChild(el("h3", "Estimated budget"));
  itineraryEl.appendChild(table(
    ["Category", `Amount (${cur})`],
    [...it.budget.items.map((i) => [i.category, i.amount.toFixed(2)]),
     ["TOTAL", it.budget.total.toFixed(2)]],
    [1],
  ));
  itineraryEl.hidden = false;
  itineraryEl.scrollIntoView({ behavior: "smooth" });
}

async function createItinerary() {
  const typing = addMessage("bot", "Building your itinerary…");
  typing.classList.add("typing");
  setBusy(true);
  try {
    const data = await post("/itinerary", { previous_response_id: responseId });
    typing.remove();
    responseId = data.response_id;
    showUsage(data.conversation_usage);
    if (data.ready) {
      renderItinerary(data.itinerary);
    } else {
      addMessage("bot", data.clarification || "I need a bit more information first.");
    }
  } catch (err) {
    typing.remove();
    addMessage("error", err.message);
  } finally {
    setBusy(false);
  }
}

function reset() {
  responseId = null;
  messagesEl.replaceChildren();
  itineraryEl.replaceChildren();
  itineraryEl.hidden = true;
  showUsage({ input_tokens: 0, output_tokens: 0, cost_usd: 0 });
  setBusy(false);
  sendMessage("Hi!");
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || busy) return;
  input.value = "";
  sendMessage(text);
});
itineraryBtn.addEventListener("click", () => { if (!busy && responseId) createItinerary(); });
$("new-btn").addEventListener("click", () => { if (!busy) reset(); });

reset();
