#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动运行程序一（生成掩膜）和程序二（裁剪PFB）
"""

import subprocess
import sys
import os

# ==================== 用户配置（请根据实际情况修改）====================
# 程序一脚本路径（可绝对路径或相对路径）
GEN_SCRIPT = r"C:\Users\Jason\Desktop\parflow\code\generate_mask.py"

# 程序一所需参数
SHP_PATH = r"C:\Users\Jason\Desktop\parflow\data\PFBAS8.shp"    # Shapefile 路径
PFBAS_CODE = "01010105000000"                           # 流域编码
FIELD_NAME = "PFBAS_ID"                            # 编码字段名
TIF_TEMPLATE = r"C:\Users\Jason\Desktop\parflow\data\PFBAS8.tif"   # 模板 TIF（与PFB对齐）
OUT_MASK = r"C:\Users\Jason\Desktop\parflow\data\masknew01.tif"           # 输出掩膜 TIF
OUT_JSON = r"C:\Users\Jason\Desktop\parflow\data\pos.json"                # 输出位置 JSON
EXPAND = 1                                      # 扩展像素数

# 程序二脚本路径
CROP_SCRIPT = r"C:\Users\Jason\Desktop\parflow\code\crop_pfb.py"

# 程序二所需参数
PFB_INPUT = r"C:\Users\Jason\Desktop\parflow\data\CHN.slopex.2026.fix.pfb"  # 输入全国 PFB
OUT_PFB = r"C:\Users\Jason\Desktop\parflow\data\result.pfb"               # 输出裁剪后 PFB
# ====================================================================

def run_command(cmd, description):
    """执行命令，若失败则退出"""
    print(f"\n>>> {description}")
    print(f">>> 命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=False)
    if result.returncode != 0:
        print(f"错误：{description} 失败，返回码 {result.returncode}")
        sys.exit(result.returncode)
    print(f"完成：{description}\n")

def main():
    # 检查脚本是否存在
    if not os.path.exists(GEN_SCRIPT):
        print(f"错误：找不到程序一脚本 {GEN_SCRIPT}")
        sys.exit(1)
    if not os.path.exists(CROP_SCRIPT):
        print(f"错误：找不到程序二脚本 {CROP_SCRIPT}")
        sys.exit(1)

    # 1. 运行程序一：生成掩膜和位置信息
    cmd_gen = [
        sys.executable, GEN_SCRIPT,
        "--shp", SHP_PATH,
        "--code", PFBAS_CODE,
        "--field", FIELD_NAME,
        "--tif", TIF_TEMPLATE,
        "--out_mask", OUT_MASK,
        "--out_json", OUT_JSON,
        "--expand", str(EXPAND)
    ]
    run_command(cmd_gen, "程序一：生成掩膜和位置信息")

    # 2. 运行程序二：裁剪 PFB
    cmd_crop = [
        sys.executable, CROP_SCRIPT,
        "--pfb", PFB_INPUT,
        "--mask", OUT_MASK,
        "--pos_json", OUT_JSON,
        "--out_pfb", OUT_PFB
    ]
    run_command(cmd_crop, "程序二：裁剪 PFB")

    print("\n=== 全部完成 ===")
    print(f"掩膜文件: {OUT_MASK}")
    print(f"位置文件: {OUT_JSON}")
    print(f"裁剪结果: {OUT_PFB}")

if __name__ == "__main__":
    main()