"""
阶段二：建筑更新强度量化 (PLUTO ↔ DOB Certificates of Occupancy)
--------------------------------------------------------
功能：
1. 读取整合后的 PLUTO 数据 (CSV 或 GeoJSON)
2. 读取 DOB CO 数据（CSV）
3. 按年份和地块编号 (BBL) 匹配，统计建筑更新数量
4. 计算 Borough 级年度建筑更新强度 (UpdateIndex)
5. 输出指标表 + 轻量版 Borough 热力地图

输入：
- pluto_all_years.geojson 或 pluto_all_years.csv
- DOB_Certificate_Of_Occupancy_20251021.csv

输出：
- update_index_by_borough.csv
- update_index_map_light.html
"""

# =============================
# 导入库
# =============================
import pandas as pd
import geopandas as gpd
import folium
import re

# =============================
# Step 1：加载 PLUTO 数据
# =============================
try:
    pluto = gpd.read_file("C:/Users/Jeffery/Desktop/石进大作业/outputs/pluto_all_years.geojson")
except Exception:
    pluto = pd.read_csv("C:/Users/Jeffery/Desktop/石进大作业/Pluto/outputs/pluto_all_years.csv", dtype={'bbl': str})

pluto.columns = [c.lower().strip() for c in pluto.columns]
pluto['bbl'] = pluto['bbl'].astype(str)

# 生成 Borough 字段（若不存在）
if 'borough' not in pluto.columns:
    borough_map = {1:'Manhattan', 2:'Bronx', 3:'Brooklyn', 4:'Queens', 5:'Staten Island'}

    def extract_borough(bbl):
        if isinstance(bbl, str):
            match = re.match(r"^\s*([1-5])", bbl)
            if match:
                return int(match.group(1))
        return None

    pluto['borough_id'] = pluto['bbl'].apply(extract_borough)
    pluto['borough'] = pluto['borough_id'].map(borough_map)

print(f"✅ 已加载 PLUTO 数据，共 {len(pluto)} 条记录，年份范围：{pluto['year'].min()}–{pluto['year'].max()}")

# =============================
# Step 2：加载 DOB 数据 (CSV)
# =============================
dob = pd.read_csv(
    "C:/Users/Jeffery/Desktop/石进大作业/纽约市居住证/DOB_Certificate_Of_Occupancy_20251021.csv",
    low_memory=False
)
dob.columns = [c.lower().strip() for c in dob.columns]

# 自动识别日期和 bbl 字段
date_cols = [c for c in dob.columns if 'date' in c or 'issue' in c]
bbl_cols = [c for c in dob.columns if 'bbl' in c or ('block' in c and 'lot' in c)]

if not date_cols or not bbl_cols:
    raise ValueError("⚠️ 无法识别 DOB 文件中的日期或 BBL 字段，请检查字段名称。")

date_col = date_cols[0]
bbl_col = bbl_cols[0]

# 提取年份
dob['year'] = pd.to_datetime(dob[date_col], errors='coerce').dt.year
dob = dob[dob['year'].between(2016, 2025)]

# 提取 BBL
dob['bbl'] = dob[bbl_col].astype(str)

# 统计每年每个地块的更新次数
dob_count = dob.groupby(['bbl', 'year']).size().reset_index(name='CO_count')

print(f"✅ DOB 数据加载成功，共 {len(dob)} 条原始记录，{len(dob_count)} 个有效地块-年份对")

# =============================
# Step 3：合并 PLUTO 与 DOB，计算更新强度
# =============================
merged = pluto.merge(dob_count, on=['bbl', 'year'], how='left').fillna({'CO_count': 0})

# 按 Borough 聚合
update_index = (
    merged.groupby(['borough', 'year'])
    .agg({'CO_count':'sum', 'bbl':'count'})
    .reset_index()
)
update_index['UpdateIndex'] = update_index['CO_count'] / update_index['bbl']
update_index.to_csv("update_index_by_borough.csv", index=False)

print("✅ 已导出 update_index_by_borough.csv")

# =============================
# Step 4：轻量版 Borough 热力地图
# =============================
borough_summary = update_index.groupby(['borough', 'year'])['UpdateIndex'].mean().reset_index()

# Borough 中心点（手动定义）
borough_centers = {
    'Manhattan': [40.7831, -73.9712],
    'Bronx': [40.8448, -73.8648],
    'Brooklyn': [40.6782, -73.9442],
    'Queens': [40.7282, -73.7949],
    'Staten Island': [40.5795, -74.1502]
}

m = folium.Map(location=[40.7128, -74.0060], zoom_start=10)

for b, g in borough_summary.groupby('borough'):
    mean_val = g['UpdateIndex'].mean()
    folium.CircleMarker(
        location=borough_centers[b],
        radius=10 + mean_val*200,  # 半径随更新强度变化
        popup=f"{b} 平均更新指数: {mean_val:.3f}",
        color='crimson',
        fill=True,
        fill_color='orange',
        fill_opacity=0.7
    ).add_to(m)

m.save("update_index_map_light.html")
print("✅ 已生成轻量版 update_index_map_light.html （几秒完成）")

# =============================
# Step 5：汇总输出结果
# =============================
summary = (
    update_index.groupby('borough')['UpdateIndex']
    .describe(percentiles=[0.25,0.5,0.75])
    .round(4)
)
print("\n📊 各行政区建筑更新强度统计：")
print(summary)
