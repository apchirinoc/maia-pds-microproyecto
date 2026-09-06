export function lerpColor(colorA: string, colorB: string, t: number): string {
  const clampedT = Math.min(1, Math.max(0, t))
  const a = Number.parseInt(colorA.slice(1), 16)
  const b = Number.parseInt(colorB.slice(1), 16)
  const ar = (a >> 16) & 0xff
  const ag = (a >> 8) & 0xff
  const ab = a & 0xff
  const br = (b >> 16) & 0xff
  const bg = (b >> 8) & 0xff
  const bb = b & 0xff

  const rr = Math.round(ar + (br - ar) * clampedT)
  const rg = Math.round(ag + (bg - ag) * clampedT)
  const rb = Math.round(ab + (bb - ab) * clampedT)

  return `#${((1 << 24) + (rr << 16) + (rg << 8) + rb).toString(16).slice(1)}`
}

export function logScale(value: number, maxValue: number): number {
  if (maxValue <= 0) return 0
  return Math.log1p(value) / Math.log1p(maxValue)
}

export function sqrtRadius(value: number, maxValue: number, minRadius = 3, maxRadius = 22): number {
  if (maxValue <= 0) return minRadius
  const t = Math.sqrt(value) / Math.sqrt(maxValue)
  return minRadius + t * (maxRadius - minRadius)
}
