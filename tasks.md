# Frontend refactor tasks

## High priority

- [x] Split `app/static/app.js` into modules by concern: `player.js` (audio/HLS
      playback), `rating.js` (thumbs up/down + skip-on-dislike), `disliked.js`
      (paginated disliked-songs list), and a small `main.js` that wires them
      together on page load.
- [x] Add frontend unit tests (Vitest) for the pure logic pieces:
      `formatTime`, pagination math in `renderDislikedSongs`, and the
      history-tracking behavior in `applyMetadata`.
- [x] Clickable station navigation: make station names in "Previous tracks" and "Songs
      you disliked" cards interactive. Clicking a station switches to it, begins playback,
      and updates the station selector dropdown with a `✓` checkmark indicator on the selected station.
- [x] Organize `app/static/` subdirectories: move JavaScript modules into
      `app/static/Script/`, image assets (`default-cover.svg`, `logo.png`) into
      `app/static/Images/`, and stylesheet (`style.css`) into `app/static/CSS/`.
- [x] Add a shared `apiFetch(url, opts)` helper to remove the duplicated
      try/fetch/throw-on-!ok/catch-and-warn pattern currently repeated in
      `fetchRatingSummary`, `setRating`, `fetchDislikedSongs`, and
      `pollMetadata`.

## Medium priority

- [x] Remove dead code in `applyMetadata`: `const prev = history[0];` is
      computed but never used.
- [x] Pull inlined API path strings (`"/songs/rating"`, `"/songs/disliked"`)
      into named constants alongside `STREAM_URL`/`METADATA_URL`.
- [x] Add a shared `renderList(container, items, toHtml, emptyMessage)`
      helper to collapse the duplicated `<li>`-building logic in
      `renderHistory` and `renderDislikedSongs`.

## Lower priority / nice-to-have

- [ ] (Skip for now) Move to ES modules / a bundler — not worth it until the
      codebase grows further.
- [ ] (Skip for now) Serve frontend config constants (`DISLIKED_PAGE_SIZE`,
      `METADATA_POLL_MS`, `HISTORY_LIMIT`) from the backend instead of
      hardcoding them in JS — speculative, revisit if they change often.
- [ ] (Skip for now) Split `style.css` further — not worth it at current size.
