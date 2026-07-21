const API_PATHS = {
  RATING: "/songs/rating",
  DISLIKED: "/songs/disliked",
};

function getListenerId() {
  let id = localStorage.getItem("listenerId");
  if (!id) {
    id = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random());
    localStorage.setItem("listenerId", id);
  }
  return id;
}
const listenerId = getListenerId();

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// Renders a <ul>/<ol>'s children from `items`, or a single "empty" <li> when
// there are none. `toHtml` must return a full <li>...</li> string.
function renderList(container, items, toHtml, emptyMessage) {
  if (!items.length) {
    container.innerHTML = `<li class="empty">${escapeHtml(emptyMessage)}</li>`;
    return;
  }
  container.innerHTML = items.map(toHtml).join("");
}

// Fetches `url`, parses JSON, and throws on a non-2xx response.
async function apiFetch(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

// Same as apiFetch, but swallows errors (logging via console.warn) and
// returns null instead of throwing. Use for best-effort UI updates where a
// failed request shouldn't interrupt anything else on the page.
async function apiFetchOrWarn(url, options, warnLabel) {
  try {
    return await apiFetch(url, options);
  } catch (err) {
    console.warn(warnLabel, err);
    return null;
  }
}
