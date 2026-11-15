import pandas as pd
import pytest
from app.utils.errors import TerraFlareError
from app.utils.obs_filter import FilteredRepo, parse_bbox


class _Repo:
    def get_observations(self, region_id=None, start=None, end=None, sensors=None, valid_only=True):
        return pd.DataFrame({"lat": [10.0, 50.0, 10.5], "lon": [20.0, 20.0, 20.5],
                             "sensor_family": ["VIIRS", "VIIRS", "MODIS"]})

    data_version = "x"


def test_bbox_filters_points():
    df = FilteredRepo(_Repo(), "19,9,21,11").get_observations()
    assert len(df) == 2 and df["lat"].max() < 11


def test_sensor_filter():
    df = FilteredRepo(_Repo(), None, "modis").get_observations()
    assert list(df["sensor_family"]) == ["MODIS"]


def test_delegates_other_attributes():
    assert FilteredRepo(_Repo()).data_version == "x"


@pytest.mark.parametrize("bad", ["1,2,3", "a,b,c,d", "10,0,5,1", "0,0,200,10"])
def test_bad_bbox_rejected(bad):
    with pytest.raises(TerraFlareError):
        parse_bbox(bad)