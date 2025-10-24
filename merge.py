import pandas as pd
import os
from pathlib import Path

# -------------------------- 配置参数（根据实际情况修改） --------------------------
# 存放数据表的文件夹路径（相对路径或绝对路径）
input_folder = "2016v2"
# 输出合并后的文件路径和名称
output_file = "merged_result.csv"  # 支持 .xlsx 或 .csv
# 文件格式（"csv" 或 "excel"）
file_format = "csv"  # 如果是 CSV 文件，改为 "csv"
# --------------------------------------------------------------------------------

# 获取文件夹中所有目标格式的文件
all_files = []
for file in os.listdir(input_folder):
    file_path = os.path.join(input_folder, file)
    # 根据格式筛选文件
    if file_format == "excel" and file.endswith((".xlsx", ".xls")):
        all_files.append(file_path)
    elif file_format == "csv" and file.endswith(".csv"):
        all_files.append(file_path)

if not all_files:
    print(f"错误：在 {input_folder} 中未找到任何 {file_format} 文件")
    exit()

# 合并所有文件
dfs = []
for file in all_files:
    try:
        # 读取文件
        if file_format == "excel":
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)
        # 检查列名是否一致（与第一个文件对比）
        if not dfs:
            first_columns = set(df.columns)
        else:
            if set(df.columns) != first_columns:
                print(f"警告：{file} 的列名与其他文件不一致，已跳过该文件")
                continue
        dfs.append(df)
        print(f"已读取：{file}（{len(df)} 行）")
    except Exception as e:
        print(f"读取 {file} 失败：{str(e)}")

# 合并数据
if dfs:
    merged_df = pd.concat(dfs, ignore_index=True)
    # 保存结果
    if output_file.endswith(".xlsx"):
        merged_df.to_excel(output_file, index=False)
    else:
        merged_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n合并完成！共 {len(merged_df)} 行数据，已保存至 {output_file}")
else:
    print("没有可合并的有效数据")