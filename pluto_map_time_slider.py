"""
纽约市建筑变化动态地图（聚合轻量版）
-----------------------------------------
输入：
  - pluto_all_years.geojson
  - pluto_change_summary.csv
输出：
  - outputs/maps/NYC_Building_Change_2016_2025_grid_agg.html
"""

import os
import math
import geopandas as gpd
import pandas as pd
from shapely.geometry import box, mapping
import folium
from folium.plugins import TimestampedGeoJson

# ========== 文件路径 ==========
PLUTO_GEO_PATH = "C:/Users/Jeffery/Desktop/石进大作业/outputs/pluto_all_years.geojson"
CHANGE_SUMMARY_PATH = "C:/Users/Jeffery/Desktop/石进大作业/Pluto/outputs/pluto_change_summary.csv"
OUTPUT_MAP = "outputs/maps/NYC_Building_Change_2016_2025_grid_agg.html"

# ========== 参数设置 ==========
GRID_SIZE_DEG = 0.01  # 网格大小（越大越流畅）
MIN_COUNT_TO_KEEP = 1
KEEP_CHANGE_TYPES = ["Rebuilt", "Expanded", "UseChange"]
MIN_YEAR, MAX_YEAR = 2016, 2025

os.makedirs(os.path.dirname(OUTPUT_MAP), exist_ok=True)

# ========== 读取数据 ==========
print("📘 读取 pluto_all_years.geojson ...")
gdf_pluto = gpd.read_file(PLUTO_GEO_PATH)

print("📘 读取 pluto_change_summary.csv ...")
df_change = pd.read_csv(CHANGE_SUMMARY_PATH)
df_change.columns = df_change.columns.str.strip().str.replace("\ufeff", "", regex=True)
df_change["bbl"] = df_change["bbl"].astype(str)
gdf_pluto["bbl"] = gdf_pluto["bbl"].astype(str)

# ========== 准备 year 字段 ==========
if "last_year" in df_change.columns:
    df_change["year"] = df_change["last_year"]
elif "first_year" in df_change.columns:
    df_change["year"] = df_change["first_year"]
else:
    raise ValueError("❌ CSV 文件中缺少 last_year 或 first_year 字段。")

df_change["year"] = pd.to_numeric(df_change["year"], errors="coerce").fillna(MAX_YEAR).astype(int)
df_change = df_change[(df_change["year"] >= MIN_YEAR) & (df_change["year"] <= MAX_YEAR)]
df_change = df_change[df_change["change_type"].isin(KEEP_CHANGE_TYPES)]
print(f"📊 变化记录数量（筛后）: {len(df_change):,}")

# ========== 合并 ==========
print("🔗 合并变化表与几何（按 bbl）...")
df_pluto = pd.DataFrame(gdf_pluto.drop(columns="geometry"))
df_merged = df_pluto.merge(df_change[["bbl", "change_type", "year"]], on="bbl", how="inner")

# 🧩 自动检测 year 列名
if "year_y" in df_merged.columns:
    df_merged["year"] = df_merged["year_y"]
elif "year_x" in df_merged.columns:
    df_merged["year"] = df_merged["year_x"]
elif "year" not in df_merged.columns:
    raise ValueError("❌ year 列在合并后丢失，请检查 df_change。")

# 恢复几何
gdf_changes = gpd.GeoDataFrame(df_merged, geometry=gdf_pluto.geometry, crs=gdf_pluto.crs)
print(f"✅ 合并后变化地块数量: {len(gdf_changes):,}")

# ========== 限定纽约市区域 ==========
nyc_bounds = box(-74.3, 40.45, -73.68, 40.95)
gdf_changes = gdf_changes[gdf_changes.geometry.within(nyc_bounds)].copy()
print(f"📍 仅保留 NYC bbox 内的变化地块: {len(gdf_changes):,}")

# ========== 构建规则网格 ==========
print("🔲 构建规则网格（fishnet）...")
minx, miny, maxx, maxy = nyc_bounds.bounds
nx = int(math.ceil((maxx - minx) / GRID_SIZE_DEG))
ny = int(math.ceil((maxy - miny) / GRID_SIZE_DEG))

cells = []
for i in range(nx):
    for j in range(ny):
        x1, y1 = minx + i * GRID_SIZE_DEG, miny + j * GRID_SIZE_DEG
        x2, y2 = x1 + GRID_SIZE_DEG, y1 + GRID_SIZE_DEG
        cells.append({"cell_id": f"{i}_{j}", "geometry": box(x1, y1, x2, y2)})

gdf_grid = gpd.GeoDataFrame(cells, crs=gdf_changes.crs)
print(f"🧩 网格单元数: {len(gdf_grid):,}")

# ========== 空间连接 ==========
print("📐 将变化地块分配到网格单元（空间连接）...")
joined = gpd.sjoin(
    gdf_changes[["bbl", "change_type", "year", "geometry"]],
    gdf_grid[["cell_id", "geometry"]],
    how="left",
    predicate="within"
)
joined = joined.dropna(subset=["cell_id"]).copy()
print(f"🔎 匹配成功记录: {len(joined):,}")

# ========== 聚合 ==========
print("📊 按年与单元聚合统计...")
df_agg = (
    joined.groupby(["year", "cell_id"])
    .agg(count=("bbl", "count"), top_type=("change_type", lambda x: x.value_counts().idxmax()))
    .reset_index()
)
df_agg = df_agg[df_agg["count"] >= MIN_COUNT_TO_KEEP]

# ========== 合并几何 ==========
gdf_cells = gdf_grid.merge(df_agg, on="cell_id", how="inner")
print(f"📦 导出格网单元: {len(gdf_cells):,}")

# ========== 构造 GeoJSON ==========
print("🛠️ 构造时间序列 GeoJSON 特征...")
features = []
type_color = {"Rebuilt": "red", "Expanded": "green", "UseChange": "blue"}

for _, row in gdf_cells.iterrows():
    year = int(row["year"])
    geom = mapping(row["geometry"].simplify(0.0001))
    color = type_color.get(row["top_type"], "gray")
    opacity = min(0.85, 0.2 + math.log1p(row["count"]) * 0.12)
    weight = 0.3 + min(2.0, math.log1p(row["count"]) * 0.6)
    features.append({
        "type": "Feature",
        "geometry": geom,
        "properties": {
            "time": f"{year}-01-01",
            "style": {"color": color, "fillColor": color, "weight": weight, "fillOpacity": opacity},
            "popup": f"Cell: {row['cell_id']}<br>Year: {year}<br>Count: {row['count']}<br>Type: {row['top_type']}"
        }
    })

geojson = {"type": "FeatureCollection", "features": features}
print(f"🔧 总 feature 数: {len(features):,}")

# ========== 创建地图 ==========
print("🗺️ 创建 Folium 地图...")
m = folium.Map(location=[40.7128, -74.0060], zoom_start=11, tiles="cartodb positron")

TimestampedGeoJson(
    data=geojson,
    transition_time=200,
    period="P1Y",
    add_last_point=False,
    auto_play=False,
    loop=False,
    max_speed=2,
    loop_button=True,
    date_options="YYYY",
    time_slider_drag_update=True,
).add_to(m)

legend_html = """
<div style="
    position: fixed;
    bottom: 40px; left: 40px; width: 180px;
    background: white; z-index:9999; font-size:14px;
    border:2px solid grey; border-radius:8px; padding:10px;">
<b>Change Types</b><br>
<span style="color:red;">&#11044;</span> Rebuilt<br>
<span style="color:green;">&#11044;</span> Expanded<br>
<span style="color:blue;">&#11044;</span> Use Change<br>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))
m.save(OUTPUT_MAP)

print(f"\n✅ 地图生成完成：{OUTPUT_MAP}")
print("💡 提示：若仍偏大或卡顿，可调大 GRID_SIZE_DEG 或 MIN_COUNT_TO_KEEP。")
