import { percentileScaler, RADAR_AXES, type RadarAxis } from "@/lib/ui";

/** The subset of profiles.json consumed by both the comparison and dossier radars. */
export type RadarProfile = {
  name: string;
  servePct: number;
  returnPct: number;
  eloHard: number;
  eloClay: number;
  eloGrass: number;
  style: Record<string, number | null>;
};

export type RadarScaler = (value: number) => number;

export function readRadarValue(profile: RadarProfile, axis: RadarAxis): number | null {
  const value = axis.source === "style"
    ? profile.style?.[axis.key]
    : (profile as unknown as Record<string, number | null>)[axis.key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** One percentile scaler per shared radar axis, fitted to the active tour's profile field. */
export function buildRadarScalers(profiles: RadarProfile[]): RadarScaler[] {
  return RADAR_AXES.map((axis) => {
    const values = profiles
      .map((profile) => readRadarValue(profile, axis))
      .filter((value): value is number => value != null);
    return percentileScaler(values);
  });
}

/** Radar consumes a series array; return the one-player form used by a dossier. */
export function profileRadarSeries(
  profile: RadarProfile,
  scalers: RadarScaler[],
  color: string,
): { name: string; color: string; values: number[] }[] {
  return [{
    name: profile.name,
    color,
    values: RADAR_AXES.map((axis, index) => {
      const raw = readRadarValue(profile, axis);
      return raw == null || !scalers[index] ? 0 : scalers[index](raw);
    }),
  }];
}

/** Explicit URL selections never fall through to an unrelated player. */
export function resolveProfileSelection(
  names: string[],
  urlName: string | null,
  current: string,
): string {
  if (!names.length) return "";
  if (urlName !== null) return names.includes(urlName) ? urlName : "";
  return names.includes(current) ? current : names[0];
}
