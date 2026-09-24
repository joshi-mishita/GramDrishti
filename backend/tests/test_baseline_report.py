from gramdrishti.data import config
from gramdrishti.data.config import window_bounds
from gramdrishti.verify import baseline_report

from .conftest import needs_oracle


@needs_oracle
def test_report_runs_on_calib_only(monkeypatch):
    requested = []
    real_select = config.select_window

    def spy(df, name, date_col, **kw):
        requested.append(name)
        return real_select(df, name, date_col, **kw)

    modules = ("gramdrishti.verify.baseline_report", "gramdrishti.models.bias",
               "gramdrishti.models.baselines")
    for mod in modules:
        monkeypatch.setattr(f"{mod}.select_window", spy)
    rep = baseline_report.build_report()
    assert "TEST" not in requested
    assert set(requested) == {"TRAIN", "CALIB"}
    assert len(rep.scores) == 3 * 5 * 5 and len(rep.events) == 3 * 5
    assert rep.n_eval_dates == (window_bounds("CALIB")[1] - window_bounds("CALIB")[0]).days + 1
    assert rep.baselines.bias.data_max_date <= window_bounds("TRAIN")[1]
    text = baseline_report.format_report(rep)
    assert "MAE B0" in text and "POD" in text and "synthetic" in text


def test_report_refuses_real_mode(monkeypatch):
    monkeypatch.setenv("DATA_MODE", "real")
    try:
        baseline_report.build_report()
    except NotImplementedError as e:
        assert "mock mode" in str(e)
    else:
        raise AssertionError("expected NotImplementedError")
