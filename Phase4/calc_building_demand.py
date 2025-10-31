"""
阶段四 · 建筑需求因子建模 D 指标（NTA级 + 对数强化）
---------------------------------------------------------
输入（示例本地路径，请按需修改）：
  Phase1/outputs/pluto_all_years.geojson
  社区级别边界/nynta2020_25c/nynta2020.shp
输出：
  Phase4/outputs/building_demand_index_parcel.geojson
  Phase4/outputs/building_demand_index_parcel.csv
  Phase4/outputs/building_demand_index_by_nta.geojson
  Phase4/outputs/building_demand_index_by_nta.csv
  Phase4/outputs/building_demand_map_by_nta.html
说明：
  - 先在地块层面计算 D，再把 D 聚合到 NTA（社区）层面供后续阶段使用。
  - 地图使用 NTA 多边形着色（对数增强，YlOrRd 色带）。
"""

import os
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
import branca.colormap as bc
import matplotlib.pyplot as plt

# ========== 文件路径（按需修改） ==========
BASE = r"C:\Users\Jeffery\Desktop\石进大作业"
pluto_path = os.path.join(BASE, "Phase1", "outputs", "pluto_all_years.geojson")
nta_path = os.path.join(BASE, "社区级别边界", "nynta2020_25c", "nynta2020.shp")

OUT_DIR = os.path.join(BASE, "Phase4", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

output_parcel_geojson = os.path.join(OUT_DIR, "building_demand_index_parcel.geojson")
output_parcel_csv = os.path.join(OUT_DIR, "building_demand_index_parcel.csv")
output_nta_geojson = os.path.join(OUT_DIR, "building_demand_index_by_nta.geojson")
output_nta_csv = os.path.join(OUT_DIR, "building_demand_index_by_nta.csv")
output_map = os.path.join(OUT_DIR, "building_demand_map_by_nta.html")

# ========== 1. 读取数据 ==========
print("📘 读取 PLUTO 与 NTA 边界 ...")
pluto = gpd.read_file(pluto_path).to_crs(epsg=4326)
nta = gpd.read_file(nta_path).to_crs(epsg=4326)

# ========== 2. 取最新年份地块（若有 year 字段） ==========
if "year" in pluto.columns:
    latest_year = int(pluto["year"].max())
    pluto = pluto[pluto["year"] == latest_year].copy()
    print(f"✅ 使用 PLUTO 年份: {latest_year}")
else:
    print("⚠️ 未检测到 'year' 字段，将使用所有地块。")

# ========== 3. 检查必要字段 ==========
req = ["units_res", "land_use", "bbl"]
for c in req:
    if c not in pluto.columns:
        raise KeyError(f"❌ PLUTO 缺少必要字段: {c}")

# ========== 4. 计算地块级 D ==========
print("⚙️ 计算地块级 D 指标 ...")

pluto["units_res"] = pluto["units_res"].fillna(0).astype(float)

# D_units: log1p then min-max normalize across parcels
pluto["D_units_raw"] = np.log1p(pluto["units_res"])
if pluto["D_units_raw"].max() > pluto["D_units_raw"].min():
    pluto["D_units"] = (pluto["D_units_raw"] - pluto["D_units_raw"].min()) / (pluto["D_units_raw"].max() - pluto["D_units_raw"].min())
else:
    pluto["D_units"] = 0.0

# D_type: map land_use codes -> weights (same mapping logic as before)
def assign_d_type(landuse):
    if pd.isna(landuse):
        return 0.5
    s = str(landuse).strip()
    # if numeric code like 1,2,3...
    if s.isdigit():
        if s.startswith("1"):
            return 1.0
        elif s.startswith("2"):
            return 0.85
        elif s.startswith("3"):
            return 0.6
        elif s.startswith("4"):
            return 0.7
        else:
            return 0.5
    # string case (try keywords)
    s_low = s.lower()
    if "resid" in s_low:
        return 1.0
    if "mix" in s_low:
        return 0.85
    if "comm" in s_low or "office" in s_low:
        return 0.6
    if "ind" in s_low:
        return 0.7
    return 0.5

pluto["D_type"] = pluto["land_use"].apply(assign_d_type)

# Combine
pluto["D"] = 0.7 * pluto["D_units"] + 0.3 * pluto["D_type"]

# D_log for visualization (log-enhanced)
# multiplier scales sensitivity; tune as needed (we use 5)
pluto["D_log_raw"] = np.log1p(pluto["D"] * 5.0)
if pluto["D_log_raw"].max() > pluto["D_log_raw"].min():
    pluto["D_log"] = (pluto["D_log_raw"] - pluto["D_log_raw"].min()) / (pluto["D_log_raw"].max() - pluto["D_log_raw"].min())
else:
    pluto["D_log"] = 0.0

# ========== 5. 保存地块级结果 ==========
print("💾 保存地块级结果 ...")
out_cols = ["bbl", "land_use", "units_res", "D_units", "D_type", "D", "D_log", "geometry"]
pluto[out_cols].to_file(output_parcel_geojson, driver="GeoJSON")
pluto[out_cols].drop(columns="geometry").to_csv(output_parcel_csv, index=False)
print("   →", output_parcel_geojson)
print("   →", output_parcel_csv)

# ========== 6. 空间连接：地块 -> NTA（按质心） ==========
print("📍 空间连接：地块 -> NTA（按质心） ...")
pluto_centroid = pluto.copy()
pluto_centroid["geometry"] = pluto_centroid.geometry.centroid
pluto_centroid = pluto_centroid.set_geometry("geometry")

# ensure NTA has name field
nta_name_col = None
for candidate in ["NTAName", "NTA_NAME", "nta_name", "NTAName"]:
    if candidate in nta.columns:
        nta_name_col = candidate
        break
if nta_name_col is None:
    # try common fallback
    if "geometry" in nta.columns:
        # if no NTAName, create synthetic names from index
        nta["NTAName"] = nta.index.astype(str)
        nta_name_col = "NTAName"
    else:
        raise KeyError("❌ 无法识别 NTA 名称字段，请检查 nta shapefile 列名。")
# normalize name col
nta["NTAName"] = nta[nta_name_col].astype(str).str.strip()

joined = gpd.sjoin(pluto_centroid, nta[["NTAName", "geometry"]], how="left", predicate="within")
print("   匹配后的记录数:", len(joined))

# ========== 7. NTA 聚合（平均 D） ==========
print("🧮 计算 NTA 平均 D ...")
nta_d = (
    joined.groupby("NTAName")
    .agg(
        parcel_count=("bbl", "count"),
        D_mean=("D", "mean"),
        D_log_mean=("D_log", "mean")
    )
    .reset_index()
)

# Merge back to NTA GeoDataFrame
nta_out = nta.merge(nta_d, on="NTAName", how="left")
nta_out["parcel_count"] = nta_out["parcel_count"].fillna(0).astype(int)
nta_out["D_mean"] = nta_out["D_mean"].fillna(0.0)
nta_out["D_log_mean"] = nta_out["D_log_mean"].fillna(0.0)

# ========== 8. 输出 NTA 级结果 ==========
print("💾 保存 NTA 级结果 ...")
nta_out.to_file(output_nta_geojson, driver="GeoJSON")
nta_out.drop(columns="geometry").to_csv(output_nta_csv, index=False)
print("   →", output_nta_geojson)
print("   →", output_nta_csv)

# ========== 9. 可视化（在 NTA 多边形上着色，YlOrRd 对数增强） ==========
print("🎨 生成 NTA 级 Choropleth 地图 ...")

m = folium.Map(location=[40.75, -73.97], zoom_start=11, tiles="CartoDB positron", control_scale=True)

# prepare color scale using D_log_mean
vmin = nta_out["D_log_mean"].min()
vmax = nta_out["D_log_mean"].max() if nta_out["D_log_mean"].max() > vmin else vmin + 1e-6
colormap = bc.linear.YlOrRd_09.scale(vmin, vmax)
colormap.caption = "建筑通信需求指数 (D) - 对数增强 (NTA平均值)"
colormap.add_to(m)

# Choropleth
folium.Choropleth(
    geo_data=nta_out,
    name="建筑需求指数 (D) - NTA (对数增强)",
    data=nta_out,
    columns=["NTAName", "D_log_mean"],
    key_on="feature.properties.NTAName",
    fill_color="YlOrRd",
    fill_opacity=0.85,
    line_opacity=0.4,
    line_color="#333333",
    nan_fill_color="#f0f0f0",
    legend_name="建筑需求指数 (对数增强)"
).add_to(m)

# Add tooltip: NTA name + parcel count + D_mean
folium.GeoJson(
    nta_out,
    name="NTA 信息提示",
    style_function=lambda feat: {
        "fillOpacity": 0,
        "weight": 0.6,
        "color": "#444444"
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["NTAName", "parcel_count", "D_mean", "D_log_mean"],
        aliases=["社区名称:", "地块数量:", "D 平均值:", "D_log 平均值:"],
        localize=True
    )
).add_to(m)

# Add borough boundaries (optional) if you have borough shapefile
nybb_shp = os.path.join(BASE, "Phase2", "nybb.shp")
if os.path.exists(nybb_shp):
    boroughs = gpd.read_file(nybb_shp).to_crs(epsg=4326)
    folium.GeoJson(
        boroughs,
        name="行政区边界",
        style_function=lambda feat: {"fillOpacity": 0, "color": "#222222", "weight": 1.2}
    ).add_to(m)

# Title / Legend box
title_html = """
     <h3 align="center" style="font-size:18px"><b>建筑通信需求强度 (D) — 社区级别 (NTA)</b></h3>
     <h4 align="center" style="font-size:12px;color:gray">基于对数增强的社区平均建筑需求指数</h4>
     <hr style="width:80%;margin:auto">
"""
m.get_root().html.add_child(folium.Element(title_html))

# Save map
m.save(output_map)
print("🌐 已保存 NTA 级地图:", output_map)

print("\n✅ 阶段四（NTA级 D 指标）完成！输出文件列表：")
print(" - 地块级 GeoJSON:", output_parcel_geojson)
print(" - 地块级 CSV:", output_parcel_csv)
print(" - NTA 级 GeoJSON:", output_nta_geojson)
print(" - NTA 级 CSV:", output_nta_csv)
print(" - NTA 级 地图:", output_map)
