import { describe, it, expect } from "vitest";
import { createRequire } from "module";

// formatters.js is a plain UMD-style script (loaded via <script src> in the
// browser, no bundler), so we load it the same way Node would load any
// CommonJS module rather than via ESM `import`.
const require = createRequire(import.meta.url);
const { formatTime, computeDislikedPagination, addToHistory, formatStationLabel, findStationByArtist } = require("../Script/formatters.js");

describe("formatTime", () => {
  it("formats seconds under a minute", () => {
    expect(formatTime(5)).toBe("0:05");
  });

  it("formats minutes and seconds", () => {
    expect(formatTime(125)).toBe("2:05");
  });

  it("pads single-digit seconds", () => {
    expect(formatTime(61)).toBe("1:01");
  });

  it("returns 0:00 for zero", () => {
    expect(formatTime(0)).toBe("0:00");
  });

  it("returns 0:00 for negative input", () => {
    expect(formatTime(-5)).toBe("0:00");
  });

  it("returns 0:00 for non-finite input", () => {
    expect(formatTime(Infinity)).toBe("0:00");
    expect(formatTime(NaN)).toBe("0:00");
  });
});

describe("computeDislikedPagination", () => {
  it("hides the pager when everything fits on one page", () => {
    const result = computeDislikedPagination(3, 5, 1);
    expect(result.hidden).toBe(true);
    expect(result.totalPages).toBe(1);
  });

  it("hides the pager when total exactly equals page size", () => {
    const result = computeDislikedPagination(5, 5, 1);
    expect(result.hidden).toBe(true);
  });

  it("computes total pages and disables prev on the first page", () => {
    const result = computeDislikedPagination(11, 5, 1);
    expect(result.totalPages).toBe(3);
    expect(result.hidden).toBe(false);
    expect(result.prevDisabled).toBe(true);
    expect(result.nextDisabled).toBe(false);
  });

  it("disables next on the last page", () => {
    const result = computeDislikedPagination(11, 5, 3);
    expect(result.prevDisabled).toBe(false);
    expect(result.nextDisabled).toBe(true);
  });

  it("enables both prev and next on a middle page", () => {
    const result = computeDislikedPagination(11, 5, 2);
    expect(result.prevDisabled).toBe(false);
    expect(result.nextDisabled).toBe(false);
  });

  it("never reports fewer than 1 total page, even when total is 0", () => {
    const result = computeDislikedPagination(0, 5, 1);
    expect(result.totalPages).toBe(1);
    expect(result.hidden).toBe(true);
  });
});

describe("addToHistory", () => {
  it("prepends the new entry", () => {
    const result = addToHistory([{ title: "A" }], { title: "B" }, 5);
    expect(result[0]).toEqual({ title: "B" });
    expect(result[1]).toEqual({ title: "A" });
  });

  it("moves duplicate track to top as the most recent entry", () => {
    const existing = [{ artist: "Galglatz (גלגלצ)", title: "Song B" }, { artist: "Galglatz (גלגלצ)", title: "Song A" }];
    const result = addToHistory(existing, { artist: "Galglatz (גלגלצ)", title: "Song A" }, 5);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ artist: "Galglatz (גלגלצ)", title: "Song A" });
    expect(result[1]).toEqual({ artist: "Galglatz (גלגלצ)", title: "Song B" });
  });

  it("caps the list at the given limit, dropping the oldest entries", () => {
    const history = [{ title: "1" }, { title: "2" }, { title: "3" }];
    const result = addToHistory(history, { title: "new" }, 3);
    expect(result).toHaveLength(3);
    expect(result.map((h) => h.title)).toEqual(["new", "1", "2"]);
  });

  it("does not mutate the original array", () => {
    const original = [{ title: "A" }];
    addToHistory(original, { title: "B" }, 5);
    expect(original).toEqual([{ title: "A" }]);
  });

  it("works from an empty history", () => {
    const result = addToHistory([], { title: "first" }, 5);
    expect(result).toEqual([{ title: "first" }]);
  });
});

describe("formatStationLabel", () => {
  it("formats station with name, frequency, and genre", () => {
    const label = formatStationLabel({ name: "AI Stream Radio", frequency: "107.9 FM", genre: "Cyberpunk" });
    expect(label).toBe("AI Stream Radio (107.9 FM - Cyberpunk)");
  });

  it("formats selected station with check mark", () => {
    const label = formatStationLabel({ name: "AI Stream Radio", frequency: "107.9 FM", genre: "Cyberpunk" }, true);
    expect(label).toBe("✓ AI Stream Radio (107.9 FM - Cyberpunk)");
  });

  it("formats station without genre", () => {
    const label = formatStationLabel({ name: "SomaFM", frequency: "Online" });
    expect(label).toBe("SomaFM (Online)");
  });

  it("handles null or undefined station gracefully", () => {
    expect(formatStationLabel(null)).toBe("Unknown Station");
    expect(formatStationLabel(undefined)).toBe("Unknown Station");
  });
});

describe("findStationByArtist", () => {
  const stations = [
    { id: 1, name: "Galglatz (גלגלצ)" },
    { id: 6, name: "Metal Detector" },
    { id: 8, name: "WQXR 105.9 FM Classical" },
  ];

  it("finds station by exact or substring artist match", () => {
    expect(findStationByArtist("Galglatz Live (גלגלצ)", stations)?.id).toBe(1);
    expect(findStationByArtist("WQXR Classical NY", stations)?.id).toBe(8);
    expect(findStationByArtist("Metal Detector Broadcast", stations)?.id).toBe(6);
  });

  it("returns null for unknown artist", () => {
    expect(findStationByArtist("Unknown Indie Band", stations)).toBe(null);
  });
});
