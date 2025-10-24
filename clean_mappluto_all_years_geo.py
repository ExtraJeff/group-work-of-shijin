"""
MapPLUTO 多年份整合脚本（含几何字段）
------------------------------------------------------
功能：
1. 自动读取 2016–2025 年的 MapPLUTO shapefile；
2. 自动识别年份；
3. 处理 2016–2017 年的分行政区结构；
4. 保留核心字段 + geometry；
5. 输出统一 GeoJSON 文件，可用于后续空间分析与可视化。
"""

import geopandas as gpd
import pandas as pd
import glob
import os
import re

# ========== 参数 ==========
DATA_DIR = "C:/Users/Jeffery/Desktop/石进大作业/MapPluto"      # 修改为你的 MapPLUTO 根目录
OUTPUT_FILE = "outputs/pluto_all_years.geojson"

# 常用字段统一映射
COLUMN_MAP = {
    "BBL": "bbl",
    "bbl": "bbl",
    "LandUse": "land_use",
    "landuse": "land_use",
    "YearBuilt": "year_built",
    "yearbuilt": "year_built",
    "BldgArea": "bldg_area",
    "bldgarea": "bldg_area",
    "LotArea": "lot_area",
    "lotarea": "lot_area",
    "UnitsRes": "units_res",
    "unitsres": "units_res"
}

# ========== 读取函数 ==========
def load_citywide(path, year):
    """读取单一 citywide shapefile"""
    print(f"📂 读取 {year} 年 citywide 数据: {path}")
    gdf = gpd.read_file(path)
    gdf.columns = [c.lower() for c in gdf.columns]
    gdf.rename(columns=COLUMN_MAP, inplace=True)
    gdf["year"] = year
    return gdf


def load_by_borough(folder, year):
    """读取分行政区的 shapefile 并合并"""
    print(f"📂 读取 {year} 年分行政区数据: {folder}")
    borough_shps = glob.glob(os.path.join(folder, "*/*.shp"))
    if not borough_shps:
        borough_shps = glob.glob(os.path.join(folder, "*.shp"))
    parts = []
    for shp in borough_shps:
        try:
            gdf = gpd.read_file(shp)
            gdf.columns = [c.lower() for c in gdf.columns]
            gdf.rename(columns=COLUMN_MAP, inplace=True)
            parts.append(gdf)
            print(f"  ✅ 载入 {os.path.basename(shp)} ({len(gdf)} 条)")
        except Exception as e:
            print(f"  ⚠️ 无法读取 {shp}: {e}")
    if parts:
        merged = pd.concat(parts, ignore_index=True)
        merged["year"] = year
        return gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:2263")
    else:
        return None


# ========== 主程序 ==========
all_gdfs = []

for folder in sorted(os.listdir(DATA_DIR)):
    year_match = re.search(r"20?(\d{2})", folder)
    if not year_match:
        continue
    year = int("20" + year_match.group(1))

    folder_path = os.path.join(DATA_DIR, folder)

    # 2016–2017 分行政区，之后为 citywide
    if year <= 2017:
        gdf = load_by_borough(folder_path, year)
    else:
        # 查找 shapefile
        shp_files = glob.glob(os.path.join(folder_path, "*.shp"))
        if not shp_files:
            print(f"⚠️ 未找到 {year} 年 shapefile")
            continue
        gdf = load_citywide(shp_files[0], year)

    if gdf is not None:
        all_gdfs.append(gdf)

# 合并
if not all_gdfs:
    print("❌ 未读取到任何有效数据。")
else:
    gdf_all = pd.concat(all_gdfs, ignore_index=True)

    # 坐标转换为 WGS84（经纬度）
    gdf_all = gdf_all.to_crs(epsg=4326)

    # 仅保留关键字段
    core_fields = ["bbl", "land_use", "year_built", "bldg_area", "lot_area", "units_res", "year", "geometry"]
    for col in core_fields:
        if col not in gdf_all.columns:
            gdf_all[col] = pd.NA

    gdf_all = gdf_all[core_fields]

    # 导出
    os.makedirs("outputs", exist_ok=True)
    gdf_all.to_file(OUTPUT_FILE, driver="GeoJSON")

    print(f"\n✅ 已成功输出统一文件：{OUTPUT_FILE}")
    print(f"📏 数据规模：{len(gdf_all):,} 条地块记录")
    print("🌎 坐标系：EPSG:4326（经纬度）")
