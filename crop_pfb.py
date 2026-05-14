#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
根据掩膜和位置信息裁剪 PFB（正确版，支持命令行参数）
"""

import numpy as np
import rasterio
from parflow.tools.io import read_pfb, write_pfb
import json
import argparse

def main():
    parser = argparse.ArgumentParser(description="裁剪 PFB")
    parser.add_argument("--pfb", required=True, help="原始全国 PFB 文件（南→北）")
    parser.add_argument("--mask", required=True, help="掩膜 TIF 文件（北→南，内1外0）")
    parser.add_argument("--pos_json", required=True, help="位置信息 JSON 文件")
    parser.add_argument("--out_pfb", required=True, help="输出裁剪后的 PFB 文件（南→北）")
    args = parser.parse_args()

    # 1. 读取位置信息
    with open(args.pos_json, 'r') as f:
        pos = json.load(f)
    row_min = pos["row_min"]
    col_min = pos["col_min"]
    height = pos["height"]
    width = pos["width"]
    print(f"位置: row_min={row_min}, col_min={col_min}, height={height}, width={width}")

    # 2. 读取掩膜（北→南）并翻转方向为南→北
    with rasterio.open(args.mask) as src:
        mask = src.read(1).astype(np.uint8)
    mask = (mask > 0).astype(np.uint8)
    mask_flipped = np.flip(mask, axis=0)        # 现在南→北

    # 3. 读取原始 PFB（南→北）
    pfb = read_pfb(args.pfb)
    z, ny, nx = pfb.shape
    print(f"原始 PFB 形状: {pfb.shape}")

    # 4. 计算在原始 PFB 中对应的行范围（南→北）
    #    掩膜矩形在北→南坐标系中从 row_min 开始（靠近北），对应南→北坐标系中的行索引：
    orig_row_start = ny - row_min - height
    orig_row_end = ny - row_min
    if orig_row_start < 0 or orig_row_end > ny:
        raise ValueError(f"计算的行范围 [{orig_row_start}, {orig_row_end}) 超出 PFB 行范围 [0, {ny})")
    print(f"在原始 PFB 中提取的行范围: [{orig_row_start}, {orig_row_end})")

    # 5. 提取子区域（南→北）
    pfb_sub = pfb[:, orig_row_start:orig_row_end, col_min:col_min+width]
    print(f"提取子区域形状: {pfb_sub.shape}")

    # 6. 应用掩膜（掩膜已翻转，方向一致）
    mask_3d = mask_flipped[np.newaxis, :, :]   # (1, H, W)
    pfb_masked = pfb_sub * mask_3d

    # 7. 保存结果
    write_pfb(args.out_pfb, pfb_masked)
    print(f"裁剪完成，输出文件: {args.out_pfb}")

if __name__ == "__main__":
    main()