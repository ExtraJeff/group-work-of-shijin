# -*- coding: utf-8 -*-
"""
阶段六 · NYC 社区应急特征聚类分析
----------------------------------------------
功能概述：
1. 数据准备与预处理
   - 读取阶段五生成的EMCI指数数据集
   - 提取2024年最新数据作为分析基准
   - 数据清洗与缺失值处理

2. 多维度特征聚类
   - 基于建筑更新强度、通信能力、需求强度、协同度与综合管控指数
   - 采用K-Means算法进行社区分类
   - 固定4个聚类类别便于策略制定

3. 聚类结果可视化
   - PCA降维散点图展示聚类分布
   - 空间分布地图显示地理格局
   - 统计图表对比各类别特征差异

4. 聚类类型识别与命名
   - 根据各类别特征表现进行语义化命名
   - 生成聚类统计报告
   - 提供针对性政策建议基础

输入数据：
- EMCI指数数据集 (emci_summary_by_nta.csv)
- NTA社区边界数据 (nynta2020.shp)

输出成果：
- 聚类分析结果数据集
- PCA降维可视化图
- 空间聚类分布图  
- 聚类统计对比图
- 各类别平均指标表
"""

import os
import pandas as pd
import geopandas as gpd
import numpy as np
from sklearn.preprocessing import StandardScaler, PowerTransformer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

# ===============================
# 设置中文字体（防止标签乱码）
# ===============================
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ===============================
# 路径配置
# ===============================
phase6_output_dir = r"C:\Users\Jeffery\Desktop\石进大作业\Phase6\outputs"
os.makedirs(phase6_output_dir, exist_ok=True)

data_path = r"C:\Users\Jeffery\Desktop\石进大作业\Phase5\outputs\emci_summary_by_nta.csv"
nta_path = r"C:\Users\Jeffery\Desktop\石进大作业\社区级别边界\nynta2020_25c\nynta2020.shp"

# ===============================
# 1. 数据读取与预处理
# ===============================
print("📘 正在读取EMCI指数数据...")
df = pd.read_csv(data_path)

# 提取2024年作为分析基准年
df_2024 = df[df["year"] == 2024].copy()
print(f"📊 2024年有效社区样本数：{len(df_2024)}")

# 定义聚类分析特征维度
features = ["UpdateIndex", "eci", "D", "ECS", "EMCI"]
df_2024[features] = df_2024[features].fillna(df_2024[features].mean())

# ===============================
# 2. 特征工程与标准化
# ===============================
print("⚙️ 正在进行特征变换与标准化处理...")

# 使用Yeo-Johnson变换改善特征分布
pt = PowerTransformer(method="yeo-johnson")
X_trans = pt.fit_transform(df_2024[features])

# 标准化处理消除量纲影响
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_trans)

# ===============================
# 3. K-Means聚类分析
# ===============================
n_clusters = 4
print(f"🔍 执行K-Means聚类分析（类别数={n_clusters}）...")

kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
df_2024["Cluster"] = kmeans.fit_predict(X_scaled)

# 计算并显示聚类中心
centers = pd.DataFrame(kmeans.cluster_centers_, columns=features)
centers = pd.DataFrame(scaler.inverse_transform(pt.inverse_transform(kmeans.cluster_centers_)), columns=features)
print("\n📈 各类别特征中心值：")
print(centers.round(3))

# ===============================
# 4. 聚类语义化命名
# ===============================
def name_cluster(row):
    """根据特征表现对聚类结果进行语义化命名"""
    if row["EMCI"] >= df_2024["EMCI"].quantile(0.75):
        return "高能力综合区"
    elif row["ECS"] >= df_2024["ECS"].quantile(0.7):
        return "高协同区域"
    elif row["D"] >= df_2024["D"].quantile(0.7):
        return "高需求更新区"
    elif row["eci"] <= df_2024["eci"].quantile(0.3):
        return "低支撑脆弱区"
    else:
        return "稳定中等区"

df_2024["ClusterName"] = df_2024.apply(name_cluster, axis=1)

# ===============================
# 5. 聚类结果统计分析
# ===============================
cluster_summary = df_2024.groupby("ClusterName")[features].mean().round(3)
cluster_summary["样本数"] = df_2024["ClusterName"].value_counts()
print("\n📊 各类别特征平均值统计：")
print(cluster_summary)

# 保存聚类统计结果
cluster_summary.to_csv(
    os.path.join(phase6_output_dir, "Cluster_Avg_Indicators.csv"),
    encoding="utf-8-sig"
)

# ===============================
# 6. PCA降维可视化
# ===============================
print("🎨 生成PCA降维聚类散点图...")

# 执行PCA降维
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

# 将降维结果添加到数据集
df_2024["PC1"] = X_pca[:, 0]
df_2024["PC2"] = X_pca[:, 1]

# 定义聚类颜色方案
cluster_colors = {
    "高能力综合区": "#E74C3C",    # 红色 - 突出重要区域
    "高协同区域": "#3498DB",      # 蓝色 - 代表协同
    "高需求更新区": "#F39C12",    # 橙色 - 代表需求
    "低支撑脆弱区": "#2ECC71",    # 绿色 - 代表基础支撑
    "稳定中等区": "#9B59B6"       # 紫色 - 中性色
}

# 创建PCA散点图
plt.figure(figsize=(10, 8))
plt.scatter(
    df_2024["PC1"], 
    df_2024["PC2"],
    c=df_2024["ClusterName"].map(cluster_colors),
    s=80, 
    edgecolor="white", 
    linewidth=1.2,
    alpha=0.8
)

# 添加图例
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=color, label=cluster, edgecolor='white', linewidth=1)
    for cluster, color in cluster_colors.items()
    if cluster in df_2024["ClusterName"].unique()
]

plt.legend(
    handles=legend_elements,
    title="社区类型",
    bbox_to_anchor=(1.05, 1),
    loc="upper left",
    frameon=True,
    fancybox=True,
    shadow=True,
    fontsize=10
)

plt.title("NTA社区应急特征聚类分析（PCA降维可视化）", fontsize=16, pad=20, fontweight='bold')
plt.xlabel(f"主成分1 (方差解释度: {pca.explained_variance_ratio_[0]:.2%})", fontsize=12)
plt.ylabel(f"主成分2 (方差解释度: {pca.explained_variance_ratio_[1]:.2%})", fontsize=12)

# 图表样式优化
plt.grid(True, alpha=0.3, linestyle='--')
plt.gca().set_facecolor('#f8f9fa')
plt.tight_layout()

# 保存PCA图
pca_png = os.path.join(phase6_output_dir, "emci_summary_by_nta_PCA_clusters.png")
plt.savefig(pca_png, dpi=300, bbox_inches="tight", facecolor='white')
plt.close()
print(f"✅ PCA聚类散点图已保存：{pca_png}")

# ===============================
# 7. 空间聚类分布可视化
# ===============================
print("🗺️ 生成聚类空间分布地图...")

# 读取社区边界数据
nta = gpd.read_file(nta_path).to_crs(epsg=4326)

# 合并聚类结果与空间数据
nta_merge = nta.merge(df_2024, on="NTAName", how="left")

# 创建空间分布图
fig, ax = plt.subplots(1, 1, figsize=(12, 10))

# 按聚类类型分组绘制，确保颜色一致性
for cluster_name in nta_merge['ClusterName'].dropna().unique():
    cluster_data = nta_merge[nta_merge['ClusterName'] == cluster_name]
    color = cluster_colors[cluster_name]
    cluster_data.plot(
        ax=ax,
        color=color,
        edgecolor="white",
        linewidth=0.6,
        alpha=0.9,
        label=cluster_name
    )

# 处理无数据区域
no_data = nta_merge[nta_merge['ClusterName'].isna()]
if not no_data.empty:
    no_data.plot(
        ax=ax,
        color="#cccccc",
        edgecolor="white",
        linewidth=0.6,
        alpha=0.5,
        label="无数据"
    )

# 创建自定义图例
from matplotlib.patches import Patch
legend_elements = []
for cluster in nta_merge['ClusterName'].dropna().unique():
    legend_elements.append(
        Patch(facecolor=cluster_colors[cluster], 
              edgecolor='white',
              linewidth=1,
              label=cluster)
    )
if not no_data.empty:
    legend_elements.append(
        Patch(facecolor="#cccccc",
              edgecolor='white',
              linewidth=1,
              label="无数据")
    )

ax.legend(
    handles=legend_elements,
    title="社区应急特征类型",
    loc="upper left",
    bbox_to_anchor=(0, 1),
    frameon=True,
    fancybox=True,
    shadow=True,
    fontsize=11,
    title_fontsize=12
)

ax.set_title(
    "纽约市社区应急特征聚类空间分布（2024年）", 
    fontsize=18, 
    pad=20, 
    fontweight='bold',
    color='#2C3E50'
)

# 添加数据说明
ax.text(
    0.5, 0.02,
    "基于建筑更新强度、通信能力、需求强度、协同度与综合管控指数的K-Means聚类分析",
    ha="center", 
    va="bottom", 
    fontsize=11, 
    color="#7F8C8D", 
    transform=ax.transAxes,
    style='italic'
)

ax.axis("off")
ax.set_facecolor("#ffffff")
plt.tight_layout()

# 保存空间分布图
map_png = os.path.join(phase6_output_dir, "emci_summary_by_nta_ClusterMap.png")
plt.savefig(map_png, dpi=300, bbox_inches="tight", facecolor='white')
plt.close()
print(f"✅ 空间聚类分布图已保存：{map_png}")

# ===============================
# 8. 聚类统计对比分析
# ===============================
print("📈 生成聚类统计对比图表...")

# 创建多子图统计面板
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('社区应急特征聚类统计对比分析', fontsize=18, fontweight='bold', y=0.95)

# 1. EMCI指数对比
cluster_emci = df_2024.groupby('ClusterName')['EMCI'].mean().sort_values(ascending=False)
bars1 = axes[0,0].bar(range(len(cluster_emci)), cluster_emci.values, 
                     color=[cluster_colors.get(cluster, '#95a5a6') for cluster in cluster_emci.index],
                     edgecolor='white', linewidth=1.5)
axes[0,0].set_title('平均EMCI指数对比', fontsize=14, fontweight='bold')
axes[0,0].set_xticks(range(len(cluster_emci)))
axes[0,0].set_xticklabels(cluster_emci.index, rotation=45, ha='right')
axes[0,0].bar_label(bars1, fmt='%.3f', padding=3)

# 2. ECS协同指数对比
cluster_ecs = df_2024.groupby('ClusterName')['ECS'].mean().sort_values(ascending=False)
bars2 = axes[0,1].bar(range(len(cluster_ecs)), cluster_ecs.values,
                     color=[cluster_colors.get(cluster, '#95a5a6') for cluster in cluster_ecs.index],
                     edgecolor='white', linewidth=1.5)
axes[0,1].set_title('平均ECS协同指数对比', fontsize=14, fontweight='bold')
axes[0,1].set_xticks(range(len(cluster_ecs)))
axes[0,1].set_xticklabels(cluster_ecs.index, rotation=45, ha='right')
axes[0,1].bar_label(bars2, fmt='%.3f', padding=3)

# 3. 需求指数对比
cluster_d = df_2024.groupby('ClusterName')['D'].mean().sort_values(ascending=False)
bars3 = axes[1,0].bar(range(len(cluster_d)), cluster_d.values,
                     color=[cluster_colors.get(cluster, '#95a5a6') for cluster in cluster_d.index],
                     edgecolor='white', linewidth=1.5)
axes[1,0].set_title('平均需求指数对比', fontsize=14, fontweight='bold')
axes[1,0].set_xticks(range(len(cluster_d)))
axes[1,0].set_xticklabels(cluster_d.index, rotation=45, ha='right')
axes[1,0].bar_label(bars3, fmt='%.3f', padding=3)

# 4. 社区数量分布
cluster_counts = df_2024['ClusterName'].value_counts()
bars4 = axes[1,1].bar(range(len(cluster_counts)), cluster_counts.values,
                     color=[cluster_colors.get(cluster, '#95a5a6') for cluster in cluster_counts.index],
                     edgecolor='white', linewidth=1.5)
axes[1,1].set_title('各类型社区数量分布', fontsize=14, fontweight='bold')
axes[1,1].set_xticks(range(len(cluster_counts)))
axes[1,1].set_xticklabels(cluster_counts.index, rotation=45, ha='right')
axes[1,1].bar_label(bars4, fmt='%d', padding=3)

plt.tight_layout()

# 保存统计图表
stats_png = os.path.join(phase6_output_dir, "emci_summary_by_nta_ClusterStats.png")
plt.savefig(stats_png, dpi=300, bbox_inches="tight", facecolor='white')
plt.close()
print(f"✅ 聚类统计对比图已保存：{stats_png}")

# ===============================
# 9. 结果导出与总结
# ===============================
output_csv = os.path.join(phase6_output_dir, "emci_summary_by_nta_ClusterResults.csv")
df_2024.to_csv(output_csv, index=False, encoding="utf-8-sig")

print("\n🎉 阶段六聚类分析完成总结")
print("=" * 50)
print("📊 核心分析成果:")
print("  • 基于5个维度的社区应急特征聚类")
print("  • 识别4种典型社区类型")
print("  • 完整的可视化分析报告")
print()
print("🔍 识别出的社区类型:")
print("  • 高能力综合区 - EMCI指数领先")
print("  • 高协同区域 - 通信协同能力突出") 
print("  • 高需求更新区 - 建筑需求强度高")
print("  • 低支撑脆弱区 - 基础设施支撑不足")
print("  • 稳定中等区 - 各项指标均衡")
print()
print("📁 输出文件清单:")
print(f"  • {output_csv} (聚类结果数据集)")
print(f"  • {pca_png} (PCA降维可视化)")
print(f"  • {map_png} (空间分布地图)")
print(f"  • {stats_png} (统计对比图表)")
print("  • Cluster_Avg_Indicators.csv (类别特征统计)")