import pickle

import numpy as np
import pandas as pd
import pytest

from historical_candidates import (
    AppearanceState, CappedParams, CappedServeState, appearance_flags, neutral_absence,
)


def history():
    return pd.DataFrame({'winner_name':['A','B','A','C'],'loser_name':['B','C','B','A'],
                         'date':pd.to_datetime(['2000-01-01','2000-01-02','2001-02-01','2001-02-02'])})


def frame():
    return pd.DataFrame({'rest_diff':[60.,-60.,12.,1.],
                         'log_days_since_diff':[5.,-5.,.5,.1],
                         'layoff_flag_diff':[1,-1,1,0],'other':[1.,2.,3.,4.]})


def test_absence_only_neutralizes_unknown_pair_not_real_returner():
    _,flags=appearance_flags(history())
    assert flags.tolist()==[True,True,False,False]
    out=neutral_absence(frame(),flags)
    np.testing.assert_array_equal(out['other'],frame()['other'])
    assert (out.iloc[:2,:3]==0).all().all()
    pd.testing.assert_frame_equal(out.iloc[2:],frame().iloc[2:])


@pytest.mark.parametrize('cut',[1,2,3])
def test_appearance_serialized_continuation_and_query_parity(cut):
    state,flags=appearance_flags(history().iloc[:cut])
    restored=pickle.loads(pickle.dumps(state));before=pickle.dumps(restored)
    row=history().iloc[cut]
    query=restored.transform_query(frame().iloc[[cut]],row.winner_name,row.loser_name,row.date)
    assert pickle.dumps(restored)==before
    _,tail=appearance_flags(history().iloc[cut:],restored)
    _,whole=appearance_flags(history())
    np.testing.assert_array_equal(np.r_[flags,tail],whole)
    pd.testing.assert_frame_equal(query,neutral_absence(frame(),whole).iloc[[cut]])


def test_appearance_rejects_past_query_and_outcome_order_irrelevant():
    st,_=appearance_flags(history())
    with pytest.raises(ValueError):st.unknown('A','B','1999-01-01')
    assert st.unknown('A','D','2002-01-01')==st.unknown('D','A','2002-01-01')


@pytest.mark.parametrize('bad',[0,-1,np.nan,np.inf,True])
def test_bad_cap(bad):
    with pytest.raises(ValueError):CappedParams(cap=bad)


def test_cap_preserves_rates_and_caps_global_and_surface_mass():
    s=CappedServeState(params=CappedParams(cap=40))
    s._add('A','Hard',100,.7,30,.4)
    assert s.gsp['A']==s.ssp['Hard']['A']==40
    assert s.gsw['A']==s.ssw['Hard']['A']==28
    assert s.grp['A']==30 and s.grw['A']==12


def test_cap_decayed_serialized_query_and_exchange():
    s=CappedServeState(params=CappedParams(cap=40));t=np.datetime64('2020-01-01')
    s._decay_to('A',t);s._decay_to('B',t)
    s._add('A','Hard',100,.7,100,.4);s._add('B','Hard',70,.6,70,.3)
    restored=pickle.loads(pickle.dumps(s));before=pickle.dumps(restored)
    p=restored.at('2020-07-01').match_prob('A','B','Hard')
    assert p==s.at('2020-07-01').match_prob('A','B','Hard')
    assert p+restored.at('2020-07-01').match_prob('B','A','Hard')==pytest.approx(1)
    assert restored.at('2020-07-01').serve_points('A')<40
    assert pickle.dumps(restored)==before
    with pytest.raises(ValueError):restored.at('2020-07-01')._add('A','Hard',100,.7,100,.4)


def test_no_cap_default_cannot_be_accidentally_instantiated():
    with pytest.raises(ValueError):CappedServeState()


def test_empty_appearance_state_is_not_a_known_absence():
    s=AppearanceState()
    assert s.unknown('A','B','2020-01-01')
