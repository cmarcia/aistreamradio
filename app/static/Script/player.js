let STREAM_URL = "/stations/1/stream";

const audio = document.getElementById("audio");
const playBtn = document.getElementById("playBtn");
const playIcon = document.getElementById("playIcon");
const pauseIcon = document.getElementById("pauseIcon");
const muteBtn = document.getElementById("muteBtn");
const volumeSlider = document.getElementById("volumeSlider");
const timeDisplay = document.getElementById("timeDisplay");
const statusMsg = document.getElementById("statusMsg");

let hls = null;
let hasStarted = false;

function setStatus(text, isError) {
  statusMsg.textContent = text;
  statusMsg.className = "status-line" + (isError ? " error" : "");
}

function setPlayingUI(isPlaying) {
  playIcon.style.display = isPlaying ? "none" : "block";
  pauseIcon.style.display = isPlaying ? "block" : "none";
  const coverArt = document.getElementById("coverArt");
  if (coverArt) {
    coverArt.classList.toggle("playing", isPlaying);
  }
}

function initHls(streamUrl = STREAM_URL) {
  STREAM_URL = streamUrl;
  if (hls) {
    try {
      hls.detachMedia();
      hls.destroy();
    } catch (e) {
      console.warn("HLS teardown warning:", e);
    }
    hls = null;
  }

  audio.pause();
  audio.removeAttribute("src");
  audio.load();

  const isHls = STREAM_URL.includes(".m3u8") || STREAM_URL.includes("/hls");

  if (isHls && window.Hls && Hls.isSupported()) {
    hls = new Hls({ lowLatencyMode: true });
    hls.loadSource(STREAM_URL);
    hls.attachMedia(audio);
    hls.on(Hls.Events.ERROR, (_event, data) => {
      if (data.fatal) {
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            setStatus("Network error — retrying…", true);
            hls.startLoad();
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            setStatus("Playback error — recovering…", true);
            hls.recoverMediaError();
            break;
          default:
            setStatus("Stream unavailable (" + data.details + ")", true);
            hls.destroy();
            hls = null;
        }
      }
    });
    return true;
  } else {
    audio.src = STREAM_URL;
    audio.load();
    return true;
  }
}

function changeStream(newStreamUrl) {
  if (!newStreamUrl) return;
  const wasPlaying = !audio.paused;
  STREAM_URL = newStreamUrl;
  hasStarted = true;
  initHls(newStreamUrl);
  if (wasPlaying) {
    audio.play().catch((err) => setStatus("Unable to start playback: " + err.message, true));
  } else {
    setStatus("Station stream updated. Click play to listen.");
  }
}

async function play() {
  if (!hasStarted) {
    hasStarted = true;
    if (!initHls()) return;
  }
  try {
    await audio.play();
  } catch (err) {
    setStatus("Unable to start playback: " + err.message, true);
  }
}

playBtn.addEventListener("click", () => {
  if (audio.paused) play(); else audio.pause();
});

muteBtn.addEventListener("click", () => {
  audio.muted = !audio.muted;
});

volumeSlider.addEventListener("input", (e) => {
  audio.volume = Number(e.target.value) / 100;
  audio.muted = false;
});
audio.volume = 0.7;

const visualizer = document.getElementById("visualizer");
const bars = visualizer ? visualizer.querySelectorAll(".bar") : [];
let visualizerInterval = null;

function animateVisualizer() {
  if (!audio.paused && !audio.muted && audio.volume > 0) {
    bars.forEach((bar) => {
      const targetHeight = Math.floor(Math.random() * 90) + 10;
      bar.style.height = `${targetHeight}%`;
    });
  } else {
    bars.forEach((bar) => {
      bar.style.height = "4px";
    });
  }
}

function startVisualizer() {
  if (!visualizerInterval) {
    visualizerInterval = setInterval(animateVisualizer, 100);
  }
}

function stopVisualizer() {
  if (visualizerInterval) {
    clearInterval(visualizerInterval);
    visualizerInterval = null;
  }
  bars.forEach((bar) => {
    bar.style.height = "4px";
  });
}

audio.addEventListener("playing", () => {
  setStatus("");
  setPlayingUI(true);
  startVisualizer();
});
audio.addEventListener("pause", () => {
  setPlayingUI(false);
  stopVisualizer();
});
audio.addEventListener("waiting", () => setStatus("Buffering…"));
audio.addEventListener("error", () => setStatus("Playback error.", true));
audio.addEventListener("timeupdate", () => {
  timeDisplay.textContent = formatTime(audio.currentTime) + " / Live";
});
