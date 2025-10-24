"""
PLUTO 多年份字段统一清洗脚本（支持 vX 命名格式）
------------------------------------------------
功能：
1. 自动读取 data/pluto/ 下的所有 pluto_20xx 或 pluto_1xvX 文件；
2. 自动识别文件名中的年份（如 pluto_16v2.csv → 2016）；
3. 统一核心字段命名；
4. 对早期版本缺失字段自动补 NaN；
5. 输出统一结构的年度汇总文件（pluto_all_years.csv）。
"""

import pandas as pd
import geopandas as gpd
import glob
import os
import re

# ========== 参数 ==========
DATA_DIR = "C:/Users/Jeffery/Desktop/石进大作业/Pluto/scripts"
OUTPUT_FILE = "scripts/pluto_all_years.csv"

# 统一字段映射表（仅列出常见字段，可按实际情况补充）
COLUMN_MAP = {
    "BBL": "bbl",
    "bbl": "bbl",
    "LandUse": "land_use",
    "landuse": "land_use",
    "Landuse": "land_use",
    "YearBuilt": "year_built",
    "yearbuilt": "year_built",
    "BldgArea": "bldg_area",
    "bldgarea": "bldg_area",
    "LotArea": "lot_area",
    "lotarea": "lot_area",
    "UnitsRes": "units_res",
    "unitsres": "units_res",
    "NumBldgs": "numbldgs",
    "NumBldg": "numbldgs",
    "LtdHeight": "ltdheight",
    "ltdheight": "ltdheight",
    "EDesignNum": "edesignum",
    "ExemptTot": "exempttot",
    "Ext": "ext",
}

# ========== 读取文件 ==========
files = sorted(glob.glob(os.path.join(DATA_DIR, "pluto_*.csv")))
if len(files) == 0:
    files = sorted(glob.glob(os.path.join(DATA_DIR, "pluto_*.geojson")))

print(f"共检测到 {len(files)} 个年度文件")

all_data = []

for f in files:
    # ---------- 自动识别年份 ----------
    fname = os.path.basename(f)
    match = re.search(r"(\d{2})(?=v?\d)", fname)
    if match:
        year_short = int(match.group(1))
        year = 2000 + year_short
    else:
        # 如果找不到年份，尝试匹配四位数字
        match4 = re.search(r"20\d{2}", fname)
        if match4:
            year = int(match4.group(0))
        else:
            print(f"⚠️ 未能在文件名中识别年份: {fname}，默认设为 0")
            year = 0

    print(f"正在处理 {year} 年数据: {fname}")

    # ---------- 读取 ----------
    try:
        if f.endswith(".geojson"):
            df = gpd.read_file(f)
        else:
            df = pd.read_csv(f, low_memory=False)
    except Exception as e:
        print(f"⚠️ 无法读取 {f}: {e}")
        continue

    # ---------- 字段标准化 ----------
    df.columns = [c.strip().lower() for c in df.columns]
    df.rename(columns=COLUMN_MAP, inplace=True)

    # ---------- 提取核心字段 ----------
    core_fields = [
        "bbl", "land_use", "year_built", "bldg_area", "lot_area", "units_res",
        "numbldgs", "ltdheight", "edesignum", "exempttot", "ext"
    ]

    # 对缺失字段补空列
    for field in core_fields:
        if field not in df.columns:
            df[field] = pd.NA

    # ---------- 添加年份 ----------
    df["year"] = year

    # ---------- 保留核心列 ----------
    df = df[core_fields + ["year"]]
    all_data.append(df)

# ========== 合并与导出 ==========
if len(all_data) == 0:
    print("❌ 未读取到任何有效数据，请检查文件路径或格式。")
else:
    pluto_all = pd.concat(all_data, ignore_index=True)
    pluto_all.drop_duplicates(subset=["bbl", "year"], inplace=True)

    os.makedirs("outputs", exist_ok=True)
    pluto_all.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\n✅ 已成功输出统一文件：", OUTPUT_FILE)
    print(f"数据规模：{pluto_all.shape[0]} 行 × {pluto_all.shape[1]} 列")
