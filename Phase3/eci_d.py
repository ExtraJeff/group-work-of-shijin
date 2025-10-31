"""
阶段三 · LinkNYC 通信设施空间密度指数（ECI）计算
----------------------------------------------------
目标：
1. 统计每个 NTA（社区区块）内的 LinkNYC 节点数量；
2. 计算平均最近邻距离（Nearest Neighbor Distance）；
3. 综合形成通信密度指数（ECI）并输出可视化。
"""

# ========== 导入库 ==========
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely import wkt
from scipy.spatial import cKDTree
import numpy as np
import folium
from folium import Choropleth

# ========== 1. 定义路径 ==========
BASE_DIR = r"C:\Users\Jeffery\Desktop\石进大作业"
PHASE3_DIR = os.path.join(BASE_DIR, "Phase3")
OUTPUT_DIR = os.path.join(PHASE3_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 输入文件
linknyc_path = os.path.join(OUTPUT_DIR, "linknyc_cleaned.geojson")
nta_path = os.path.join(BASE_DIR, "社区级别边界", "nynta2020_25c", "nynta2020.shp")

# ========== 2. 读取数据 ==========
print(f"读取已清洗的 GeoJSON： {linknyc_path}")
linknyc = gpd.read_file(linknyc_path)
print("节点数量：", len(linknyc))

nta_gdf = gpd.read_file(nta_path)
print("NTA 多边形数量：", len(nta_gdf))
print("注意：NTA 文件列示例（前20列）：", list(nta_gdf.columns)[:20])

# ========== 3. 坐标系统一 ==========
linknyc = linknyc.to_crs(epsg=2263)
nta_gdf = nta_gdf.to_crs(epsg=2263)

# ========== 4. 空间连接（节点匹配NTA） ==========
joined = gpd.sjoin(linknyc, nta_gdf, how="left", predicate="within")
print("sjoin 后节点计数（含 NTA info）:", len(joined))

# ========== 5. KDTree 最近邻距离 ==========
coords = np.array(list(zip(joined.geometry.x, joined.geometry.y)))
print("节点用于 KDTree 的坐标样本（前5）：", coords[:5])

tree = cKDTree(coords)
distances, indices = tree.query(coords, k=2, workers=-1)
joined["nearest_neighbor_dist"] = distances[:, 1]  # 第二列是最近邻距离

# ========== 6. 按 NTA 聚合统计 ==========
nta_summary = (
    joined.groupby("NTAName")
    .agg(
        node_count=("site_id", "count"),
        avg_nearest_dist_m=("nearest_neighbor_dist", "mean")
    )
    .reset_index()
)

# 计算面积与密度
nta_gdf["area_km2"] = nta_gdf.geometry.area / 1e6
nta_summary = nta_gdf.merge(nta_summary, on="NTAName", how="left")
nta_summary["node_count"] = nta_summary["node_count"].fillna(0)
nta_summary["node_density_per_km2"] = nta_summary["node_count"] / nta_summary["area_km2"]
city_avg_dist = joined["nearest_neighbor_dist"].mean()

print("示例 NTA（前5）:")
print(nta_summary[["NTAName", "node_count", "area_km2", "node_density_per_km2", "avg_nearest_dist_m"]].head())
print("城市平均最近邻距离 (m):", city_avg_dist)

# ========== 7. 计算 ECI ==========
nta_summary["eci"] = (nta_summary["node_density_per_km2"] /
                      (nta_summary["avg_nearest_dist_m"] / city_avg_dist)).replace([np.inf, -np.inf], np.nan)
nta_summary["eci"] = nta_summary["eci"].fillna(0)

# ========== 8. 输出结果 ==========
csv_path = os.path.join(OUTPUT_DIR, "linknyc_eci_by_nta.csv")
nta_summary.to_csv(csv_path, index=False)
print(f"✅ 已输出统计 CSV: {csv_path}")

# ========== 9. 保存为 GeoJSON ==========
gdf_out = gpd.GeoDataFrame(nta_summary, geometry=nta_summary.geometry, crs=nta_gdf.crs)
eci_geojson_path = os.path.join(OUTPUT_DIR, "linknyc_eci_by_nta.geojson")
gdf_out.to_file(eci_geojson_path, driver="GeoJSON")
print(f"✅ 已输出 GeoJSON: {eci_geojson_path}")

# ========== 10. 生成可视化地图 ==========
print("🗺️ 生成交互式地图...")

m = folium.Map(location=[40.75, -73.97], zoom_start=11, tiles="CartoDB positron")

# 加入底层 ECI 色阶图
Choropleth(
    geo_data=gdf_out,
    data=gdf_out,
    columns=["NTAName", "eci"],
    key_on="feature.properties.NTAName",
    fill_color="YlOrRd",
    fill_opacity=0.75,
    line_opacity=0.6,
    line_color="blue",
    nan_fill_opacity=0.1,
    legend_name="LinkNYC 通信密度指数（ECI）"
).add_to(m)

# 添加社区标签
for _, row in gdf_out.iterrows():
    if row["node_count"] > 0:
        folium.CircleMarker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            radius=2,
            color="navy",
            fill=True,
            fill_opacity=0.8,
            popup=f"{row['NTAName']}<br>节点数: {int(row['node_count'])}<br>ECI: {row['eci']:.2f}"
        ).add_to(m)

eci_html = os.path.join(OUTPUT_DIR, "linknyc_eci_map.html")
m.save(eci_html)

print(f"✅ 已生成交互式地图: {eci_html}")
print("🎯 阶段三 - ECI 空间密度分析完成！")
