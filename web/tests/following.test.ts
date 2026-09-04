import { describe, expect, it } from "vitest";
import { followsPlayer, followingStorageKey, parseFollowing, toggleFollowing } from "@/lib/following";

describe("followed players", () => {
  it("isolates tours and tolerates malformed saved preferences", () => {
    expect(followingStorageKey("atp")).not.toBe(followingStorageKey("wta"));
    for (const raw of [null, "broken", "{}", "null"]) expect(parseFollowing(raw)).toEqual([]);
    expect(parseFollowing('[null, 1, "", "  ", "João Fonseca", "Joao Fonseca"]')).toEqual(["João Fonseca"]);
  });
  it("matches normalized names and removes the existing identity on toggle", () => {
    const names = toggleFollowing([], "João Fonseca");
    expect(followsPlayer(names, "Joao Fonseca")).toBe(true);
    expect(followsPlayer(names, "Fonseca")).toBe(false);
    expect(toggleFollowing(names, "Joao Fonseca")).toEqual([]);
    expect(toggleFollowing(names, "")).toEqual(names);
  });
});
