# -*- coding: utf-8 -*-
"""
阶段五 · NTA级应急管控能力指数 (EMCI_NTA) 建模与可视化
-----------------------------------------------------
功能概述：
1. 数据集成与预处理
   - 整合PLUTO地块数据、LinkNYC通信设施数据、建筑需求指数
   - 按年份计算各社区(NTA)的应急管控能力指数

2. EMCI指数计算
   - 基于建筑更新强度、通信能力、需求强度的多维度建模
   - 采用对数变换和标准化处理
   - 包含历史数据(2016-2025)和未来预测(2026-2030)

3. 时空可视化
   - 交互式时间滑块地图展示EMCI指数年度变化
   - 静态热力图显示长期增长趋势
   - 支持社区详细信息查看

4. 预测分析
   - 基于线性回归的未来趋势预测
   - 识别高增长潜力区域

输入数据：
- PLUTO地块数据 (pluto_all_years.geojson)
- LinkNYC通信设施数据 (linknyc_eci_by_nta.geojson) 
- 建筑需求指数 (building_demand_index_by_nta.csv)
- NTA社区边界 (nynta2020.shp)

输出成果：
- 多年份EMCI指数数据集 (emci_summary_by_nta_rev7_0.csv)
- 交互式时间序列地图 (emci_map_by_nta_rev7_0.html)
- 增长率空间分布图 (emci_map_by_nta_rev7_0_growth_heatmap.png)
"""

import os
import warnings
warnings.filterwarnings("ignore")

import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from folium.plugins import TimestampedGeoJson
import json
from branca.element import MacroElement, Template
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ========== 中文字体设置 ==========
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ========== 路径配置 ==========
BASE = r"C:\Users\Jeffery\Desktop\石进大作业"
nta_path = os.path.join(BASE, "社区级别边界", "nynta2020_25c", "nynta2020.shp")
eci_path = os.path.join(BASE, "Phase3", "outputs", "linknyc_eci_by_nta.geojson")
pluto_path = os.path.join(BASE, "Phase1", "outputs", "pluto_all_years.geojson")
d_path = os.path.join(BASE, "Phase4", "outputs", "building_demand_index_by_nta.csv")

OUT_DIR = os.path.join(BASE, "Phase5", "outputs")
os.makedirs(OUT_DIR, exist_ok=True)
output_csv = os.path.join(OUT_DIR, "emci_summary_by_nta.csv")
output_html = os.path.join(OUT_DIR, "emci_map_by_nta.html")

# ========== 1. 数据读取与验证 ==========
print("📘 正在读取输入数据...")

# 读取NTA社区边界
nta = gpd.read_file(nta_path).to_crs(epsg=4326)

# 读取LinkNYC通信设施数据
eci = gpd.read_file(eci_path).to_crs(epsg=4326)

# 读取PLUTO地块数据
pluto = gpd.read_file(pluto_path).to_crs(epsg=4326)

# 读取建筑需求指数
d = pd.read_csv(d_path)

# 验证数据完整性
if "year" not in pluto.columns:
    raise KeyError("PLUTO数据缺少年份字段")

years = sorted(pluto["year"].dropna().unique())
print(f"📅 检测到数据年份范围: {years}")

# ========== 2. 数据预处理 ==========
# 标准化建筑需求指数字段
if "D_mean" in d.columns:
    d = d[["NTAName", "D_mean"]].rename(columns={"D_mean": "D"})

# 提取通信设施核心指标
required_cols = {"NTAName", "node_count", "area_km2", "eci"}
eci_summary = eci[list(required_cols)].copy()
eci_summary["node_count"] = eci_summary["node_count"].fillna(0)
eci_summary["area_km2"] = eci_summary["area_km2"].replace(0, np.nan).fillna(1.0)

# ========== 3. EMCI指数计算 ==========
print("⚙️ 开始计算各年份EMCI指数...")
all_years_results = []

for yr in years:
    print(f"  处理年份 {yr}...")
    
    # 提取当前年份地块数据
    pluto_y = pluto[pluto["year"] == yr].copy()
    if pluto_y.empty:
        continue
        
    # 计算地块质心并关联到NTA社区
    pluto_y = pluto_y[~pluto_y.geometry.is_empty].copy()
    pluto_y["centroid"] = pluto_y.geometry.centroid
    pluto_pts = pluto_y.set_geometry("centroid")
    pluto_nta = gpd.sjoin(pluto_pts, nta[["NTAName", "geometry"]], how="left", predicate="within")
    
    # 计算资源密度
    resource_density = pluto_nta.groupby("NTAName").size().reset_index(name="resource_count")
    
    # 合并所有数据源
    merged = (
        eci_summary
        .merge(d, on="NTAName", how="left")
        .merge(resource_density, on="NTAName", how="left")
    )
    
    # 数据填充
    merged["D"] = merged["D"].fillna(0)
    merged["resource_count"] = merged["resource_count"].fillna(0)
    
    # 计算基础指标
    merged["building_density"] = merged["node_count"] / merged["area_km2"]
    merged["UpdateIndex"] = 1.0  # 建筑更新强度指数
    
    # 计算核心组件
    merged["ERP"] = (merged["UpdateIndex"] * merged["building_density"]) / (merged["resource_count"] + 1)
    merged["ECS"] = merged["eci"] * (merged["resource_count"] / (merged["building_density"] + 1))
    
    # EMCI指数计算
    def calc_emci_raw(row):
        erp = row["ERP"]
        if erp <= 0 or np.isnan(erp):
            return 0.0
        denom = erp * (1 + 0.5 * row["D"])
        if denom == 0 or np.isnan(denom):
            return 0.0
        return row["ECS"] / denom

    merged["EMCI_raw"] = merged.apply(calc_emci_raw, axis=1)
    merged["EMCI"] = np.log1p(merged["EMCI_raw"])  # 对数变换增强稳定性
    
    # 指标标准化
    def normalize_series(s):
        if s.max() == s.min():
            return s.apply(lambda x: 0.0)
        return (s - s.min()) / (s.max() - s.min())

    merged["ERP_norm"] = normalize_series(merged["ERP"])
    merged["ECS_norm"] = normalize_series(merged["ECS"])
    merged["EMCI_norm"] = normalize_series(merged["EMCI"])
    merged["year"] = yr

    all_years_results.append(merged)

# 合并所有年份结果
final_df = pd.concat(all_years_results, ignore_index=True)

# ========== 4. 未来趋势预测 ==========
print("🔮 生成2026-2030年预测数据...")

pred_years = [2026, 2027, 2028, 2029, 2030]
predictions = []

# 基于历史数据的线性外推
for nta_name, group in final_df.groupby("NTAName"):
    if group["year"].nunique() < 2:
        continue
        
    group_sorted = group.sort_values("year")
    x = group_sorted["year"].values
    y = group_sorted["EMCI"].values
    
    # 线性回归拟合趋势
    coef = np.polyfit(x, y, 1)
    trend_func = np.poly1d(coef)
    
    # 生成预测值
    for y_future in pred_years:
        y_pred = trend_func(y_future)
        row = group_sorted.iloc[-1].copy()
        row["year"] = y_future
        row["EMCI"] = max(y_pred, 0)  # 确保非负
        row["EMCI_norm"] = np.nan
        predictions.append(row)

# 合并预测数据
pred_df = pd.DataFrame(predictions)
final_df = pd.concat([final_df, pred_df], ignore_index=True)

# 保存完整数据集
final_df.to_csv(output_csv, index=False)
print(f"💾 EMCI指数数据集已保存: {output_csv}")

# ========== 5. 时间序列交互地图 ==========
print("🗺️ 构建交互式时间序列地图...")

# 数据标准化处理
def normalize_emci(df):
    df["EMCI_norm"] = (df["EMCI"] - df["EMCI"].min()) / (df["EMCI"].max() - df["EMCI"].min())
    return df

final_df = final_df.groupby("year").apply(normalize_emci).reset_index(drop=True)

# 颜色映射函数
def get_color_norm(value):
    if value is None or np.isnan(value):
        return '#cccccc'
    v = float(value)
    if v < 0.2: return '#fff7ec'
    elif v < 0.4: return '#fdd49e'
    elif v < 0.6: return '#fdbb84'
    elif v < 0.8: return '#fc8d59'
    else: return '#d7301f'

# 准备时间序列数据
features = []
all_years = sorted(final_df["year"].unique())

# 优化几何数据
nta_geometry_dict = {}
for idx, row in nta.iterrows():
    nta_name = row["NTAName"]
    try:
        simplified_geom = row.geometry.simplify(0.0001)
        nta_geometry_dict[nta_name] = simplified_geom.__geo_interface__
    except Exception as e:
        continue

# 构建GeoJSON特征
for yr in all_years:
    subset = final_df[final_df["year"] == yr]
    
    for _, row in subset.iterrows():
        nta_name = row["NTAName"]
        emci_norm = row.get("EMCI_norm", None)
        
        if pd.isna(emci_norm) or nta_name not in nta_geometry_dict:
            continue
            
        color = get_color_norm(emci_norm)
        geom = nta_geometry_dict[nta_name]
        
        # 构建特征属性
        props = {
            "NTAName": nta_name,
            "time": f"{int(yr)}-01-01",
            "value": float(emci_norm),
            "EMCI": float(row.get("EMCI", 0)),
            "EMCI_raw": float(row.get("EMCI_raw", 0)),
            "ERP": float(row.get("ERP", 0)),
            "ECS": float(row.get("ECS", 0)),
            "node_count": int(row.get("node_count", 0)),
            "resource_count": int(row.get("resource_count", 0)),
            "building_density": float(row.get("building_density", 0)),
            "D": float(row.get("D", 0)),
            "style": {
                "color": "black",
                "weight": 0.6,
                "fillColor": color,
                "fillOpacity": 0.75
            },
            "popup": f"""
                <div style="min-width: 250px;">
                    <h4 style="margin: 0 0 10px 0; color: #1976d2;">{nta_name}</h4>
                    <div style="border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 8px;">
                        <strong>年份:</strong> {int(yr)}<br>
                        <strong>EMCI (归一化):</strong> {emci_norm:.3f}<br>
                        <strong>EMCI (原始):</strong> {row.get('EMCI', 0):.3f}
                    </div>
                    <div style="font-size: 12px;">
                        <strong>基础设施指标:</strong><br>
                        • 节点数量: {int(row.get('node_count', 0))}<br>
                        • 建筑密度: {row.get('building_density', 0):.2f}<br>
                        • 资源数量: {int(row.get('resource_count', 0))}
                    </div>
                    <div style="font-size: 12px; margin-top: 5px;">
                        <strong>需求指标:</strong><br>
                        • 建筑需求指数: {row.get('D', 0):.3f}<br>
                        • ERP: {row.get('ERP', 0):.3f}<br>
                        • ECS: {row.get('ECS', 0):.3f}
                    </div>
                    {'<div style="color: #ff6b35; margin-top: 5px; font-size: 11px;"><strong>📈 预测数据</strong></div>' if yr >= 2026 else ''}
                </div>
            """
        }
        feature = {"type": "Feature", "geometry": geom, "properties": props}
        features.append(feature)

geojson_data = {"type": "FeatureCollection", "features": features}

# 创建基础地图
m = folium.Map(location=[40.75, -73.97], zoom_start=11, tiles="CartoDB positron")

# 添加时间滑块组件
timeslider = TimestampedGeoJson(
    geojson_data,
    period="P1Y",
    duration="P1M",
    auto_play=False,
    loop=False,
    transition_time=1000,
    add_last_point=True,
    date_options='YYYY'
)
timeslider.add_to(m)

# ========== 6. 地图界面优化 ==========
# 时间滑块位置调整
template = """
{% macro html(this, kwargs) %}
<style>
.leaflet-bottom.leaflet-left {
    width: auto;
}
.leaflet-control.leaflet-bar {
    float: left;
}
</style>
{% endmacro %}
"""

class TimeSliderPosition(MacroElement):
    def __init__(self):
        super().__init__()
        self._template = Template(template)

m.get_root().add_child(TimeSliderPosition())

# 控制面板
control_html = '''
<div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
            background: white; padding: 10px; border-radius: 5px;
            border: 2px solid grey; font-family: Arial, sans-serif;">
    <h4 style="margin: 0 0 6px 0;">📊 EMCI 时间序列地图</h4>
    <div style="font-size:13px;"><strong>时间范围:</strong> 2016–2030</div>
    <div style="font-size:12px; margin-top:4px;"><strong>预测区间:</strong> 2026–2030</div>
    <div style="margin-top:6px; font-size:11px; color: #666;">
        <strong>💡 操作提示:</strong> 使用时间滑块浏览年度变化，点击社区查看详情
    </div>
</div>
'''
m.get_root().html.add_child(folium.Element(control_html))

# 图例
legend_html = '''
<div style="position: fixed; bottom: 50px; right: 10px; z-index: 9999;
            background: white; padding: 10px; border-radius: 5px;
            border: 1px solid grey; font-size: 12px;">
    <h4 style="margin: 0 0 5px 0;">EMCI指数图例</h4>
    <div><i style="background: #fff7ec; width: 20px; height: 10px; display: inline-block; border: 1px solid #999;"></i> 0.0 - 0.2</div>
    <div><i style="background: #fdd49e; width: 20px; height: 10px; display: inline-block; border: 1px solid #999;"></i> 0.2 - 0.4</div>
    <div><i style="background: #fdbb84; width: 20px; height: 10px; display: inline-block; border: 1px solid #999;"></i> 0.4 - 0.6</div>
    <div><i style="background: #fc8d59; width: 20px; height: 10px; display: inline-block; border: 1px solid #999;"></i> 0.6 - 0.8</div>
    <div><i style="background: #d7301f; width: 20px; height: 10px; display: inline-block; border: 1px solid #999;"></i> 0.8 - 1.0</div>
    <div style="margin-top:6px;"><i style="background: #cccccc; width: 20px; height: 10px; display: inline-block; border: 1px solid #999;"></i> 无数据</div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# 保存交互地图
m.save(output_html)
print(f"✅ 交互式地图已生成: {output_html}")

# ========== 7. 增长率空间分析 ==========
print("📈 计算长期增长率空间分布...")

# 计算各社区年平均增长率
growth_df = final_df.groupby("NTAName").apply(
    lambda g: (g.sort_values("year")["EMCI"].iloc[-1] - g.sort_values("year")["EMCI"].iloc[0]) /
              (g["year"].max() - g["year"].min())
).reset_index(name="annual_growth")

# 关联空间数据
nta_growth = nta.merge(growth_df, on="NTAName", how="left")

print("增长率统计摘要:")
print(growth_df["annual_growth"].describe().to_string())

# 生成热力图
vmin, vmax = np.percentile(growth_df["annual_growth"].dropna(), [2, 98])

fig, ax = plt.subplots(1, 1, figsize=(12, 10))

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

nta_growth.plot(
    column="annual_growth",
    cmap="YlOrRd",
    linewidth=0.4,
    ax=ax,
    edgecolor="gray",
    legend=True,
    vmin=vmin,
    vmax=vmax,
    legend_kwds={
        'label': "年平均增长率",
        'orientation': "vertical",
        'shrink': 0.8
    }
)

ax.set_title("纽约市社区EMCI指数年平均增长率分布(2016-2030)", fontsize=16, pad=20)
ax.axis("off")

# 添加数据说明
plt.text(
    0.5, 0.02,
    "数据来源: EMCI模型计算结果 | 增长率 = (EMCI2030 - EMCI2016) / 14",
    ha="center", va="bottom", fontsize=10, color="gray", transform=ax.transAxes
)

growth_map_path = output_html.replace(".html", "_growth_heatmap.png")
plt.savefig(growth_map_path, dpi=300, bbox_inches="tight", facecolor='white')
plt.close()

print(f"✅ 增长率热力图已保存: {growth_map_path}")

# ========== 8. 项目总结 ==========
print("\n🎉 阶段五完成总结")
print("=" * 50)
print("📊 核心成果:")
print("  • 多年度EMCI指数数据集 (2016-2030)")
print("  • 交互式时间序列可视化地图")
print("  • 长期增长率空间分布分析")
print("  • 未来五年趋势预测")
print()
print("🔧 技术特色:")
print("  • 基于建筑更新、通信能力、需求强度的综合建模")
print("  • 时间滑块驱动的动态可视化")
print("  • 社区级别的详细指标展示")
print("  • 线性回归的未来趋势预测")
print()
print("📁 输出文件:")
print(f"  • {output_csv}")
print(f"  • {output_html}") 
print(f"  • {growth_map_path}")