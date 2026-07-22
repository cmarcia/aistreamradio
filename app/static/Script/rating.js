let currentSong = null; // { artist, title, has_track_info }
let rated = null;

function getThumbUpBtn() {
  return document.getElementById("thumbUp") || document.getElementById("rateUpBtn");
}

function getThumbDownBtn() {
  return document.getElementById("thumbDown") || document.getElementById("rateDownBtn");
}

function getThumbUpCount() {
  return document.getElementById("thumbUpCount");
}

function getThumbDownCount() {
  return document.getElementById("thumbDownCount");
}

function renderRatingSummary(summary) {
  const upCount = getThumbUpCount();
  const downCount = getThumbDownCount();
  if (upCount) upCount.textContent = summary.thumbs_up;
  if (downCount) downCount.textContent = summary.thumbs_down;
  rated = summary.user_rating;

  const btnUp = getThumbUpBtn();
  const btnDown = getThumbDownBtn();
  if (btnUp) btnUp.classList.toggle("active", rated === "up");
  if (btnDown) btnDown.classList.toggle("active", rated === "down");
}

async function fetchRatingSummary() {
  if (!currentSong || currentSong.has_track_info === false || !currentSong.title) return;
  const params = new URLSearchParams({
    artist: currentSong.artist,
    title: currentSong.title,
    listener_id: getListenerId(),
  });
  const summary = await apiFetchOrWarn(
    API_PATHS.RATING + "?" + params.toString(),
    undefined,
    "rating fetch failed"
  );
  if (summary) renderRatingSummary(summary);
}

// coverArt is defined in main.js — it owns the "now playing" cover art
// element, since it's the one that sets coverArt.src from live metadata.
function captureCoverSnapshot() {
  const coverEl = document.getElementById("coverArt");
  if (!coverEl || !coverEl.naturalWidth) return null;
  try {
    const canvas = document.createElement("canvas");
    canvas.width = coverEl.naturalWidth;
    canvas.height = coverEl.naturalHeight;
    canvas.getContext("2d").drawImage(coverEl, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.85);
  } catch (err) {
    console.warn("cover snapshot failed", err);
    return null;
  }
}

async function setRating(kind) {
  if (!currentSong || currentSong.has_track_info === false || !currentSong.title) return;
  if (rated === kind) return;

  const summary = await apiFetchOrWarn(
    API_PATHS.RATING,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist: currentSong.artist,
        title: currentSong.title,
        listener_id: getListenerId(),
        rating: kind,
        cover_image: kind === "down" ? captureCoverSnapshot() : null,
      }),
    },
    "rating submit failed"
  );

  if (!summary) return;
  renderRatingSummary(summary);
  if (kind === "down") {
    skipDislikedTrack();
    if (typeof resetDislikedToFirstPage === "function") {
      resetDislikedToFirstPage();
    }
  }
}

document.addEventListener("click", (e) => {
  const upBtn = e.target.closest("#thumbUp, #rateUpBtn");
  if (upBtn) {
    e.preventDefault();
    setRating("up");
    return;
  }
  const downBtn = e.target.closest("#thumbDown, #rateDownBtn");
  if (downBtn) {
    e.preventDefault();
    setRating("down");
    return;
  }
});

let skippingSong = null;
function skipDislikedTrack() {
  skippingSong = currentSong;
  const audioEl = document.getElementById("audio");
  if (audioEl) audioEl.muted = true;
  if (typeof setStatus === "function") setStatus("Skipping disliked track…");
}

function maybeEndSkip() {
  if (!skippingSong) return;
  const stillSameSong =
    currentSong &&
    currentSong.artist === skippingSong.artist &&
    currentSong.title === skippingSong.title;
  if (!stillSameSong) {
    skippingSong = null;
    const audioEl = document.getElementById("audio");
    if (audioEl) audioEl.muted = false;
    if (typeof setStatus === "function") setStatus("");
  }
}

function onTrackChanged(song) {
  currentSong = song;
  const hasTrack = song && song.has_track_info !== false && Boolean(song.title);

  const btnUp = getThumbUpBtn();
  const btnDown = getThumbDownBtn();
  if (btnUp) btnUp.disabled = !hasTrack;
  if (btnDown) btnDown.disabled = !hasTrack;

  if (hasTrack) {
    fetchRatingSummary();
  } else {
    rated = null;
    const upCount = getThumbUpCount();
    const downCount = getThumbDownCount();
    if (upCount) upCount.textContent = "0";
    if (downCount) downCount.textContent = "0";
    if (btnUp) btnUp.classList.remove("active");
    if (btnDown) btnDown.classList.remove("active");
  }
  maybeEndSkip();
}

