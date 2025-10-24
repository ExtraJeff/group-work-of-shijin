"""
阶段 1：建筑演化识别与变化分类分析
--------------------------------------
输入：outputs/pluto_all_years.csv
输出：
 - outputs/pluto_change_summary.csv  （每个地块的变化分类）
 - outputs/update_ratio_by_year.csv （年度更新比例）
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

INPUT_FILE = "outputs/pluto_all_years.csv"
OUTPUT_SUMMARY = "outputs/pluto_change_summary.csv"
OUTPUT_TREND = "outputs/update_ratio_by_year.csv"

print("📘 正在读取数据...")
df = pd.read_csv(INPUT_FILE, low_memory=False)

# ========== 数据预处理 ==========
df = df.dropna(subset=["bbl", "year"])  # 移除无效行
df["bbl"] = df["bbl"].astype(str).str.strip()
df["year"] = df["year"].astype(int)
df = df.sort_values(["bbl", "year"]).reset_index(drop=True)

# ========== 构建变化检测函数 ==========
def classify_changes(g):
    """对单个 BBL 的时间序列分析"""
    g = g.sort_values("year")
    result = {
        "first_year": g["year"].min(),
        "last_year": g["year"].max(),
        "years_recorded": len(g),
        "year_built_first": g["year_built"].iloc[0],
        "year_built_last": g["year_built"].iloc[-1],
        "land_use_first": g["land_use"].iloc[0],
        "land_use_last": g["land_use"].iloc[-1],
        "bldg_area_min": g["bldg_area"].min(),
        "bldg_area_max": g["bldg_area"].max(),
        "units_res_min": g["units_res"].min(),
        "units_res_max": g["units_res"].max(),
    }

    # 判定变化类型
    rebuilt = (result["year_built_first"] != result["year_built_last"]) and (result["year_built_last"] > 0)
    use_change = (result["land_use_first"] != result["land_use_last"])
    area_increase = (result["bldg_area_max"] - result["bldg_area_min"]) > 0.1 * result["bldg_area_min"]
    units_increase = (result["units_res_max"] - result["units_res_min"]) > 0

    if rebuilt:
        change_type = "Rebuilt"
    elif use_change:
        change_type = "UseChange"
    elif area_increase or units_increase:
        change_type = "Expanded"
    else:
        change_type = "Stable"

    result["change_type"] = change_type
    return pd.Series(result)

print("🔍 正在检测地块变化...")
summary = df.groupby("bbl").apply(classify_changes).reset_index()

# ========== 统计各类变化数量 ==========
change_stats = summary["change_type"].value_counts(normalize=True).mul(100).round(2)
print("\n📊 变化类型比例（%）：")
print(change_stats)

# ========== 年度变化趋势 ==========
update_trend = (
    df.groupby("year")["bbl"].nunique().diff()
    / df.groupby("year")["bbl"].nunique().shift(1)
).fillna(0)
update_trend = update_trend.rename("update_ratio").reset_index()

# ========== 保存结果 ==========
os.makedirs("outputs", exist_ok=True)
summary.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8-sig")
update_trend.to_csv(OUTPUT_TREND, index=False, encoding="utf-8-sig")

print(f"\n✅ 已输出文件：{OUTPUT_SUMMARY}")
print(f"✅ 已输出文件：{OUTPUT_TREND}")

# ========== 可视化 ==========
plt.figure(figsize=(10,5))
plt.plot(update_trend["year"], update_trend["update_ratio"], marker="o")
plt.title("Annual Building Update Ratio (2016–2025)")
plt.xlabel("Year")
plt.ylabel("Update Ratio (Relative)")
plt.grid(True)
plt.tight_layout()
plt.savefig("outputs/building_update_trend.png", dpi=300)
plt.show()

print("\n📈 已生成年度变化趋势图：outputs/building_update_trend.png")
