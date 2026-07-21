// Pure, DOM-free helpers shared across the frontend scripts. Kept separate
// from the DOM-wiring files so they can be unit tested directly (see
// app/static/tests/) without needing a browser or jsdom.
(function (global) {
  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m + ":" + String(s).padStart(2, "0");
  }

  // Pure pagination math for the "Songs you disliked" pager.
  function computeDislikedPagination(total, pageSize, page) {
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    return {
      totalPages,
      hidden: total <= pageSize,
      prevDisabled: page <= 1,
      nextDisabled: page >= totalPages,
    };
  }

  // Returns a new history array with `entry` prepended at the top (most recent),
  // removing any older occurrence of the same track to avoid duplicates.
  // Does not mutate the array passed in and caps at `limit`.
  function addToHistory(history, entry, limit) {
    if (!entry || !entry.title) return history;
    const filtered = history.filter(
      (h) => !(h.title === entry.title && (h.artist === entry.artist || !h.artist || !entry.artist))
    );
    const next = [entry, ...filtered];
    if (next.length > limit) next.length = limit;
    return next;
  }

  // Formats station object into a human-readable dropdown option label.
  function formatStationLabel(station, isSelected = false) {
    if (!station || typeof station !== "object") return "Unknown Station";
    const prefix = isSelected ? "✓ " : "";
    const name = station.name || "Station";
    const freq = station.frequency ? ` (${station.frequency}` : "";
    const genreStr = typeof station.genre === "object" && station.genre !== null ? station.genre.name : station.genre;
    const genre = genreStr ? ` - ${genreStr})` : station.frequency ? ")" : "";
    return `${prefix}${name}${freq}${genre}`;
  }

  // Matches a song's artist / station string against the available stations list.
  function findStationByArtist(artistName, stationsList = []) {
    if (!artistName || typeof artistName !== "string" || !stationsList || !stationsList.length) return null;

    const rawTarget = artistName.trim().toLowerCase();
    const normalize = (str) =>
      str
        .toLowerCase()
        .replace(/[^\w\s\u0590-\u05FF]/g, " ")
        .replace(/\s+/g, " ")
        .trim();

    const targetNorm = normalize(artistName);

    // 1. Direct match on raw or normalized name
    let match = stationsList.find((s) => {
      if (!s.name) return false;
      const sRaw = s.name.trim().toLowerCase();
      const sNorm = normalize(s.name);
      return sRaw === rawTarget || sNorm === targetNorm;
    });
    if (match) return match;

    // 2. Substring match on normalized string
    match = stationsList.find((s) => {
      if (!s.name) return false;
      const sNorm = normalize(s.name);
      return (sNorm.length > 0 && targetNorm.includes(sNorm)) || (targetNorm.length > 0 && sNorm.includes(targetNorm));
    });
    if (match) return match;

    // 3. Significant word intersection (words >= 3 chars, ignoring common filler)
    const targetWords = targetNorm.split(" ").filter((w) => w.length >= 3 && w !== "live" && w !== "radio" && w !== "broadcast");
    if (targetWords.length > 0) {
      match = stationsList.find((s) => {
        if (!s.name) return false;
        const sWords = normalize(s.name).split(" ").filter((w) => w.length >= 3);
        return targetWords.some((tw) => sWords.includes(tw));
      });
      if (match) return match;
    }

    // 4. Fallback: match any word token >= 3 characters
    const allTargetWords = targetNorm.split(" ").filter((w) => w.length >= 3);
    return (
      stationsList.find((s) => {
        if (!s.name) return false;
        const sNorm = normalize(s.name);
        return allTargetWords.some((w) => sNorm.includes(w));
      }) || null
    );
  }

  const helpers = { formatTime, computeDislikedPagination, addToHistory, formatStationLabel, findStationByArtist };

  if (typeof module === "object" && module.exports) {
    module.exports = helpers;
  } else {
    Object.assign(global, helpers);
  }
})(typeof window !== "undefined" ? window : globalThis);
