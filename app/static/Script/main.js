import { AuthClient } from '/static/Script/auth-client.js';

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

// View containers & auth elements
const authScreen = document.getElementById("authScreen");
const authenticatedApp = document.getElementById("authenticatedApp");
const stationNav = document.getElementById("stationNav");
const userProfileNav = document.getElementById("userProfileNav");
const navUserName = document.getElementById("navUserName");
const navUserAvatar = document.getElementById("navUserAvatar");
const logoutBtn = document.getElementById("logoutBtn");
const providerList = document.getElementById("providerList");

const auth = new AuthClient();
let isAppInitialized = false;

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
      const thumb = t.cover_url
        ? `<img class="thumb" src="${escapeHtml(t.cover_url)}" alt="" onerror="this.src='${DEFAULT_COVER_URL}'">`
        : `<img class="thumb" src="${DEFAULT_COVER_URL}" alt="">`;
      return `<li>${thumb}<div class="history-item-text"><button type="button" class="station-click-btn" data-station-id="${stId}" data-artist="${escapeHtml(t.artist)}" title="Click to tune into ${escapeHtml(t.artist)}"><b>${escapeHtml(t.artist)}</b></button><span class="separator">:</span> <i>${escapeHtml(t.title)}</i></div></li>`;
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

  if (currentTrackKey !== activeTrackKey) return;

  if (data.cover_url) {
    currentTrackCoverUrl = data.cover_url;
    if (lastMeta) {
      lastMeta.cover_url = data.cover_url;
    }
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
    }
    if (
      currentTrackKey !== null &&
      isNewTrack &&
      lastMeta &&
      lastMeta.has_track_info !== false &&
      lastMeta.title
    ) {
      const coverForHistory = lastMeta.cover_url || currentTrackCoverUrl || (lastMeta._station_id ? `/stations/${lastMeta._station_id}/cover` : null);
      history = addToHistory(
        history,
        {
          artist: lastMeta.artist,
          title: lastMeta.title,
          cover_url: coverForHistory,
          station_id: lastMeta._station_id || (currentStation ? currentStation.id : null),
        },
        HISTORY_LIMIT
      );
      renderHistory();
      currentTrackCoverUrl = null;
    }

    currentTrackKey = key;
    trackName.textContent = meta.title;
    artistName.textContent = meta.artist || "Unknown Artist";
    const trackInfoTag = document.getElementById("trackInfoTag");
    if (trackInfoTag) trackInfoTag.textContent = meta.artist || "VECTOR PULSE";
  } else {
    currentTrackKey = null;
    currentTrackCoverUrl = null;
    trackName.textContent = "No track available";
    artistName.textContent = (meta && meta.artist) || "Live Broadcast";
    const trackInfoTag = document.getElementById("trackInfoTag");
    if (trackInfoTag) trackInfoTag.textContent = (meta && meta.artist) || "VECTOR PULSE";
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

  if (coverArt) {
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
  const brandName = document.getElementById("brandName");
  if (brandName && st && st.name) {
    brandName.textContent = `AI Streaming Radio – ${st.name}`;
  }

  const streamQuality = document.getElementById("streamQuality");


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
  renderStationCards();
}


function renderStationCards() {
  const container = document.getElementById("stationCardsList");
  if (!container || !stationsList || !stationsList.length) return;

  const mockListeners = ["142k lisk", "98k lisk", "210k lisk", "75k lisk"];

  container.innerHTML = stationsList.map((st, idx) => {
    const isSelected = currentStation && Number(st.id) === Number(currentStation.id);
    const genreStr = typeof st.genre === "object" && st.genre !== null ? st.genre.name : (st.genre || "Cyber Beats");
    const coverPath = `/stations/${st.id}/cover`;
    const listeners = mockListeners[idx % mockListeners.length];
    return `
      <div class="station-card ${isSelected ? "active" : ""}" data-station-id="${st.id}">
        <div class="station-icon-frame">
          <img class="station-icon-img" src="${coverPath}" alt="${escapeHtml(st.name)}" onerror="this.src='${DEFAULT_COVER_URL}'">
        </div>
        <div class="station-info-group">
          <span class="station-title-bold">${escapeHtml(st.name.toUpperCase())}</span>
          <span class="station-sub-text">${escapeHtml(genreStr)}</span>
          <div class="mini-eq-bars">
            <div class="mini-bar"></div>
            <div class="mini-bar"></div>
            <div class="mini-bar"></div>
            <div class="mini-bar"></div>
          </div>
        </div>
        <span class="station-listeners-count">${listeners}</span>
      </div>
    `;
  }).join("");
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
    renderStationCards();
    renderHistory();
    if (typeof fetchDislikedSongs === "function") {
      fetchDislikedSongs();
    }
  }
}


async function renderProviders() {
  if (!providerList) return;
  providerList.innerHTML = '<p style="color: var(--text-muted);">Loading providers...</p>';
  const providers = await auth.getProviders();
  if (!providers || providers.length === 0) {
    providerList.innerHTML = '<button type="button" class="provider-btn" id="demoLoginBtn">Sign in as Demo Listener</button>';
  } else {
    providerList.innerHTML = providers.map(p => `
      <button type="button" class="provider-btn" data-provider="${p.id}">
        ${p.icon_url ? `<img src="${p.icon_url}" alt="" style="width:20px;height:20px;">` : '🔐'}
        Sign in with ${escapeHtml(p.name)}
      </button>
    `).join('');
  }
}

document.addEventListener("click", (e) => {
  const providerBtn = e.target.closest(".provider-btn");
  if (providerBtn) {
    const providerId = providerBtn.dataset.provider || "demo";
    auth.login(providerId);
    return;
  }

  const stationCard = e.target.closest(".station-card");
  if (stationCard) {
    const stId = Number(stationCard.dataset.stationId);
    const st = stationsList.find((s) => Number(s.id) === stId);
    if (st) {
      selectStation(st, true);
    }
    return;
  }

  const btn = e.target.closest(".station-click-btn");
  if (btn) {
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
    return;
  }
});

if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    auth.logout();
  });
}

// Rating button proxies
const rateUpBtn = document.getElementById("rateUpBtn");
const rateDownBtn = document.getElementById("rateDownBtn");
const thumbUp = document.getElementById("thumbUp");
const thumbDown = document.getElementById("thumbDown");
if (rateUpBtn && thumbUp) rateUpBtn.addEventListener("click", () => thumbUp.click());
if (rateDownBtn && thumbDown) rateDownBtn.addEventListener("click", () => thumbDown.click());


// Hero CTAs
const heroBtnSignIn = document.getElementById("heroBtnSignIn");
const heroBtnRegister = document.getElementById("heroBtnRegister");
if (heroBtnSignIn) {
  heroBtnSignIn.addEventListener("click", () => {
    switchToTab("signin");
    document.getElementById("loginEmail")?.focus();
  });
}
if (heroBtnRegister) {
  heroBtnRegister.addEventListener("click", () => {
    switchToTab("register");
    document.getElementById("regFullName")?.focus();
  });
}

const authFormTitle = document.getElementById("authFormTitle");
const authFormSubtitle = document.getElementById("authFormSubtitle");
const authFooterText = document.getElementById("authFooterText");
const authFooterToggleLink = document.getElementById("authFooterToggleLink");
let currentAuthMode = "signin";

function setAuthMode(mode) {
  currentAuthMode = mode;
  if (mode === "signin") {
    if (loginForm) loginForm.style.display = "flex";
    if (registerForm) registerForm.style.display = "none";
    if (authFormTitle) authFormTitle.textContent = "Welcome back";
    if (authFormSubtitle) authFormSubtitle.textContent = "Please enter your details to sign in to your account";
    if (authFooterText) authFooterText.textContent = "Don't have an account?";
    if (authFooterToggleLink) authFooterToggleLink.textContent = "Sign up for free";
  } else {
    if (registerForm) registerForm.style.display = "flex";
    if (loginForm) loginForm.style.display = "none";
    if (authFormTitle) authFormTitle.textContent = "Create an account";
    if (authFormSubtitle) authFormSubtitle.textContent = "Please fill out your details to get started";
    if (authFooterText) authFooterText.textContent = "Already have an account?";
    if (authFooterToggleLink) authFooterToggleLink.textContent = "Sign in";
  }
}

if (authFooterToggleLink) {
  authFooterToggleLink.addEventListener("click", (e) => {
    e.preventDefault();
    setAuthMode(currentAuthMode === "signin" ? "register" : "signin");
  });
}


// Form submission handlers
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const registerForm = document.getElementById("registerForm");
const registerError = document.getElementById("registerError");

if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (loginError) loginError.style.display = "none";
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;
    try {
      await auth.loginEmailPassword(email, password);
    } catch (err) {
      if (loginError) {
        loginError.textContent = err.message || "Invalid credentials.";
        loginError.style.display = "block";
      }
    }
  });
}

if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (registerError) registerError.style.display = "none";
    const fullName = document.getElementById("regFullName").value;
    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;
    try {
      await auth.registerEmailPassword(email, password, fullName);
    } catch (err) {
      if (registerError) {
        registerError.textContent = err.message || "Registration failed.";
        registerError.style.display = "block";
      }
    }
  });
}

// Authentication state listener & view gating
auth.onAuthStateChanged(async (user) => {
  if (user) {
    // Authenticated state
    if (authScreen) authScreen.style.display = "none";
    if (authenticatedApp) authenticatedApp.style.display = "block";
    if (stationNav) stationNav.style.display = "flex";
    if (userProfileNav) userProfileNav.style.display = "flex";

    if (navUserName) navUserName.textContent = user.full_name || user.email;
    if (navUserAvatar && user.avatar_url) {
      navUserAvatar.src = user.avatar_url;
      navUserAvatar.style.display = "inline-block";
    }

    if (!isAppInitialized) {
      isAppInitialized = true;
      await loadStations();
      setInterval(pollMetadata, METADATA_POLL_MS);
    }
  } else {
    // Unauthenticated state
    if (authScreen) authScreen.style.display = "flex";
    if (authenticatedApp) authenticatedApp.style.display = "none";
    if (stationNav) stationNav.style.display = "none";
    if (userProfileNav) userProfileNav.style.display = "none";

    renderProviders();
  }
});

// Check user state on startup
auth.getUser();


