"""Convenience CLI for ad-hoc predictions and draw projections.

  PYTHONPATH=src python -m tennis_model.cli predict "Jannik Sinner" "Carlos Alcaraz" --surface Hard --bo 5
  PYTHONPATH=src python -m tennis_model.cli project-slam "Wimbledon" 2025
  PYTHONPATH=src python -m tennis_model.cli field "Jannik Sinner" "Carlos Alcaraz" ... --surface Clay --bo 5

Requires a trained predictor (run `python -m tennis_model.pipeline` first).
"""

from __future__ import annotations

import argparse

from .model.predict import TennisPredictor


def _predict(p: TennisPredictor, args) -> None:
    r = p.predict(args.a, args.b, surface=args.surface, best_of=args.bo)
    print(f"\n{r['a']} vs {r['b']}  [{r['surface']}, Bo{r['best_of']}]")
    print(f"  P({r['a']}) = {r['p_a']:.1%}   P({r['b']}) = {r['p_b']:.1%}")
    print(f"  components: Elo blend {r['p_blend']:.1%}, point model {r['p_point']:.1%}")
    print("  set-score distribution:")
    for k, v in r["set_dist"].items():
        print(f"    {k}: {v:.1%}")


def _project_slam(p: TennisPredictor, args) -> None:
    from .data.results import load_matches
    from .sim.draws import find_tournament, reconstruct_draw
    from .sim.simulate import simulate_tournament

    df = load_matches()
    ids = find_tournament(df, args.name, args.year)
    if not ids:
        print(f"No tournament matching '{args.name}' in {args.year}")
        return
    draw = reconstruct_draw(df, ids[0])
    print(f"\n{draw['name']} {args.year} ({draw['surface']}, Bo{draw['best_of']}, "
          f"draw {len(draw['slots'])}) — actual champion: {draw['champion']}")
    sim = simulate_tournament(p, draw["slots"], surface=draw["surface"],
                              best_of=draw["best_of"], n_sims=args.sims, seed=1)
    print(sim.head(args.top)[["player", "SF", "F", "Champion"]].to_string(index=False))


def _field(p: TennisPredictor, args) -> None:
    from .sim.simulate import project_field
    sim = project_field(p, args.players, surface=args.surface, best_of=args.bo,
                        n_sims=args.sims, seed=1)
    print(f"\nProjected field ({args.surface}, Bo{args.bo}), Elo-seeded:")
    print(sim.head(args.top)[["player", "SF", "F", "Champion"]].to_string(index=False))


def main():
    ap = argparse.ArgumentParser(prog="tennis_model.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("predict", help="single match win probability + scoreline")
    sp.add_argument("a"); sp.add_argument("b")
    sp.add_argument("--surface", default="Hard", choices=["Hard", "Clay", "Grass"])
    sp.add_argument("--bo", type=int, default=3, choices=[3, 5])

    sp = sub.add_parser("project-slam", help="simulate a real (reconstructed) Slam draw")
    sp.add_argument("name"); sp.add_argument("year", type=int)
    sp.add_argument("--sims", type=int, default=20000); sp.add_argument("--top", type=int, default=10)

    sp = sub.add_parser("field", help="seed a list of players and simulate a bracket")
    sp.add_argument("players", nargs="+")
    sp.add_argument("--surface", default="Hard", choices=["Hard", "Clay", "Grass"])
    sp.add_argument("--bo", type=int, default=3, choices=[3, 5])
    sp.add_argument("--sims", type=int, default=20000); sp.add_argument("--top", type=int, default=10)

    args = ap.parse_args()
    p = TennisPredictor.load()
    {"predict": _predict, "project-slam": _project_slam, "field": _field}[args.cmd](p, args)


if __name__ == "__main__":
    main()
