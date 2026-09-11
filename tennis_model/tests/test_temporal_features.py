"""Prefix, saved-state and invalid-evidence tests for the temporal corrections."""

import pickle
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest
from tennis_model.data.style_history import StyleHistory
from tennis_model.model.features import H2HState
from tennis_model.model.predict import TennisPredictor
from tennis_model.points.serve_return import ServeReturnState, run_serve_return
from tennis_model.ratings.build import RatingState


def charts(extra=False):
    metadata, overview = [], []
    for i in range(1, 4 if extra else 3):
        metadata.append({'match_id': str(i), 'Date': 20250100 + i,
                         'Player 1': 'Alfa One', 'Player 2': 'Bravo Two'})
        for player, ace in [('Alfa One', 15), ('Bravo Two', 3)]:
            overview.append({'match_id': str(i), 'player': player, 'set': 'Total',
                             'serve_pts': 150, 'return_pts': 150, 'aces': ace * i,
                             'first_won': 50, 'second_won': 40})
    return pd.DataFrame(metadata), {'stats-Overview': pd.DataFrame(overview)}


def test_chart_current_day_exclusion_threshold_and_future_append():
    meta, tables = charts()
    history = StyleHistory('atp', meta, tables, 'a' * 64)
    assert history.snapshot('2025-01-02').profile('alfa one') == {}
    assert history.snapshot('2025-01-02').counts('alfa one') == (150., 1)
    snap = history.snapshot('2025-01-03')
    assert snap.counts('alfa one') == (300., 2)
    assert snap.profile('alfa one')['style_serve_dom'] == .15
    later = StyleHistory('atp', *charts(extra=True), 'a' * 64)
    assert later.snapshot('2025-01-03') == snap
    pairs = pd.DataFrame({'date': pd.to_datetime(['2025-01-02','2025-01-03']),
                          'winner_name':['Alfa One'] * 2, 'loser_name':['Bravo Two'] * 2})
    result = later.pair_features(pairs)
    assert list(result.has_style) == [0, 1]
    assert result.style_serve_dom_diff.iloc[1] == pytest.approx(.12)
    with pytest.raises(FrozenInstanceError):
        snap.cutoff = '2099-01-01'
    mutable = snap.profile('alfa one')
    mutable['style_serve_dom'] = 999
    assert snap.profile('alfa one')['style_serve_dom'] == .15


def test_ambiguous_chart_metadata_and_conflicting_stats_are_excluded():
    meta, tables = charts()
    bad = pd.concat([meta, meta.iloc[:1].assign(Date=20240202)], ignore_index=True)
    history = StyleHistory('atp', bad, tables)
    assert history.exclusions['ambiguousMetadataRows'] == 2
    assert not history.snapshot('2025-02-01').profile('alfa one')
    duplicate = tables['stats-Overview'].iloc[:1].assign(aces=999)
    tables['stats-Overview'] = pd.concat([tables['stats-Overview'], duplicate], ignore_index=True)
    history = StyleHistory('atp', meta, tables)
    assert history.exclusions['conflictingMatches'] == 1
    assert not history.snapshot('2025-02-01').profile('alfa one')
    with pytest.raises(ValueError, match='no match metadata'):
        StyleHistory('atp', pd.DataFrame(), tables)


def test_saved_style_features_ignore_current_global_profiles(monkeypatch):
    import tennis_model.data.charting as charting

    snapshot = StyleHistory('atp', *charts(), 'a' * 64).snapshot('2025-01-03')
    elo = RatingState()
    elo.last_date = np.datetime64('2025-01-03')
    pred = TennisPredictor(None, None, elo, ServeReturnState(), H2HState({}), {},
                           style_snapshot=snapshot)
    restored = pickle.loads(pickle.dumps(pred))
    monkeypatch.setattr(charting, 'build_profiles', lambda tour: pytest.fail('global style read'))
    before = restored.features('Alfa One','Bravo Two',as_of='2025-01-04')
    after = restored.features('Alfa One','Bravo Two',as_of='2025-02-01')
    for c in [c for c in before if c.startswith('style_')] + ['has_style']:
        pd.testing.assert_series_equal(before[c], after[c])
    assert before.style_serve_dom_diff.iloc[0] == pytest.approx(.12)


def matches():
    df = pd.DataFrame({
        'date': pd.to_datetime(['2025-01-01','2025-01-01','2025-02-01','2025-04-01']),
        'winner_name':['A','C','A','A'], 'loser_name':['B','D','B','B'],
        'surface_b':['Hard']*4, 'best_of':[3]*4, 'completed':[True]*4, 'has_stats':[True]*4,
        'w_svpt':[100.]*4, 'l_svpt':[100.]*4,
        'w_1stWon':[40.,50.,60.,50.], 'w_2ndWon':[20.]*4,
        'l_1stWon':[35.,40.,40.,40.], 'l_2ndWon':[20.]*4,
        'stats_availability_basis':['played_date']*4,
    })
    df['stats_available_at'] = df.date
    return df


def test_serve_prior_is_prefix_only_batched_and_population_controlled():
    df = matches()
    state, full = run_serve_return(df)
    _, prefix = run_serve_return(df.iloc[:3])
    pd.testing.assert_frame_equal(full.iloc[:3], prefix)
    assert full.prior_avg.iloc[0] == full.prior_avg.iloc[1] == .62
    assert full.prior_avg.iloc[2] == pytest.approx(245/400)
    assert full.prior_service_points.iloc[2] == 400
    perturbed = df.copy()
    perturbed.loc[3, 'w_1stWon'] = 5.
    _, changed = run_serve_return(perturbed)
    pd.testing.assert_frame_equal(full.iloc[:4], changed.iloc[:4])
    _, controlled = run_serve_return(df, baseline_df=df.iloc[:2])
    assert controlled.prior_service_points.iloc[3] == 400
    assert state.prior_state.points == 800


def test_saved_serve_state_matches_later_prefix_without_mutation():
    df = matches()
    state, _ = run_serve_return(df.iloc[:3])
    restored = pickle.loads(pickle.dumps(state))
    digest = pickle.dumps(restored)
    _, full = run_serve_return(df)
    view = restored.at(df.date.iloc[3])
    pa, pb = view.point_probs('A','B','Hard')
    assert pa == pytest.approx(full.pa_serve.iloc[3], abs=1e-12)
    assert pb == pytest.approx(full.pb_serve.iloc[3], abs=1e-12)
    assert view.serve_points('A') == pytest.approx(full.w_srv_pts.iloc[3], abs=1e-12)
    view.point_probs('B','A','Hard')
    with pytest.raises(ValueError, match='cannot mutate'):
        view._decay_to('A', df.date.iloc[3])
    assert pickle.dumps(restored) == digest


def test_unknown_availability_and_invalid_counts_never_enter_prior():
    df = matches().drop(columns=['stats_available_at','stats_availability_basis'])
    st, out = run_serve_return(df)
    assert st.prior_state.points == 0
    assert st.prior_state.excluded_unknown_time == 4
    assert (out.prior_avg == .62).all()
    known = matches()
    known.loc[0,'w_1stWon'] = 999
    st, out = run_serve_return(known)
    assert st.prior_state.excluded_invalid_stats == 1
    assert st.prior_state.points == 600
    assert out.w_srv_pts.iloc[2] == 0  # malformed stats did not enter player state either


def test_changing_prior_preserves_absolute_adjusted_evidence():
    st = ServeReturnState(avg=.62, base={'Hard':.62})
    st._add('A','Hard',100, .7, 100, .4)
    before = (dict(st.gsw), dict(st.grw), dict(st.gsp))
    k = st.params.serve_shrinkage_points
    assert st.global_serve_skill('A') == pytest.approx((70 - .62 * 100)/(100 + k))
    st.avg = .55
    st.base['Hard'] = .55
    assert st.global_serve_skill('A') == pytest.approx((70 - .55 * 100)/(100 + k))
    assert before == (st.gsw, st.grw, st.gsp)


def test_chart_aliases_use_the_same_normalized_identity_table_as_match_rows(monkeypatch):
    from tennis_model import config

    meta, tables = charts()
    meta['Player 1'] = 'Old Alias'
    tables['stats-Overview']['player'] = tables['stats-Overview'].player.replace('Alfa One', 'Old Alias')
    monkeypatch.setitem(config.PLAYER_ALIASES, 'old alias', 'Alfa One')
    history = StyleHistory('atp', meta, tables, 'a'*64)
    assert history.snapshot('2025-01-03').profile('alfa one')['style_serve_dom'] == .15
    pair = pd.DataFrame({'date':pd.to_datetime(['2025-01-03']),
                         'winner_name':['Alfa One'],'loser_name':['Bravo Two']})
    assert history.pair_features(pair).has_style.iloc[0] == 1


def test_delayed_event_end_prior_survives_serialization_and_later_date_query():
    df = matches()
    df.loc[:1, 'stats_available_at'] = pd.Timestamp('2025-01-07')
    df.loc[:1, 'stats_availability_basis'] = 'event_end'
    state, _ = run_serve_return(df.iloc[:2])
    saved = pickle.loads(pickle.dumps(state))
    before = pickle.dumps(saved)
    assert len(saved.pending_prior_observations) == 2
    assert saved.at('2025-01-07').prior_state.points == 0  # strict before, not same day
    assert saved.at('2025-01-08').prior_state.points == 400
    _, full = run_serve_return(df)
    view = saved.at(df.date.iloc[2])
    assert view.avg == pytest.approx(full.prior_avg.iloc[2], abs=1e-12)
    assert view.point_probs('A','B','Hard') == pytest.approx(
        (full.pa_serve.iloc[2], full.pb_serve.iloc[2]), abs=1e-12)
    assert pickle.dumps(saved) == before
