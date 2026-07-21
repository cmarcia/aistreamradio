// Configurable page size for the "Songs you disliked" list. Bump this up
// (or down) whenever the desired page size changes — nothing else in the
// pagination logic needs to change.
const DISLIKED_PAGE_SIZE = 5;

const dislikedList = document.getElementById("dislikedList");
const dislikedPager = document.getElementById("dislikedPager");
const dislikedPrevBtn = document.getElementById("dislikedPrevBtn");
const dislikedNextBtn = document.getElementById("dislikedNextBtn");
const dislikedPageInfo = document.getElementById("dislikedPageInfo");
let dislikedPage = 1;

function dislikedSongToHtml(s) {
  const thumb = s.cover_image
    ? `<img class="thumb" src="${escapeHtml(s.cover_image)}" alt="">`
    : `<img class="thumb" src="/static/Images/default-cover.svg" alt="">`;
  const st = (window.stationsList && findStationByArtist(s.artist, window.stationsList));
  const stId = st ? st.id : "";
  return `<li>${thumb}<button type="button" class="station-click-btn" data-station-id="${stId}" data-artist="${escapeHtml(s.artist)}" title="Click to tune into ${escapeHtml(s.artist)}"><b>${escapeHtml(s.artist)}</b></button><span class="separator">:</span> <i>${escapeHtml(s.title)}</i></li>`;
}

function renderDislikedSongs(page) {
  renderList(dislikedList, page.items, dislikedSongToHtml, "You haven't disliked any tracks yet.");

  const pagination = computeDislikedPagination(page.total, page.page_size, page.page);
  dislikedPager.hidden = pagination.hidden;
  dislikedPageInfo.textContent = "Page " + page.page + " of " + pagination.totalPages;
  dislikedPrevBtn.disabled = pagination.prevDisabled;
  dislikedNextBtn.disabled = pagination.nextDisabled;
}

async function fetchDislikedSongs() {
  const params = new URLSearchParams({
    listener_id: listenerId,
    page: dislikedPage,
    page_size: DISLIKED_PAGE_SIZE,
  });
  const page = await apiFetchOrWarn(
    API_PATHS.DISLIKED + "?" + params.toString(),
    undefined,
    "disliked songs fetch failed"
  );
  if (page) renderDislikedSongs(page);
}

// Called by rating.js right after a new dislike is recorded, so the
// listener sees their newest dislike at the top of the list.
function resetDislikedToFirstPage() {
  dislikedPage = 1;
  fetchDislikedSongs();
}

dislikedPrevBtn.addEventListener("click", () => {
  if (dislikedPage > 1) {
    dislikedPage--;
    fetchDislikedSongs();
  }
});
dislikedNextBtn.addEventListener("click", () => {
  dislikedPage++;
  fetchDislikedSongs();
});
