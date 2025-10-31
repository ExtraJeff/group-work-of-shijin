"""
阶段四 · 建筑需求因子建模 D 指标（NTA级 + 对数强化）动态可视化
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
  Phase4/outputs/building_demand_timeline_by_nta.html  # 新增时间滑块地图
说明：
  - 先在地块层面计算 D，再把 D 聚合到 NTA（社区）层面供后续阶段使用。
  - 静态地图使用 NTA 多边形着色（对数增强，YlOrRd 色带）。
  - 新增时间滑块地图展示 D 指标的年度变化。
"""

import os
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from folium.plugins import TimestampedGeoJson
import branca.colormap as bc
import matplotlib.pyplot as plt
import json

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
output_timeline_map = os.path.join(OUT_DIR, "building_demand_timeline_by_nta.html")  # 新增时间滑块地图

# ========== 1. 读取数据 ==========
print("📘 读取 PLUTO 与 NTA 边界 ...")
pluto = gpd.read_file(pluto_path).to_crs(epsg=4326)
nta = gpd.read_file(nta_path).to_crs(epsg=4326)

# ========== 2. 检查年份字段并处理 ==========
if "year" not in pluto.columns:
    raise KeyError("❌ PLUTO 数据缺少 'year' 字段，无法进行时间序列分析")
    
years = sorted(pluto["year"].unique())
print(f"📅 可用年份: {years}")

# ========== 3. 检查必要字段 ==========
req = ["units_res", "land_use", "bbl", "year"]
for c in req:
    if c not in pluto.columns:
        raise KeyError(f"❌ PLUTO 缺少必要字段: {c}")

# ========== 4. 计算地块级 D（按年份） ==========
print("⚙️ 按年份计算地块级 D 指标 ...")

# 准备存储所有年份的结果
all_years_pluto = []

for year in years:
    print(f"   处理年份 {year}...")
    pluto_year = pluto[pluto["year"] == year].copy()
    
    # 填充缺失值
    pluto_year["units_res"] = pluto_year["units_res"].fillna(0).astype(float)
    
    # D_units: log1p then min-max normalize across parcels
    pluto_year["D_units_raw"] = np.log1p(pluto_year["units_res"])
    if pluto_year["D_units_raw"].max() > pluto_year["D_units_raw"].min():
        pluto_year["D_units"] = (pluto_year["D_units_raw"] - pluto_year["D_units_raw"].min()) / (pluto_year["D_units_raw"].max() - pluto_year["D_units_raw"].min())
    else:
        pluto_year["D_units"] = 0.0

    # D_type: map land_use codes -> weights
    def assign_d_type(landuse):
        if pd.isna(landuse):
            return 0.5
        s = str(landuse).strip()
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

    pluto_year["D_type"] = pluto_year["land_use"].apply(assign_d_type)

    # Combine
    pluto_year["D"] = 0.7 * pluto_year["D_units"] + 0.3 * pluto_year["D_type"]

    # D_log for visualization (log-enhanced)
    pluto_year["D_log_raw"] = np.log1p(pluto_year["D"] * 5.0)
    if pluto_year["D_log_raw"].max() > pluto_year["D_log_raw"].min():
        pluto_year["D_log"] = (pluto_year["D_log_raw"] - pluto_year["D_log_raw"].min()) / (pluto_year["D_log_raw"].max() - pluto_year["D_log_raw"].min())
    else:
        pluto_year["D_log"] = 0.0
        
    all_years_pluto.append(pluto_year)

# 合并所有年份的数据
pluto_all = pd.concat(all_years_pluto, ignore_index=True)

# ========== 5. 保存地块级结果 ==========
print("💾 保存地块级结果 ...")
out_cols = ["bbl", "land_use", "units_res", "year", "D_units", "D_type", "D", "D_log", "geometry"]
pluto_all[out_cols].to_file(output_parcel_geojson, driver="GeoJSON")
pluto_all[out_cols].drop(columns="geometry").to_csv(output_parcel_csv, index=False)
print("   →", output_parcel_geojson)
print("   →", output_parcel_csv)

# ========== 6. 空间连接：地块 -> NTA（按质心） ==========
print("📍 空间连接：地块 -> NTA（按质心） ...")
pluto_centroid = pluto_all.copy()
pluto_centroid["geometry"] = pluto_centroid.geometry.centroid
pluto_centroid = pluto_centroid.set_geometry("geometry")

# 确保 NTA 有名称字段
nta_name_col = None
for candidate in ["NTAName", "NTA_NAME", "nta_name", "NTAName"]:
    if candidate in nta.columns:
        nta_name_col = candidate
        break
if nta_name_col is None:
    if "geometry" in nta.columns:
        nta["NTAName"] = nta.index.astype(str)
        nta_name_col = "NTAName"
    else:
        raise KeyError("❌ 无法识别 NTA 名称字段，请检查 nta shapefile 列名。")

nta["NTAName"] = nta[nta_name_col].astype(str).str.strip()
joined = gpd.sjoin(pluto_centroid, nta[["NTAName", "geometry"]], how="left", predicate="within")

# ========== 7. NTA 聚合（按年份平均 D） ==========
print("🧮 按年份计算 NTA 平均 D ...")
nta_d_by_year = (
    joined.groupby(["NTAName", "year"])
    .agg(
        parcel_count=("bbl", "count"),
        D_mean=("D", "mean"),
        D_log_mean=("D_log", "mean")
    )
    .reset_index()
)

# 合并回 NTA GeoDataFrame
nta_out = nta.merge(nta_d_by_year, on="NTAName", how="left")
nta_out["parcel_count"] = nta_out["parcel_count"].fillna(0).astype(int)
nta_out["D_mean"] = nta_out["D_mean"].fillna(0.0)
nta_out["D_log_mean"] = nta_out["D_log_mean"].fillna(0.0)

# ========== 8. 输出 NTA 级结果 ==========
print("💾 保存 NTA 级结果 ...")
nta_out.to_file(output_nta_geojson, driver="GeoJSON")
nta_out.drop(columns="geometry").to_csv(output_nta_csv, index=False)
print("   →", output_nta_geojson)
print("   →", output_nta_csv)

# ========== 9. 静态可视化（在 NTA 多边形上着色，YlOrRd 对数增强） ==========
print("🎨 生成 NTA 级静态 Choropleth 地图 ...")
latest_year = years[-1]
nta_latest = nta_out[nta_out["year"] == latest_year].copy()

m_static = folium.Map(location=[40.75, -73.97], zoom_start=11, tiles="CartoDB positron", control_scale=True)

# 准备颜色尺度
vmin = nta_latest["D_log_mean"].min()
vmax = nta_latest["D_log_mean"].max() if nta_latest["D_log_mean"].max() > vmin else vmin + 1e-6
colormap = bc.linear.YlOrRd_09.scale(vmin, vmax)
colormap.caption = f"建筑需求指数 (D) - 对数增强 (NTA平均值, {latest_year}年)"
colormap.add_to(m_static)

# Choropleth
folium.Choropleth(
    geo_data=nta_latest,
    name=f"建筑需求指数 (D) - NTA ({latest_year}年)",
    data=nta_latest,
    columns=["NTAName", "D_log_mean"],
    key_on="feature.properties.NTAName",
    fill_color="YlOrRd",
    fill_opacity=0.85,
    line_opacity=0.4,
    line_color="#333333",
    nan_fill_color="#f0f0f0",
    legend_name="建筑需求指数 (对数增强)"
).add_to(m_static)

# 添加提示信息
folium.GeoJson(
    nta_latest,
    name="NTA 信息提示",
    style_function=lambda feat: {
        "fillOpacity": 0,
        "weight": 0.6,
        "color": "#444444"
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["NTAName", "parcel_count", "D_mean", "D_log_mean", "year"],
        aliases=["社区名称:", "地块数量:", "D 平均值:", "D_log 平均值:", "年份:"],
        localize=True
    )
).add_to(m_static)

# 添加行政边界
nybb_shp = os.path.join(BASE, "Phase2", "nybb.shp")
if os.path.exists(nybb_shp):
    boroughs = gpd.read_file(nybb_shp).to_crs(epsg=4326)
    folium.GeoJson(
        boroughs,
        name="行政区边界",
        style_function=lambda feat: {"fillOpacity": 0, "color": "#222222", "weight": 1.2}
    ).add_to(m_static)

# 标题
title_html = f"""
     <h3 align="center" style="font-size:18px"><b>建筑通信需求强度 (D) — 社区级别 ({latest_year}年)</b></h3>
     <h4 align="center" style="font-size:12px;color:gray">基于对数增强的社区平均建筑需求指数</h4>
     <hr style="width:80%;margin:auto">
"""
m_static.get_root().html.add_child(folium.Element(title_html))

m_static.save(output_map)
print("🌐 已保存 NTA 级静态地图:", output_map)

# ========== 10. 时间滑块动态可视化 ==========
print("🕐 生成时间滑块动态地图 ...")

# 创建基础地图
m_timeline = folium.Map(location=[40.75, -73.97], zoom_start=11, tiles="CartoDB positron", control_scale=True)

# 计算全局颜色尺度（所有年份）
global_vmin = nta_out["D_log_mean"].min()
global_vmax = nta_out["D_log_mean"].max() if nta_out["D_log_mean"].max() > global_vmin else global_vmin + 1e-6
global_colormap = bc.linear.YlOrRd_09.scale(global_vmin, global_vmax)
global_colormap.caption = "建筑需求指数 (D) - 所有年份"
global_colormap.add_to(m_timeline)

# 准备时间序列数据
features = []

for year in years:
    nta_year = nta_out[nta_out["year"] == year].copy()
    
    for idx, row in nta_year.iterrows():
        # 为每个NTA的每个年份创建特征
        feature = {
            "type": "Feature",
            "geometry": row.geometry.__geo_interface__ if row.geometry else None,
            "properties": {
                "time": f"{year}-01-01",  # 时间格式，只显示年份
                "NTAName": row["NTAName"],
                "parcel_count": int(row["parcel_count"]),
                "D_mean": round(row["D_mean"], 4),
                "D_log_mean": round(row["D_log_mean"], 4),
                "year": int(row["year"]),
                "style": {
                    "fillColor": global_colormap(row["D_log_mean"]),
                    "fillOpacity": 0.85,
                    "color": "#333333",
                    "weight": 0.6,
                    "opacity": 0.4
                }
            }
        }
        features.append(feature)

# 创建时间序列GeoJSON
geojson_data = {
    "type": "FeatureCollection",
    "features": features
}

# 添加时间序列图层
TimestampedGeoJson(
    data=geojson_data,
    period="P1Y",  # 每年一个周期
    duration="P1Y",
    add_last_point=True,
    auto_play=True,  # 自动播放
    loop=False,
    transition_time=1000,
    date_options='YYYY',  # 只显示年份
).add_to(m_timeline)

# 添加行政边界
if os.path.exists(nybb_shp):
    boroughs = gpd.read_file(nybb_shp).to_crs(epsg=4326)
    folium.GeoJson(
        boroughs,
        name="行政区边界",
        style_function=lambda feat: {
            "fillOpacity": 0,
            "color": "#222222",
            "weight": 2,
            "opacity": 0.8
        }
    ).add_to(m_timeline)

# 添加图例和说明
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; 
            left: 10px; 
            z-index: 9999;
            background: white;
            padding: 12px;
            border-radius: 6px;
            border: 2px solid #ff7f00;
            font-size: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            font-family: Arial, sans-serif;
            max-width: 250px;">
    <h4 style="margin: 0 0 8px 0; color: #ff7f00; text-align: center;">建筑需求指数 (D) 时间序列</h4>
    <div style="margin-bottom: 6px;">
        <span>🔥 颜色越深表示需求越高</span>
    </div>
    <div style="margin-bottom: 6px;">
        <span>📅 使用左下角时间滑块</span>
    </div>
    <div style="margin-bottom: 6px;">
        <span>▶️ 点击播放按钮自动播放</span>
    </div>
    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e0e0; font-size: 11px; color: #666;">
        <div>显示 NTA 级别的平均建筑通信需求指数</div>
        <div>基于住宅单元和土地利用类型计算</div>
    </div>
</div>
'''
m_timeline.get_root().html.add_child(folium.Element(legend_html))

# 标题
timeline_title_html = """
     <h3 align="center" style="font-size:18px"><b>建筑通信需求强度 (D) — 社区时间序列分析</b></h3>
     <h4 align="center" style="font-size:12px;color:gray">各社区建筑需求指数的年度变化趋势</h4>
     <hr style="width:80%;margin:auto">
"""
m_timeline.get_root().html.add_child(folium.Element(timeline_title_html))

# 保存时间滑块地图
m_timeline.save(output_timeline_map)
print("🌐 已保存时间滑块动态地图:", output_timeline_map)

print("\n✅ 阶段四（NTA级 D 指标 + 时间序列）完成！输出文件列表：")
print(" - 地块级 GeoJSON:", output_parcel_geojson)
print(" - 地块级 CSV:", output_parcel_csv)
print(" - NTA 级 GeoJSON:", output_nta_geojson)
print(" - NTA 级 CSV:", output_nta_csv)
print(" - NTA 级静态地图:", output_map)
print(" - NTA 级时间滑块地图:", output_timeline_map)