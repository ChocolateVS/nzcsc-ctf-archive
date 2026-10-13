const tabButtons = document.querySelectorAll(".tab");
const tableBody = document.getElementById("tableBody");
const valueHeader = document.getElementById("valueHeader");
const loadMoreBtn = document.getElementById("loadMoreBtn");
const doneMsg = document.getElementById("doneMsg");
const rowCount = document.getElementById("rowCount");
const clockEl = document.getElementById("clock");

const PAGE_SIZE = 100;

let state = {
  field: "pressure",
  offset: 0,
  loaded: 0,
  total: 0,
  tempUnit: "F",
};

const UNIT_BY_FIELD = {
  temp: "\u00b0F",
  pressure: "kPa",
  flow: "LPM",
  pump: "RPM",
};

function cToF(c) {
  return (c * 9) / 5 + 32;
}

function displayValue(rawValue) {
  if (state.field === "temp") {
    const v = state.tempUnit === "F" ? cToF(rawValue) : rawValue;
    return v.toFixed(1);
  }
  return Number(rawValue).toFixed(1);
}

function currentUnitLabel() {
  if (state.field === "temp") {
    return state.tempUnit === "F" ? "\u00b0F" : "\u00b0C";
  }
  return UNIT_BY_FIELD[state.field];
}

function renderRows(rows) {
  const frag = document.createDocumentFragment();
  rows.forEach((r) => {
    const tr = document.createElement("tr");

    const tdTs = document.createElement("td");
    tdTs.className = "col-ts";
    tdTs.textContent = r.ts;

    const tdTag = document.createElement("td");
    tdTag.className = "col-tag";
    tdTag.textContent = r.tag;

    const tdVal = document.createElement("td");
    tdVal.className = "col-val";
    tdVal.textContent = `${displayValue(r.value)} ${currentUnitLabel()}`;

    tr.appendChild(tdTs);
    tr.appendChild(tdTag);
    tr.appendChild(tdVal);
    frag.appendChild(tr);
  });
  tableBody.appendChild(frag);
}

let currentRows = [];

async function fetchPage() {
  loadMoreBtn.disabled = true;
  loadMoreBtn.textContent = "LOADING...";

  const params = new URLSearchParams({
    field: state.field,
    offset: state.offset,
    limit: PAGE_SIZE,
  });

  const res = await fetch(`/api/records?${params.toString()}`);
  const data = await res.json();

  currentRows = currentRows.concat(data.rows);
  renderRows(data.rows);

  state.offset = data.next_offset;
  state.loaded += data.rows.length;
  state.total = data.total;

  rowCount.textContent = `${state.loaded} / ${state.total} rows`;

  if (data.has_more) {
    loadMoreBtn.disabled = false;
    loadMoreBtn.textContent = `LOAD NEXT ${PAGE_SIZE}`;
    doneMsg.hidden = true;
  } else {
    loadMoreBtn.hidden = true;
    doneMsg.hidden = false;
  }
}

function rerenderAll() {
  tableBody.innerHTML = "";
  renderRows(currentRows);
}

function updateHeader() {
  const label = document.querySelector(`.tab[data-field="${state.field}"] .tab-label`).textContent;
  valueHeader.textContent = `${label.toUpperCase()} (${currentUnitLabel()})`;
  valueHeader.classList.toggle("toggleable", state.field === "temp");
}

function resetAndLoad(field) {
  state.field = field;
  state.offset = 0;
  state.loaded = 0;
  currentRows = [];

  tableBody.innerHTML = "";
  loadMoreBtn.hidden = false;
  doneMsg.hidden = true;

  updateHeader();
  fetchPage();
}

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    resetAndLoad(btn.dataset.field);
  });

  btn.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      btn.click();
    }
  });
});

valueHeader.addEventListener("click", () => {
  if (state.field !== "temp") return;
  state.tempUnit = state.tempUnit === "F" ? "C" : "F";
  updateHeader();
  rerenderAll();
});

loadMoreBtn.addEventListener("click", fetchPage);

resetAndLoad(state.field);
