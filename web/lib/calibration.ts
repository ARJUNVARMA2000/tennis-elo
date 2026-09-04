export type CalibrationBin = { bin: string; n: number; pred: number; actual: number };

/** Descriptive Wilson interval using the published (possibly rounded) observed rate.
 * https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm
 * This binomial approximation does not correct dependence between tennis matches.
 */
export function calibrationInterval(rate: number, n: number): [number, number] | null {
  if (!Number.isInteger(n) || n <= 0 || !Number.isFinite(rate) || rate < 0 || rate > 1) return null;
  const z = 1.959963984540054;
  const denominator = 1 + z * z / n;
  const center = (rate + z * z / (2 * n)) / denominator;
  const half = z * Math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / denominator;
  return [Math.max(0, center - half), Math.min(1, center + half)];
}
