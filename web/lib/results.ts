export type ResultFilter = "all" | "called" | "upsets";

export type ResultLike = { upset: boolean };

export function resultCounts(rows: ResultLike[]) {
  const upsets = rows.filter((row) => row.upset).length;
  return { all: rows.length, called: rows.length - upsets, upsets };
}

export function filterResults<T extends ResultLike>(rows: T[], filter: ResultFilter): T[] {
  if (filter === "all") return rows;
  return rows.filter((row) => (filter === "upsets" ? row.upset : !row.upset));
}
