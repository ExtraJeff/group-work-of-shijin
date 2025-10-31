"""
阶段三（时间动态版）· LinkNYC 通信设施空间密度指数动态变化
----------------------------------------------------
目标：
1. 从active_date提取安装年份
2. 计算每个社区每年的通信密度指数（ECI）
3. 使用时间滑块展示ECI指数的年度变化
4. 无节点社区保持灰色
5. 输出交互式时间动态地图
"""

# ========== 导入库 ==========
import os
import pandas as pd
import geopandas as gpd
from scipy.spatial import cKDTree
import numpy as np
import folium
from folium.plugins import TimestampedGeoJson
import json
from datetime import datetime

# ========== 1. 路径设置 ==========
BASE_DIR = r"C:\Users\Jeffery\Desktop\石进大作业"
PHASE3_DIR = os.path.join(BASE_DIR, "Phase3")
OUTPUT_DIR = os.path.join(PHASE3_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

linknyc_path = os.path.join(OUTPUT_DIR, "linknyc_cleaned.geojson")
nta_path = os.path.join(BASE_DIR, "社区级别边界", "nynta2020_25c", "nynta2020.shp")

# ========== 2. 读取数据 ==========
print("📘 读取数据中 ...")
linknyc = gpd.read_file(linknyc_path)
nta_gdf = gpd.read_file(nta_path)
print(f"✅ 数据读取成功: {len(linknyc)} 个节点, {len(nta_gdf)} 个社区")

# ========== 3. 从active_date提取年份 ==========
print("📅 正在从active_date提取安装年份...")

# 检查active_date列是否存在
if 'active_date' not in linknyc.columns:
    raise KeyError("❌ 数据中缺少 'active_date' 列")

# 转换日期格式并提取年份
linknyc['active_date'] = pd.to_datetime(linknyc['active_date'], errors='coerce')

# 检查是否有无效日期
invalid_dates = linknyc['active_date'].isna().sum()
if invalid_dates > 0:
    print(f"⚠️  发现 {invalid_dates} 个无效日期，已自动处理")

# 提取年份
linknyc['year'] = linknyc['active_date'].dt.year

# 检查年份范围
valid_years = linknyc['year'].notna()
years_range = linknyc.loc[valid_years, 'year']
print(f"📊 激活年份范围: {years_range.min()} - {years_range.max()}")
print(f"📈 各年份节点数量:")
year_counts = linknyc['year'].value_counts().sort_index()
for year, count in year_counts.items():
    print(f"   {year}: {count} 个节点")

# 移除年份为NaN的记录（如果有）
linknyc = linknyc[linknyc['year'].notna()]
linknyc['year'] = linknyc['year'].astype(int)

# ========== 4. 坐标系统一 ==========
linknyc = linknyc.to_crs(epsg=2263)
nta_gdf = nta_gdf.to_crs(epsg=2263)

# ========== 5. 按年份计算ECI ==========
print("\n📊 正在按年份计算ECI指数...")

# 获取所有年份并按时间排序
years = sorted(linknyc['year'].unique())
print(f"🕓 检测到年份: {years}")

# 存储每年结果
annual_results = []

for year in years:
    print(f"⏳ 正在计算 {year} 年 ECI ...")
    
    # 筛选该年份及之前的所有节点（累积计算）
    linknyc_year = linknyc[linknyc['year'] <= year].copy()
    
    if len(linknyc_year) == 0:
        continue
        
    # 空间连接
    joined = gpd.sjoin(linknyc_year, nta_gdf, how="left", predicate="within")
    
    # 最近邻距离
    coords = np.array(list(zip(joined.geometry.x, joined.geometry.y)))
    tree = cKDTree(coords)
    distances, _ = tree.query(coords, k=2)
    joined["nearest_neighbor_dist"] = distances[:, 1]
    
    # 按社区聚合
    nta_summary = (
        joined.groupby("NTAName")
        .agg(
            node_count=("site_id", "count"),
            avg_nearest_dist_m=("nearest_neighbor_dist", "mean")
        )
        .reset_index()
    )
    
    # 合并地理边界
    nta_gdf_copy = nta_gdf.copy()
    nta_gdf_copy["area_km2"] = nta_gdf_copy.geometry.area / 1e6
    nta_summary = nta_gdf_copy.merge(nta_summary, on="NTAName", how="left")
    
    # 填补缺失
    nta_summary["node_count"] = nta_summary["node_count"].fillna(0)
    nta_summary["avg_nearest_dist_m"] = nta_summary["avg_nearest_dist_m"].fillna(0)
    nta_summary["node_density_per_km2"] = nta_summary["node_count"] / nta_summary["area_km2"]
    
    city_avg_dist = joined["nearest_neighbor_dist"].mean()
    
    # 计算 ECI
    nta_summary["eci"] = (
        nta_summary["node_density_per_km2"] /
        (nta_summary["avg_nearest_dist_m"] / city_avg_dist)
    ).replace([np.inf, -np.inf], np.nan)
    nta_summary["eci"] = nta_summary["eci"].fillna(0)
    
    # 对数变换
    nta_summary["eci_log"] = 0.0
    nta_summary.loc[nta_summary["node_count"] > 0, "eci_log"] = np.log10(
        nta_summary.loc[nta_summary["node_count"] > 0, "eci"] + 1
    )
    
    # 添加年份
    nta_summary["year"] = year
    
    annual_results.append(nta_summary)

# ========== 6. 合并所有年份结果 ==========
all_years_df = pd.concat(annual_results, ignore_index=True)

# 输出合并结果
eci_geojson_path = os.path.join(OUTPUT_DIR, "linknyc_eci_by_nta_all_years.geojson")
gdf_out = gpd.GeoDataFrame(all_years_df, geometry=all_years_df.geometry, crs=nta_gdf.crs)
gdf_out.to_file(eci_geojson_path, driver="GeoJSON")
print(f"✅ 已输出年度ECI GeoJSON: {eci_geojson_path}")

# ========== 7. 时间滑块地图可视化 ==========
print("🎨 正在生成时间滑块动态地图 ...")

gdf_out_4326 = gdf_out.to_crs(epsg=4326)

# 定义颜色函数
def get_color(eci_log_value, node_count):
    """根据ECI对数值和节点数量获取颜色"""
    if node_count == 0:
        return '#f2f2f2'  # 无节点区域灰色
    
    # 根据ECI对数值分级上色
    if eci_log_value < 0.5:
        return '#fee0d2'  # 浅橙色 - 低密度
    elif eci_log_value < 1.0:
        return '#fc9272'  # 中等橙色 - 中等密度
    elif eci_log_value < 1.5:
        return '#fb6a4a'  # 橙色 - 较高密度
    else:
        return '#de2d26'  # 红色 - 高密度

# 构建时间序列数据
features = []

for year in years:
    year_data = gdf_out_4326[gdf_out_4326['year'] == year]
    
    for _, row in year_data.iterrows():
        color = get_color(row['eci_log'], row['node_count'])
        
        feature = {
            "type": "Feature",
            "geometry": row.geometry.__geo_interface__,
            "properties": {
                "NTAName": row["NTAName"],
                "time": f"{int(year)}-01-01",  # 标准日期格式
                "eci_log": float(row["eci_log"]),
                "eci_original": float(row["eci"]),
                "node_count": int(row["node_count"]),
                "style": {
                    "color": "#444444",
                    "weight": 0.6,
                    "fillColor": color,
                    "fillOpacity": 0.85
                },
                "popup": (
                    f"<b>{row['NTAName']}</b><br>"
                    f"年份: {int(year)}<br>"
                    f"节点数量: {int(row['node_count'])}<br>"
                    f"ECI原始值: {row['eci']:.3f}<br>"
                    f"ECI对数标准化: {row['eci_log']:.3f}<br>"
                    f"<small>显示截至{year}年的累积节点</small>"
                )
            },
        }
        features.append(feature)

# 创建GeoJSON数据
geojson_data = {
    "type": "FeatureCollection",
    "features": features
}

# ========== 8. 创建时间滑块地图 ==========
m = folium.Map(location=[40.75, -73.97], zoom_start=11, tiles="CartoDB positron")

# 创建时间滑块图层
timeslider = TimestampedGeoJson(
    geojson_data,
    period="P1Y",           # 时间间隔为1年
    duration="P1M",         # 过渡时间为1个月
    auto_play=False,        # 不自动播放
    loop=False,             # 不循环播放
    transition_time=1000,   # 过渡动画时间1秒
    date_options='YYYY',    # 显示年份
    add_last_point=True     # 添加最后一个时间点
)

timeslider.add_to(m)

# ========== 9. 添加JavaScript控制 ==========
initial_year = years[0] if years else 2016
js_code = f'''
<script>
// 应用样式到GeoJSON要素
function applyStyles() {{
    const layers = Object.values(map._layers);
    for (const layer of layers) {{
        if (layer._geoJson) {{
            layer.eachLayer(function(featureLayer) {{
                if (featureLayer.feature && featureLayer.feature.properties.style) {{
                    const style = featureLayer.feature.properties.style;
                    featureLayer.setStyle({{
                        color: style.color,
                        weight: style.weight,
                        fillColor: style.fillColor,
                        fillOpacity: style.fillOpacity
                    }});
                }}
            }});
        }}
    }}
}}

// 查找时间滑块图层
function findTimeSlider() {{
    const layers = Object.values(map._layers);
    for (const layer of layers) {{
        if (layer._timeDimension && layer._timeDimension._player) {{
            return layer._timeDimension;
        }}
    }}
    return null;
}}

// 播放/暂停控制
function playPause() {{
    const timeDimension = findTimeSlider();
    if (timeDimension && timeDimension._player) {{
        if (timeDimension._player._playing) {{
            timeDimension._player.pause();
        }} else {{
            timeDimension._player.play();
        }}
    }}
}}

// 重置时间
function resetTime() {{
    const timeDimension = findTimeSlider();
    if (timeDimension) {{
        timeDimension.setCurrentTime(0);
    }}
}}

// 初始化时应用样式
document.addEventListener('DOMContentLoaded', function() {{
    setTimeout(applyStyles, 1000);
    setInterval(applyStyles, 2000);
}});

// 更新年份显示
function updateYearDisplay(year) {{
    // 移除年份显示功能
}}

// 监听时间变化
setInterval(function() {{
    const timeControls = document.querySelectorAll('.leaflet-control-timecontrol');
    timeControls.forEach(element => {{
        const text = element.textContent || element.innerText;
        if (text && /\\\\d{{4}}/.test(text)) {{
            // 移除年份显示功能
        }}
    }});
}}, 500);

// 监听图层变化，确保样式正确应用
map.on('moveend', function() {{
    applyStyles();
}});
</script>
'''

m.get_root().html.add_child(folium.Element(js_code))

# ========== 10. 添加图例 ==========
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; 
            right: 10px; 
            z-index: 9999;
            background: white;
            padding: 12px;
            border-radius: 6px;
            border: 2px solid #2196F3;
            font-size: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
    <h4 style="margin: 0 0 8px 0; color: #1976D2;">ECI 图例</h4>
    <div style="margin-bottom: 4px;"><i style="background: #f2f2f2; width: 20px; height: 10px; display: inline-block; border: 1px solid #999; border-radius: 2px;"></i> 无节点区域</div>
    <div style="margin-bottom: 4px;"><i style="background: #fee0d2; width: 20px; height: 10px; display: inline-block; border: 1px solid #999; border-radius: 2px;"></i> 低密度 (ECI对数 < 0.5)</div>
    <div style="margin-bottom: 4px;"><i style="background: #fc9272; width: 20px; height: 10px; display: inline-block; border: 1px solid #999; border-radius: 2px;"></i> 中密度 (0.5-1.0)</div>
    <div style="margin-bottom: 4px;"><i style="background: #fb6a4a; width: 20px; height: 10px; display: inline-block; border: 1px solid #999; border-radius: 2px;"></i> 较高密度 (1.0-1.5)</div>
    <div><i style="background: #de2d26; width: 20px; height: 10px; display: inline-block; border: 1px solid #999; border-radius: 2px;"></i> 高密度 (> 1.5)</div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# ========== 11. 保存地图 ==========
eci_html = os.path.join(OUTPUT_DIR, "linknyc_eci_timeslider_map.html")
m.save(eci_html)

print(f"✅ 已生成时间滑块动态地图: {eci_html}")
print("🎯 阶段三 - ECI 时间动态分析完成！")
print(f"📊 时间范围: {min(years)} - {max(years)}")
print("💡 功能说明:")
print("   • 使用时间滑块查看ECI指数年度变化")
print("   • 播放按钮自动展示网络发展历程") 
print("   • 点击区域查看详细的ECI信息")
print("   • 显示截至当前年份的累积节点分布")