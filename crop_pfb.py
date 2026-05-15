#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
程序二：利用掩膜 TIF 和位置信息裁剪全国 PFB
输入：
    - 全国 PFB 文件（3D，方向从南到北）
    - 掩膜 TIF 文件（内1外0）
    - 位置 JSON 文件（由程序一生成）
    - 输出 PFB 路径
输出：
    - 裁剪后的 PFB（子区域，方向从南到北）
"""

import numpy as np
import rasterio
from parflow.tools.io import read_pfb, write_pfb
import json
import argparse

def main():
    parser = argparse.ArgumentParser(description="利用掩膜和位置信息裁剪 PFB")
    parser.add_argument("--pfb", required=True, help="输入全国 PFB 文件")
    parser.add_argument("--mask", required=True, help="掩膜 TIF 文件")
    parser.add_argument("--pos_json", required=True, help="位置 JSON 文件（由程序一生成）")
    parser.add_argument("--out_pfb", required=True, help="输出裁剪后的 PFB 文件")
    args = parser.parse_args()

    # 1. 读取位置信息
    with open(args.pos_json, "r") as f:
        pos = json.load(f)
    row_min = pos["row_min"]
    col_min = pos["col_min"]
    height = pos["height"]
    width = pos["width"]
    print(f"[程序二] 位置信息: 起始行={row_min}, 起始列={col_min}, 尺寸={height}x{width}")

    # 2. 读取掩膜数值（可选校验）
    with rasterio.open(args.mask) as src:
        mask = src.read(1)
        mask = (mask > 0).astype(np.uint8)
    if mask.shape != (height, width):
        print(f"[程序二] 警告：掩膜实际尺寸 {mask.shape} 与 JSON 记录不一致，将以掩膜为准")
        height, width = mask.shape

    # 3. 读取 PFB
    print(f"[程序二] 读取 PFB: {args.pfb}")
    pfb = read_pfb(args.pfb)      # (Z, Y_nat, X_nat), Y 从南到北
    z, ny, nx = pfb.shape
    print(f"[程序二] PFB 原始形状: {pfb.shape}")

    # 4. 翻转 PFB 使 Y 方向与掩膜一致（掩膜 Y 从北到南）
    pfb_flipped = np.flip(pfb, axis=1)   # 现在 Y 从北到南

    # 5. 裁剪矩形区域
    if row_min + height > pfb_flipped.shape[1] or col_min + width > pfb_flipped.shape[2]:
        raise ValueError("裁剪区域超出 PFB 范围，请检查位置信息")
    pfb_cropped = pfb_flipped[:, row_min:row_min+height, col_min:col_min+width]
    print(f"[程序二] 裁剪后子区域形状: {pfb_cropped.shape}")

    # 6. 应用掩膜：流域外置 0
    mask_3d = mask[np.newaxis, :, :]   # (1, H, W)
    pfb_masked = pfb_cropped * mask_3d

    # 7. 翻转回原始方向（南到北）
    pfb_result = np.flip(pfb_masked, axis=1)

    # 8. 保存结果
    write_pfb(args.out_pfb, pfb_result)
    print(f"[程序二] 裁剪后 PFB 已保存: {args.out_pfb}")
    print(f"[程序二] 输出形状: {pfb_result.shape}")
    print(f"[程序二] 非零像素数（流域内）: {np.sum(pfb_result != 0)}")

if __name__ == "__main__":
    main()
