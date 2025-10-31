# NYC应急管控研究项目

## 项目简介

本项目旨在对纽约市(NYC)的应急管控能力进行综合分析和评估。通过整合PLUTO地块数据、LinkNYC通信设施数据等多源数据，构建了应急管控能力指数(EMCI)，并通过时空分析、聚类分析等方法，为城市应急管理提供决策支持。

## 环境配置指南

### 1. Python环境准备

本项目推荐使用Python 3.9或3.10版本。建议创建独立的虚拟环境以避免依赖冲突：

```bash
# 使用conda创建虚拟环境
conda create -n nyc_emci python=3.9
conda activate nyc_emci

# 或使用venv
python -m venv nyc_emci
# Windows激活
nyc_emci\Scripts\activate
# Linux/Mac激活
source nyc_emci/bin/activate
```

### 2. 安装依赖库

项目所需的所有依赖已整理在`requirements.txt`文件中。请运行以下命令安装：

```bash
pip install -r requirements.txt
```

### 3. 主要依赖说明

- **数据处理库**：pandas, numpy, geopandas
- **地理空间分析**：shapely, fiona, pyproj
- **可视化库**：matplotlib, folium, seaborn, branca
- **机器学习**：scikit-learn
- **Web界面**：dash, dash-bootstrap-components

### 4. 环境变量配置

部分脚本中的路径配置需要根据实际情况修改。主要包括：

- `BASE_PATH`/`BASE_DIR`：项目根目录
- 数据源文件路径

## 项目结构

```
├── MapPluto/          # 原始PLUTO地图数据（按年份分类）
├── Pluto/             # PLUTO数据集（CSV格式，按年份分类）
├── Phase1/            # 阶段一：建筑变化分析
│   ├── outputs/       # 输出结果
├── Phase2/            # 阶段二：更新指数计算
│   ├── outputs/       # 输出结果
├── Phase3/            # 阶段三：通信设施分析
│   ├── outputs/       # 输出结果
├── Phase4/            # 阶段四：需求指数建模
│   ├── outputs/       # 输出结果
├── Phase5/            # 阶段五：EMCI指数计算
│   ├── outputs/       # 输出结果
├── Phase6/            # 阶段六：聚类分析
│   ├── outputs/       # 输出结果
├── 社区级别边界/       # NTA社区边界数据
├── 自治区级别边界/      # 行政区边界数据
├── nyc_dashboard.py   # 主仪表盘应用
├── requirements.txt   # 项目依赖
└── README.md          # 项目说明文档
```

## 主要功能模块

### 1. 数据预处理与清洗

- **clean_pluto_all_years.py**：统一多年份PLUTO数据的字段命名和结构
- **数据标准化**：确保不同来源数据的坐标系统一致（主要使用EPSG:4326和EPSG:2263）

### 2. 分析阶段

- **阶段一**：建筑变化检测与可视化
- **阶段二**：计算更新指数
- **阶段三**：通信设施密度分析（ECI指数）
- **阶段四**：建筑需求因子建模
- **阶段五**：综合应急管控能力指数(EMCI)计算与预测
- **阶段六**：社区聚类分析

### 3. 可视化与展示

- **交互式地图**：使用folium创建时空动态地图
- **仪表盘应用**：基于Dash的Web界面，整合各阶段分析结果

## 使用指南

### 运行完整分析流程

项目分析分为6个主要阶段，建议按顺序执行各阶段脚本：

1. 首先运行Phase1中的数据清洗脚本
2. 依次执行各阶段的分析脚本
3. 最后可通过`nyc_dashboard.py`启动交互式仪表盘

### 运行仪表盘

```bash
python nyc_dashboard.py
```

启动后，在浏览器中访问相应地址即可查看交互式分析结果。

## 注意事项

1. 项目使用了大量地理空间数据，确保有足够的磁盘空间
2. 部分计算可能较为耗时，特别是涉及空间连接和聚类分析的部分
3. 确保正确设置文件路径，部分脚本中的路径为示例路径，需要根据实际环境修改
4. 如需处理更大规模数据，建议调整内存分配或考虑分批处理策略

## 故障排除

- **依赖安装问题**：对于geopandas等地理空间库安装失败，可尝试使用conda安装
- **路径错误**：检查脚本中的路径设置是否与实际文件位置一致
- **数据编码问题**：确保读取CSV文件时使用正确的编码（utf-8）

## 作者与贡献

NYC应急管控研究项目组

## 许可证

[待定]