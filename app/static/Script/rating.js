const thumbUp = document.getElementById("thumbUp");
const thumbDown = document.getElementById("thumbDown");
const thumbUpCount = document.getElementById("thumbUpCount");
const thumbDownCount = document.getElementById("thumbDownCount");

let currentSong = null; // { artist, title, has_track_info }
let rated = null;

function renderRatingSummary(summary) {
  thumbUpCount.textContent = summary.thumbs_up;
  thumbDownCount.textContent = summary.thumbs_down;
  rated = summary.user_rating;
  thumbUp.classList.toggle("active", rated === "up");
  thumbDown.classList.toggle("active", rated === "down");
}

async function fetchRatingSummary() {
  if (!currentSong || currentSong.has_track_info === false || !currentSong.title) return;
  const params = new URLSearchParams({
    artist: currentSong.artist,
    title: currentSong.title,
    listener_id: listenerId,
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
  if (!coverArt || !coverArt.naturalWidth) return null;
  try {
    const canvas = document.createElement("canvas");
    canvas.width = coverArt.naturalWidth;
    canvas.height = coverArt.naturalHeight;
    canvas.getContext("2d").drawImage(coverArt, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.85);
  } catch (err) {
    console.warn("cover snapshot failed", err);
    return null;
  }
}

async function setRating(kind) {
  if (!currentSong || currentSong.has_track_info === false || !currentSong.title || rated) return;
  const summary = await apiFetchOrWarn(
    API_PATHS.RATING,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist: currentSong.artist,
        title: currentSong.title,
        listener_id: listenerId,
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
    resetDislikedToFirstPage();
  }
}
if (thumbUp) thumbUp.addEventListener("click", () => setRating("up"));
if (thumbDown) thumbDown.addEventListener("click", () => setRating("down"));

// We can't seek forward on a live broadcast, so "skip" mutes playback
// until the metadata poll reports a different track, then unmutes.
let skippingSong = null;
function skipDislikedTrack() {
  skippingSong = currentSong;
  audio.muted = true;
  setStatus("Skipping disliked track…");
}

function maybeEndSkip() {
  if (!skippingSong) return;
  const stillSameSong =
    currentSong &&
    currentSong.artist === skippingSong.artist &&
    currentSong.title === skippingSong.title;
  if (!stillSameSong) {
    skippingSong = null;
    audio.muted = false;
    setStatus("");
  }
}

// Called by main.js whenever the live metadata poll reports a (possibly
// unchanged) "now playing" track.
function onTrackChanged(song) {
  currentSong = song;
  const hasTrack = song && song.has_track_info !== false && Boolean(song.title);

  if (thumbUp) thumbUp.disabled = !hasTrack;
  if (thumbDown) thumbDown.disabled = !hasTrack;

  if (hasTrack) {
    fetchRatingSummary();
  } else {
    rated = null;
    if (thumbUpCount) thumbUpCount.textContent = "0";
    if (thumbDownCount) thumbDownCount.textContent = "0";
    if (thumbUp) thumbUp.classList.remove("active");
    if (thumbDown) thumbDown.classList.remove("active");
  }
  maybeEndSkip();
}
