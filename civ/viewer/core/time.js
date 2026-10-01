// The world's calendar: hours (ticks) to days, seasons and years, and the light of the day.
export const SEASONS = ["spring", "summer", "autumn", "winter"];

export class Calendar {
  constructor(meta) {
    this.tpd = meta.tpd;                    // hours a day
    this.dps = meta.dps;                    // days a season
    this.tpy = meta.tpy;                    // hours a year
    this.nightFrom = meta.night_from ?? meta.tpd - 3;
  }

  // t may be fractional (the replay runs smoothly between recorded hours)
  of(t) {
    const hour = Math.floor(t) % this.tpd, dayIndex = Math.floor(t / this.tpd), s = Math.floor(dayIndex / this.dps);
    const frac = (t % this.tpd) / this.tpd;
    return {
      t, hour, frac,
      day: dayIndex + 1,
      dayOfSeason: dayIndex % this.dps + 1,
      season: SEASONS[s % 4], seasonIndex: s % 4,
      seasonFrac: (dayIndex % this.dps + frac) / this.dps,
      year: Math.floor(s / 4) + 1,
      night: hour >= this.nightFrom,
      part: hour < 2 ? "dawn" : hour < 5 ? "morning" : hour < this.nightFrom - 1 ? "afternoon" : hour < this.nightFrom ? "evening" : "night",
    };
  }

  label(t) {
    const w = this.of(t);
    return `Day ${w.day} · ${w.part} · ${w.season}, year ${w.year}`;
  }

  years(hours) { return hours / this.tpy; }
}
