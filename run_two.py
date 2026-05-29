#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动运行程序一（生成掩膜）和程序二（裁剪PFB）
根据 PFBASID 自动识别对应的 PFBASn.shp 和 PFBASn.tif 文件
直接调用函数，无需 subprocess
支持裁剪多个 PFB 文件，输出文件名自动为“核心名称.流域编号.pfb”
裁剪完成后，对每个输出的 PFB 执行 pfmask-to-pfsol 生成 VTK 和 PFSOL 文件
对于 3D 的 PFB（Z>1），自动提取第一层生成临时 2D 文件进行转换
"""

import os
import sys
import subprocess
import tempfile

# 添加代码目录到 Python 路径
CODE_DIR = "/data/wangzihan-data/code"
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from generate_mask import generate_mask
from crop_pfb import crop_pfb
from parflow.tools.io import read_pfb, write_pfb

# ==================== 用户配置 ====================
INPUT_SHP_DIR = "/data/wangzihan-data/inputs"
INPUT_PFB_DIR = "/data/share/parflow-group/CONCN1.1/inputs"
OUTPUT_DIR = "/data/wangzihan-data/outputs"
FIELD_NAME = "PFBAS_ID"
OUT_MASK = os.path.join(OUTPUT_DIR, "mask.tif")
OUT_JSON = os.path.join(OUTPUT_DIR, "pos.json")
EXPAND = 1
PFMASK_CMD = "/data/software/parflow-gnu13/parflow-3.13.0/bin/pfmask-to-pfsol"
BOTTOM_PATCH_LABEL = 2
SIDE_PATCH_LABEL = 3
Z_TOP = 2000.0
Z_BOTTOM = 0.0

PFB_INPUTS = [
    "CHN.slopex.2026.fix.pfb",
    "CHN.slopey.2026.fix.pfb",
    "Shangguan_300m_FBZ_fix.pfb",
    "CONCN_manning.fix.2026.pfb",
    "GLHYMPS1.0_multi_efold_fix.pfb"
]
# ====================================================


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def get_output_filename(input_filename, basin_code):
    mapping = {
        "CHN.slopex.2026.fix.pfb": "slopex",
        "CHN.slopey.2026.fix.pfb": "slopey",
        "Shangguan_300m_FBZ_fix.pfb": "Shangguan",
        "CONCN_manning.fix.2026.pfb": "CONCN_manning",
        "GLHYMPS1.0_multi_efold_fix.pfb": "GLHYMPS1.0"
    }
    base_name = os.path.basename(input_filename)
    if base_name not in mapping:
        raise ValueError(f"未定义输出映射规则的文件: {base_name}")
    core_name = mapping[base_name]
    return f"{core_name}.{basin_code}.pfb"


def get_pfbas_level(pfbas_code):
    code_stripped = pfbas_code.rstrip('0')
    if not code_stripped:
        return 2
    level = len(code_stripped)
    if level % 2 != 0:
        level += 1
    if level < 2:
        level = 2
    if level > 14:
        level = 14
    return level


def run_pfmask_to_pfsol(mask_pfb_path, output_prefix, output_dir):
    """
    对 PFB 文件执行 pfmask-to-pfsol。
    如果 PFB 是 3D（Z>1），则自动提取第一层生成临时 2D 文件进行处理。
    """
    # 读取 PFB 检查维度
    data = read_pfb(mask_pfb_path)
    original_shape = data.shape
    if len(original_shape) != 3:
        raise ValueError(f"PFB 不是三维数组: {original_shape}")

    nz, ny, nx = original_shape
    use_temp = False
    temp_pfb_path = mask_pfb_path

    if nz != 1:
        print(f"  检测到 PFB 为 3D（Z={nz}），提取第一层生成临时 2D 文件...")
        # 提取第一层（保持三维形状 (1, ny, nx)）
        data_2d = data[0:1, :, :]   # shape (1, ny, nx)
        # 创建临时文件
        fd, temp_pfb_path = tempfile.mkstemp(suffix=".pfb", dir=output_dir)
        os.close(fd)
        write_pfb(temp_pfb_path, data_2d)
        use_temp = True
        print(f"  临时文件: {temp_pfb_path}")

    vtk_path = os.path.join(output_dir, f"{output_prefix}.vtk")
    pfsol_path = os.path.join(output_dir, f"{output_prefix}.pfsol")

    cmd = [
        PFMASK_CMD,
        "--mask", temp_pfb_path,
        "--vtk", vtk_path,
        "--pfsol", pfsol_path,
        "--bottom-patch-label", str(BOTTOM_PATCH_LABEL),
        "--side-patch-label", str(SIDE_PATCH_LABEL),
        "--z-top", str(Z_TOP),
        "--z-bottom", str(Z_BOTTOM)
    ]

    print(f"  执行命令: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, cwd=output_dir,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True)
        print(f"  成功生成: {vtk_path}\n            {pfsol_path}")
    except subprocess.CalledProcessError as e:
        print(f"  错误：命令执行失败，返回码 {e.returncode}")
        print(f"  错误输出: {e.stderr}")
        raise
    except FileNotFoundError:
        print(f"  错误：找不到命令 '{PFMASK_CMD}'，请检查路径")
        raise
    finally:
        if use_temp and os.path.exists(temp_pfb_path):
            os.remove(temp_pfb_path)
            print(f"  已删除临时文件: {temp_pfb_path}")


def main():
    ensure_dir(OUTPUT_DIR)

    pfbas_code = input("请输入14位流域编码（如01010500001000）: ").strip()
    if len(pfbas_code) != 14 or not pfbas_code.isdigit():
        print("错误：编码应为14位数字")
        sys.exit(1)

    level = get_pfbas_level(pfbas_code)
    print(f"[信息] 流域编码: {pfbas_code}")
    print(f"[信息] 识别到使用前 {level} 位 -> 对应文件: PFBAS{level}.shp 和 PFBAS{level}.tif")

    shp_path = os.path.join(INPUT_SHP_DIR, f"PFBAS{level}.shp")
    tif_template = os.path.join(INPUT_SHP_DIR, f"PFBAS{level}.tif")

    if not os.path.exists(shp_path):
        print(f"错误：找不到 Shapefile 文件 {shp_path}")
        sys.exit(1)
    if not os.path.exists(tif_template):
        print(f"错误：找不到模板 TIF 文件 {tif_template}")
        sys.exit(1)

    # 程序一：生成掩膜
    print("\n>>> 程序一：生成掩膜和位置信息")
    generate_mask(
        shp_path=shp_path,
        code=pfbas_code,
        field=FIELD_NAME,
        tif_path=tif_template,
        out_mask_path=OUT_MASK,
        out_json_path=OUT_JSON,
        expand=EXPAND,
        verbose=True
    )

    # 程序二：裁剪 PFB
    output_pfb_info = []
    for input_file in PFB_INPUTS:
        input_path = os.path.join(INPUT_PFB_DIR, input_file)
        output_file = get_output_filename(input_path, pfbas_code)
        output_path = os.path.join(OUTPUT_DIR, output_file)
        output_prefix = output_file.replace(".pfb", "")

        print(f"\n>>> 程序二：裁剪 {input_file}")
        if not os.path.exists(input_path):
            print(f"警告：找不到输入文件 {input_path}，跳过")
            continue

        crop_pfb(
            pfb_path=input_path,
            mask_path=OUT_MASK,
            pos_json_path=OUT_JSON,
            out_pfb_path=output_path,
            verbose=True
        )
        output_pfb_info.append((output_path, output_prefix))

    # 程序三：生成 VTK 和 PFSOL
    print("\n>>> 程序三：生成 VTK 和 PFSOL 文件（调用 pfmask-to-pfsol）")
    for pfb_path, prefix in output_pfb_info:
        if not os.path.exists(pfb_path):
            print(f"警告：裁剪结果文件不存在 {pfb_path}，跳过")
            continue
        print(f"\n处理: {pfb_path}")
        run_pfmask_to_pfsol(pfb_path, prefix, OUTPUT_DIR)

    print("\n=== 全部完成 ===")
    print(f"掩膜文件: {OUT_MASK}")
    print(f"位置文件: {OUT_JSON}")
    for input_file in PFB_INPUTS:
        output_file = get_output_filename(os.path.join(INPUT_PFB_DIR, input_file), pfbas_code)
        print(f"{input_file} -> {output_file}")
    print(f"\n生成的 VTK 和 PFSOL 文件位于: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
