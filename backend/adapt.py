import pandas as pd, numpy as np
src = r"C:\Users\shrey\TerraFlare\backend\app\data\processed\firms\obs_clean.parquet"
out = r"C:\Users\shrey\TerraFlare\data\staging_obs_clean.parquet"
df = pd.read_parquet(src)
print(df["product_type"].value_counts(dropna=False).to_dict())
print(df["source_dataset"].value_counts(dropna=False).to_dict())
print(df["daynight"].value_counts(dropna=False).to_dict())

c = pd.DataFrame()
c["obs_id"] = df["record_id"]
c["source_id"] = df["source_dataset"]
c["sensor_family"] = df["sensor_family"]
c["platform"] = df["platform"]
pt = df["product_type"].astype(str).str.upper()
c["processing_stream"] = np.where(pt == "NRT", "NRT", np.where(pt == "SP", "SP", "UNKNOWN"))
c["product_version"] = df["product_version"]
c["ingest_batch_id"] = "main_firms_obs_clean"
c["acq_date"] = df["acq_date"]
c["lat"] = df["lat"]; c["lon"] = df["lon"]
c["is_valid"] = df["is_valid"]
c["qc_flags"] = ""
c["is_synthetic"] = False
c["acq_datetime_utc"] = df["acq_datetime_utc"]
c["local_date"] = (df["acq_datetime_utc"] + pd.to_timedelta(df["lon"] / 15.0, unit="h")).dt.normalize()
c["h3_cell"] = df["h3_cell"]
c["confidence_raw"] = df["confidence_raw"]
c["confidence_class"] = df["confidence_class"]
c["frp_mw"] = df["frp_mw"]
c["day_night"] = df["daynight"]
c["fire_type"] = np.nan
c["satellite_raw"] = df["satellite"]
c["instrument_raw"] = df["sensor_family"]
c["extras"] = None
c.to_parquet(out, index=False)
print(c.shape, c["processing_stream"].value_counts().to_dict())