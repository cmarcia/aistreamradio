let METADATA_URL = "/stations/1/metadata";
const DEFAULT_COVER_URL = "/static/Images/default-cover.svg";
const COVER_URL = "/static/Images/default-cover.svg";
const METADATA_POLL_MS = 15000;
const HISTORY_LIMIT = 5;

const coverArt = document.getElementById("coverArt");
const artistName = document.getElementById("artistName");
const albumName = document.getElementById("albumName");
const trackName = document.getElementById("trackName");
const sourceQuality = document.getElementById("sourceQuality");
const historyList = document.getElementById("historyList");
const stationSelect = document.getElementById("stationSelect");

if (coverArt) {
  coverArt.onerror = () => {
    if (currentStation) {
      const stationFallback = `/stations/${currentStation.id}/cover`;
      if (coverArt.src && !coverArt.src.includes(stationFallback)) {
        coverArt.src = stationFallback;
      }
    } else if (coverArt.src && !coverArt.src.includes(DEFAULT_COVER_URL)) {
      coverArt.src = DEFAULT_COVER_URL;
    }
  };
}

let currentStation = null;
let currentTrackKey = null;
let currentTrackCoverUrl = null;
let lastMeta = null;
let history = [];
let stationsList = [];

function updateStationSelectOptions(selectedId) {
  if (!stationSelect || !stationsList || !stationsList.length) return;
  stationSelect.innerHTML = stationsList
    .map((s) => {
      const isSelected = Number(s.id) === Number(selectedId);
      const label = formatStationLabel(s, isSelected);
      return `<option value="${s.id}" ${isSelected ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");
  stationSelect.value = String(selectedId);
}

function renderHistory() {
  renderList(
    historyList,
    history,
    (t) => {
      const st = findStationByArtist(t.artist, stationsList) || (t.station_id && stationsList.find((s) => Number(s.id) === Number(t.station_id)));
      const stId = st ? st.id : "";
      return `<li><button type="button" class="station-click-btn" data-station-id="${stId}" data-artist="${escapeHtml(t.artist)}" title="Click to tune into ${escapeHtml(t.artist)}"><b>${escapeHtml(t.artist)}</b></button><span class="separator">:</span> <i>${escapeHtml(t.title)}</i></li>`;
    },
    "Nothing played yet this session."
  );
}

async function fetchTrackCoverArt(artist, title, album) {
  if (!artist || !title) return;

  const activeTrackKey = currentTrackKey;
  const params = new URLSearchParams({ artist, title });
  if (album) params.append("album", album);

  const data = await apiFetchOrWarn(`/itunes/search?${params.toString()}`, {}, "Cover art lookup failed");
  if (!data) return;

  // Race condition guard: ensure track has not changed while request was in-flight
  if (currentTrackKey !== activeTrackKey) return;

  if (data.cover_url) {
    currentTrackCoverUrl = data.cover_url;
    if (coverArt) {
      coverArt.src = data.cover_url;
    }
  }
  if (data.album_name && albumName) {
    let yearStr = data.release_year ? ` (${data.release_year})` : "";
    albumName.textContent = `${data.album_name}${yearStr}`;
  }
}

function applyMetadata(meta) {
  if (meta && currentStation) {
    meta._station_id = currentStation.id;
  }
  const hasTrackInfo = Boolean(meta && meta.has_track_info !== false && meta.title);

  let isNewTrack = false;
  if (hasTrackInfo) {
    const key = (meta.artist || "") + " — " + meta.title;
    if (key !== currentTrackKey) {
      isNewTrack = true;
      currentTrackCoverUrl = null;
    }
    if (
      currentTrackKey !== null &&
      isNewTrack &&
      lastMeta &&
      lastMeta.has_track_info !== false &&
      lastMeta.title
    ) {
      history = addToHistory(
        history,
        {
          artist: lastMeta.artist,
          title: lastMeta.title,
          station_id: lastMeta._station_id || (currentStation ? currentStation.id : null),
        },
        HISTORY_LIMIT
      );
      renderHistory();
    }
    currentTrackKey = key;
    trackName.textContent = meta.title;
    artistName.textContent = meta.artist || "Unknown Artist";
  } else {
    currentTrackKey = null;
    currentTrackCoverUrl = null;
    trackName.textContent = "No track available";
    artistName.textContent = (meta && meta.artist) || "Live Broadcast";
  }
  lastMeta = meta;

  let albumStr = (meta && meta.album) || "";
  if (meta && meta.date && !albumStr.includes(meta.date)) {
    albumStr += " (" + meta.date + ")";
  }
  albumName.textContent = albumStr;

  const bitDepth = meta && meta.bit_depth ? meta.bit_depth + "-bit" : "";
  const sampleRate = meta && meta.sample_rate ? (meta.sample_rate / 1000).toFixed(1) + "kHz" : "";
  sourceQuality.textContent = "Source quality: " + [bitDepth, sampleRate].filter(Boolean).join(" ");

  const genrePill = document.getElementById("stationGenrePill");
  if (genrePill && meta && (meta.genre || window.currentStationGenre)) {
    genrePill.textContent = "GENRE: " + (meta.genre || window.currentStationGenre);
  }

  if (meta && meta.cover_url) {
    currentTrackCoverUrl = meta.cover_url.startsWith("http")
      ? meta.cover_url
      : meta.cover_url + "?t=" + Date.now();
    coverArt.src = currentTrackCoverUrl;
  } else if (currentTrackCoverUrl) {
    coverArt.src = currentTrackCoverUrl;
  } else if (currentStation) {
    coverArt.src = `/stations/${currentStation.id}/cover?t=` + Date.now();
  } else {
    coverArt.src = DEFAULT_COVER_URL;
  }

  if (hasTrackInfo && isNewTrack) {
    fetchTrackCoverArt(meta.artist, meta.title, meta.album);
  }

  onTrackChanged({
    artist: (meta && meta.artist) || "",
    title: hasTrackInfo ? meta.title : "",
    has_track_info: hasTrackInfo,
  });
}

async function pollMetadata() {
  if (!METADATA_URL) return;
  const meta = await apiFetchOrWarn(METADATA_URL, { cache: "no-store" }, "metadata fetch failed");
  if (meta) applyMetadata(meta);
}

function selectStation(st, autoPlay = false) {
  if (!st) return;
  currentStation = st;
  currentTrackKey = null;
  currentTrackCoverUrl = null;
  updateStationSelectOptions(st.id);


  const brandName = document.getElementById("brandName");
  const streamQuality = document.getElementById("streamQuality");

  if (brandName && st.name) {
    brandName.textContent = st.name;
  }
  const genreStr = typeof st.genre === "object" && st.genre !== null ? st.genre.name : st.genre;
  if (genreStr) {
    window.currentStationGenre = genreStr;
    const genrePill = document.getElementById("stationGenrePill");
    if (genrePill) {
      genrePill.textContent = "GENRE: " + genreStr;
    }
  }
  if (streamQuality) {
    const freq = st.frequency ? st.frequency + " / " : "";
    const genre = genreStr || "HLS Lossless";
    streamQuality.textContent = "Stream quality: " + freq + genre;
  }

  if (st.stream_url) {
    changeStream(st.stream_url, autoPlay);
  }
  if (st.metadata_url) {
    METADATA_URL = st.metadata_url;
    pollMetadata();
  }
}

async function loadStations() {
  const data = await apiFetchOrWarn("/stations", {}, "Failed to load stations");
  if (data && data.length > 0) {
    stationsList = data;
    window.stationsList = stationsList;
    if (stationSelect) {
      selectStation(stationsList[0], false);

      stationSelect.addEventListener("change", (e) => {
        const selectedId = Number(e.target.value);
        const st = stationsList.find((s) => s.id === selectedId);
        if (st) {
          selectStation(st, true);
        }
      });
    }
    renderHistory();
    if (typeof fetchDislikedSongs === "function") {
      fetchDislikedSongs();
    }
  }
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".station-click-btn");
  if (!btn) return;

  e.preventDefault();
  e.stopPropagation();

  const stId = btn.dataset.stationId;
  const artistName = btn.dataset.artist;

  let station = null;
  if (artistName && stationsList.length) {
    station = findStationByArtist(artistName, stationsList);
  }
  if (!station && stId && stationsList.length) {
    station = stationsList.find((s) => Number(s.id) === Number(stId));
  }

  if (station) {
    selectStation(station, true);
  }
});

setInterval(pollMetadata, METADATA_POLL_MS);
fetchDislikedSongs();
loadStations();
