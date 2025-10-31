# ===============================================================
# 阶段三 · LinkNYC 通信设施数据清洗、空间化与年度热力分析
# ---------------------------------------------------------------
# 功能：
# 1. 读取 LinkNYC 节点数据；
# 2. 清洗字段并提取激活年份；
# 3. 转换为 GeoDataFrame（EPSG:4326）；
# 4. 生成年度累计趋势图；
# 5. 生成带时间滑块的热力图（叠加纽约市边界）。
# ===============================================================

import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import TimestampedGeoJson
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# ========== 字体设置（防止中文乱码） ==========
plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体显示中文
plt.rcParams['axes.unicode_minus'] = False     # 解决负号显示问题

# ========== 1. 读取数据 ==========
data_path = r"C:\Users\Jeffery\Desktop\石进大作业\纽约市Wifi热点\LinkNYC_Kiosk_Locations.csv"
df = pd.read_csv(data_path)
print("✅ 原始数据读取成功，共有记录数:", len(df))

# ========== 2. 过滤有效节点 ==========
df = df[df["Installation Status"].str.lower() == "live"]
df = df.dropna(subset=["Latitude", "Longitude", "Activation Complete"])
print("有效启用节点数:", len(df))

# ========== 3. 选择并标准化字段 ==========
keep_cols = [
    "Site ID", "Planned Kiosk Type", "Installation Status", "Borough",
    "Latitude", "Longitude", "Installation Complete", "Activation Complete",
    "Neighborhood Tabulation Area (NTA)"
]
df = df[keep_cols].copy()
df.columns = [
    "site_id", "kiosk_type", "status", "borough",
    "latitude", "longitude",
    "install_date", "active_date", "nta"
]

# ========== 4. 处理激活日期 ==========
df["active_date"] = pd.to_datetime(df["active_date"], errors="coerce")
df = df.dropna(subset=["active_date"])
df["year"] = df["active_date"].dt.year.astype(int)
print("年份范围:", df["year"].min(), "→", df["year"].max())

# ========== 5. 转换为地理空间数据 ==========
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
    crs="EPSG:4326"
)

# ========== 6. 输出清洗结果 ==========
output_dir = r"C:\Users\Jeffery\Desktop\石进大作业\Phase3\outputs"
import os
os.makedirs(output_dir, exist_ok=True)
gdf.to_file(f"{output_dir}/linknyc_cleaned.geojson", driver="GeoJSON")

# ========== 7. 年度累计统计 ==========
yearly = (
    gdf.groupby(["borough", "year"])
    .agg(count=("site_id", "count"))
    .reset_index()
)
yearly["cum_count"] = yearly.groupby("borough")["count"].cumsum()
yearly.to_csv(f"{output_dir}/linknyc_yearly_summary.csv", index=False)

# ========== 8. 绘制年度累计折线图 ==========
plt.figure(figsize=(10, 6))
for borough, grp in yearly.groupby("borough"):
    plt.plot(grp["year"], grp["cum_count"], marker="o", label=borough)

plt.title("LinkNYC 累计节点数变化（按 Borough）")
plt.xlabel("年份")
plt.ylabel("累计节点数量")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f"{output_dir}/linknyc_yearly_trend.png", dpi=300)
plt.close()
print("📊 年度累计趋势图已保存为 linknyc_yearly_trend.png")

# ========== 9. 创建年度累积节点分布图 ==========
nybb_path = r"C:\Users\Jeffery\Desktop\石进大作业\Phase2\nybb.shp"
nyc_boundary = gpd.read_file(nybb_path)
if nyc_boundary.crs != "EPSG:4326":
    nyc_boundary = nyc_boundary.to_crs("EPSG:4326")

# 数据准备
heat_df = gdf[["latitude", "longitude", "year"]].dropna().copy()
heat_df["latitude"] = heat_df["latitude"].astype(float)
heat_df["longitude"] = heat_df["longitude"].astype(float)
heat_df["year"] = heat_df["year"].astype(int)
years = sorted(heat_df["year"].unique())

print("可用的年份:", years)

# 创建地图
nyc_map = folium.Map(location=[40.75, -73.97], zoom_start=11, tiles="CartoDB positron")

# 添加行政边界（保持蓝色边界）
folium.GeoJson(
    nyc_boundary,
    name="NYC Boundary",
    style_function=lambda x: {
        "fillColor": "#e3f2fd",  # 浅蓝色填充
        "color": "#1976d2",      # 蓝色边框
        "weight": 2,
        "fillOpacity": 0.1,
    },
    tooltip=folium.GeoJsonTooltip(fields=["BoroName"], aliases=["Borough:"])
).add_to(nyc_map)

# 构建时间序列数据
features = []
all_years_data = {}

# 为每个年份准备数据
for year in years:
    # 当年新增的节点（红色）
    new_nodes = heat_df[heat_df["year"] == year]
    # 之前年份的所有节点（蓝色）
    existing_nodes = heat_df[heat_df["year"] < year]
    
    year_features = []
    
    # 添加之前年份的节点（蓝色）
    for _, row in existing_nodes.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point", 
                "coordinates": [row["longitude"], row["latitude"]]
            },
            "properties": {
                "time": f"{year}-01-01",  # 只显示年份
                "style": {"color": "#1e88e5", "icon": "circle"},  # 蓝色
                "icon": "circle",
                "iconstyle": {
                    "fillColor": "#1e88e5",  # 蓝色
                    "fillOpacity": 0.8,
                    "stroke": "true",
                    "color": "#ffffff",
                    "weight": 1,
                    "radius": 2,
                },
            },
        }
        year_features.append(feature)
    
    # 添加当年新增节点（红色）
    for _, row in new_nodes.iterrows():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point", 
                "coordinates": [row["longitude"], row["latitude"]]
            },
            "properties": {
                "time": f"{year}-01-01",  # 只显示年份
                "style": {"color": "#e53935", "icon": "circle"},  # 红色
                "icon": "circle",
                "iconstyle": {
                    "fillColor": "#e53935",  # 红色
                    "fillOpacity": 0.9,
                    "stroke": "true",
                    "color": "#ffffff",
                    "weight": 1,
                    "radius": 4,  # 新节点稍大一些
                },
            },
        }
        year_features.append(feature)
    
    all_years_data[year] = year_features
    features.extend(year_features)

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
    auto_play=False,
    loop=False,
    transition_time=1000,
    date_options='YYYY',  # 只显示年份
).add_to(nyc_map)

# 添加改进的图例
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; 
            right: 10px; 
            z-index: 9999;
            background: white;
            padding: 12px;
            border-radius: 6px;
            border: 2px solid #1976D2;
            font-size: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            font-family: Arial, sans-serif;">
    <h4 style="margin: 0 0 8px 0; color: #1976D2; text-align: center;">节点分布图例</h4>
    <div style="margin-bottom: 6px; display: flex; align-items: center;">
        <i style="background: #e53935; width: 14px; height: 14px; display: inline-block; border: 2px solid white; border-radius: 50%; margin-right: 8px;"></i>
        <span>当年新增节点</span>
    </div>
    <div style="margin-bottom: 6px; display: flex; align-items: center;">
        <i style="background: #1e88e5; width: 12px; height: 12px; display: inline-block; border: 2px solid white; border-radius: 50%; margin-right: 8px;"></i>
        <span>往年已有节点</span>
    </div>
    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #e0e0e0; font-size: 11px; color: #666;">
        <div>💡 使用左下角时间滑块</div>
        <div>查看节点累积过程</div>
    </div>
</div>
'''
nyc_map.get_root().html.add_child(folium.Element(legend_html))

# 自动缩放
bounds = [[heat_df["latitude"].min(), heat_df["longitude"].min()],
          [heat_df["latitude"].max(), heat_df["longitude"].max()]]
nyc_map.fit_bounds(bounds)

folium.LayerControl(collapsed=False).add_to(nyc_map)

output_html = f"{output_dir}/linknyc_nodes_timeline.html"
nyc_map.save(output_html)
print("🌆 ✅ 节点时间分布图已保存为 linknyc_nodes_timeline.html")
print("💡 功能说明:")
print("   • 使用时间滑块查看节点累积过程")
print("   • 红色节点: 当年新增 | 蓝色节点: 往年已有")
print("   • 时间戳只显示年份")
print("   • 保持蓝色行政边界")