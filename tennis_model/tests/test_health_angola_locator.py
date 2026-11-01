"""Replay Angola's sponsor/city locator gap through acquisition, projection and gate."""
import copy
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.config import PLAYER_ALIASES
from tennis_model.data.names import name_key
from tennis_model.model import upcoming
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model.data import draws, draws_official, draws_wiki, events, health, live, source_audit

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/angola_locator_20261101.json').read_text())
EID = '1082-2026'
NOW = CAPTURE['observedAt']
NAME = CAPTURE['event']['name']


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.fromisoformat(NOW.replace('Z', '+00:00')).astimezone(tz)


def bind(monkeypatch, tmp_path, *, reviewed=True, text=None):
    for module in (draws, draws_official, events):
        monkeypatch.setattr(module, 'datetime', Clock)
    for module in (draws, draws_official, events, tournaments, upcoming):
        monkeypatch.setattr(module, 'live_dir', lambda tour: tmp_path)
    from tennis_model.eval import track
    monkeypatch.setattr(track, 'FORECAST_DIR', tmp_path / 'forecasts')
    monkeypatch.setattr(draws_official, 'wta_catalog', lambda year: copy.deepcopy(CAPTURE['catalog']))
    monkeypatch.setattr(draws_official, '_download',
                        lambda url, cache: b'captured' if '/1176/' in url else None)
    monkeypatch.setattr(draws_official, 'extract_pdf_text',
                        lambda body: CAPTURE['pdf']['text'] if text is None else text)
    overrides = copy.deepcopy(draws_official.OFFICIAL_DRAW_ID_OVERRIDES)
    if not reviewed:
        overrides['wta'].pop(EID, None)
    monkeypatch.setattr(draws_official, 'OFFICIAL_DRAW_ID_OVERRIDES', overrides)
    monkeypatch.setattr(draws_wiki, '_download_wiki_meta', lambda *args: None)
    monkeypatch.setattr(draws_wiki, 'fetch_draw', lambda *args: None)
    monkeypatch.setattr(tournaments, 'resolve_surface_info', lambda *a, **kw: ('Hard', 'official'))
    monkeypatch.setattr(tournaments, 'resolve_level', lambda *a, **kw: 'WTA 125')
    observed = [copy.deepcopy(CAPTURE['event'])]
    fields = live.parse_fields(observed, 'womens')
    (tmp_path / 'fields.json').write_text(json.dumps(fields))
    live.parse_upcoming(observed, 'womens').to_csv(tmp_path / 'upcoming.csv', index=False)
    return observed, next(iter(fields.values()))['field']


def project_and_gate(observed, field, cache):
    names = {PLAYER_ALIASES.get(name_key(n), n) for n in field}
    frame = pd.DataFrame(columns=['date', 'tourney_name', 'winner_name', 'loser_name',
                                  'round', 'surface_b', 'best_of', 'tourney_level'])
    frame['date'] = pd.to_datetime(frame['date'])
    cards = tournaments.build_tournaments(_Pred(dict.fromkeys(names, 1500)), frame, 'wta',
                                           build_date=NOW[:10], n_sims=100)
    raw, proof = source_audit.capture_source('wta', observed, NOW)
    data = _healthy_data()
    data['meta'].update(modelPlayerNames=sorted(names), tournamentSourceAudit=proof)
    data['tournaments'] = cards
    data['brackets'] = [{**c, 'rounds': c['bracket']} for c in cards if c.get('bracket')]
    data['upcoming'] = [{'espnId': r.espn_id, 'round': r.round,
                         'playerA': r.playerA, 'playerB': r.playerB, 'pA': .5}
                        for r in upcoming.load_upcoming('wta').itertuples()]
    oc = _oc(data=data)
    oc.update(draw_cache=cache,
              source_audit={'state': 'valid', 'witness': json.loads(raw), 'proof': proof})
    findings = [f for f in health.output_findings('wta', oc, pd.Timestamp(NOW),
                                                 observed_at=pd.Timestamp(NOW))
                if f.code.startswith('output.source_audit.')]
    assert all(health._gate_blocks(f) for f in findings)
    return cards, findings


def test_without_locator_reproduces_missing_source_event(monkeypatch, tmp_path):
    observed, field = bind(monkeypatch, tmp_path, reviewed=False)
    meta = {**live.parse_event_meta(observed)[NAME], 'name': NAME}
    candidates = draws_official.wta_candidate_ids(2026, meta)
    assert next(i + 1 for i, c in enumerate(candidates) if c['id'] == '1176') == 10
    draws.download_tournament_draws(['wta'], events_by_tour={'wta': observed})
    cache = draws.load_tournament_draws('wta')
    cards, findings = project_and_gate(observed, field, cache)
    assert not cache and not cards
    assert [(f.code, f.entity) for f in findings] == [
        ('output.source_audit.event_missing', 'espn:' + EID)]


def test_reviewed_locator_publishes_exact_prestart_bracket(monkeypatch, tmp_path):
    observed, field = bind(monkeypatch, tmp_path)
    # Repeat the acquisition so the persisted source locator/cache path is covered too.
    for _ in range(2):
        draws.download_tournament_draws(['wta'], events_by_tour={'wta': observed})
        cache = draws.load_tournament_draws('wta')
        assert set(cache) == {EID}
        draw = cache[EID]
        assert draw['sourceId'] == '1176' and draw['source'] == 'wta'
        assert draw['evidencePlayers'] == draw['evidenceFieldPlayers'] == 28
        assert len(draw['slots']) == len(set(draw['slots'])) == 32
        assert [n for n in draw['slots'] if n.startswith('Qualifier ')] == [
            'Qualifier 1', 'Qualifier 2', 'Qualifier 3', 'Qualifier 4']
        assert events.load_registry('wta')['events'][EID]['sourceIds']['wta'] == '1176'
        cards, findings = project_and_gate(observed, field, cache)
        assert not findings, [(f.code, f.evidence) for f in findings]
        assert [c['espnId'] for c in cards] == [EID]
        card = cards[0]
        assert card['status'] == 'upcoming' and card['drawStatus'] == 'real'
        assert card['drawSize'] == card['bracketSize'] == 32
        assert card['mainDrawMatchCount'] == 0 and card['projection']
        ordered = [m[s] for m in card['bracket'][0]['matches'] for s in ('a', 'b')]
        assert ordered == draw['slots']
        assert card['drawSourceId'] == '1176'


@pytest.mark.parametrize('mismatch', ['date', 'players'])
def test_reviewed_locator_still_requires_dates_and_players(monkeypatch, tmp_path, mismatch):
    text = CAPTURE['pdf']['text']
    if mismatch == 'date':
        text = text.replace('November 1-8 2026', 'October 1-8 2026')
        assert text != CAPTURE['pdf']['text']
    observed, field = bind(monkeypatch, tmp_path, text=text)
    if mismatch == 'players':
        field = [f'Unrelated Player {i}' for i in range(28)]
    draw, rejected = draws_official.fetch_official_draw(
        'wta', 2026, {**live.parse_event_meta(observed)[NAME], 'name': NAME}, {}, field)
    assert draw is None
    reason = 'calendar overlap is too small' if mismatch == 'date' else 'matches 0/28'
    assert any(f'wta:1176 {reason}' in r for r in rejected)
