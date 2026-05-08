# 流域掩膜生成工具

根据流域 Shapefile 和 PFBAS 编码，从任意 GeoTIFF 文件中裁剪出流域的最小外接矩形（可向外扩展若干像素），生成二值掩膜栅格：**流域内为 1，流域外为 0**（可通过参数快速修改为其他值）。

## 功能特点

- 自动读取 Shapefile，根据字段值（如 `PFBAS`）定位目标流域
- 支持流域几何为 `Polygon` 或 `MultiPolygon`，自动合并同一编码的多要素
- 将与 TIF 文件坐标系自动对齐（重投影）
- 计算流域的最小外接矩形，并支持向外扩展指定像素数（上下左右各 `expand` 格）
- 输出单波段 GeoTIFF 掩膜，压缩（LZW）保存
- 默认生成 **流域内 = 1，流域外 = 0** 的 `uint8` 栅格（可灵活修改）

## 依赖库

- Python ≥ 3.7
- `geopandas`
- `rasterio`
- `numpy`
- `shapely`

安装命令（推荐使用 conda）：

```bash
conda install geopandas rasterio numpy shapely
```

# 或

```
pip install geopandas rasterio numpy shapely
```

## 函数说明

### 1. `extract_basin_boundary`

从 Shapefile 中提取指定流域的几何对象、原始边界和坐标系。

**参数：**

| 参数  | 类型  | 说明  |
| --- | --- | --- |
| `pfbas_code` | str/int | 目标流域的编码（例如 `"123456"`） |
| `shp_path` | str | Shapefile 文件路径 |
| `code_field` | str | 存储流域编码的字段名，默认为 `"PFBAS"` |

**返回：**

```python
{
    "geometry": shapely.geometry.Polygon or MultiPolygon,  # 流域几何
    "bounds": (xmin, ymin, xmax, ymax),                    # 原始边界
    "crs": pyproj.CRS or rasterio.crs.CRS                  # 坐标系
}
```

### 2. `mask_and_crop_tif`

根据流域几何，从 TIF 文件中裁剪扩展后的最小外接矩形，生成掩膜栅格。

**参数：**

| 参数  | 类型  | 说明  |
| --- | --- | --- |
| `tif_path` | str | 输入 GeoTIFF 文件路径（作为模板） |
| `basin_info` | dict | `extract_basin_boundary` 返回的字典 |
| `output_tif_path` | str | 输出掩膜 TIFF 路径 |
| `expand` | int | 向外扩展的像素数，默认为 1（上下左右各扩展一格） |

**掩膜赋值逻辑（默认）：**

- 流域内部像素值 = **1**
- 流域外部像素值 = **0**


## 使用示例

```python
from mask_generator import extract_basin_boundary, mask_and_crop_tif

# 1. 配置路径和编码
shp_file = "PFBAS8.shp"
tif_file = "PFBAS8.tif"
pfbas = "01010105000000"
output_mask = "mask.tif"

# 2. 获取流域信息
basin_info = extract_basin_boundary(target_code, shp_file, code_field="PFBAS_ID")
print("原始边界:", basin_info["bounds"])

# 3. 生成掩膜（向外扩展 1 像素）
mask_and_crop_tif(tif_file, basin_info, output_mask, expand=1)
```

运行后，`mask.tif` 即为所需栅格：流域内值为 1，流域外值为 0。

## 注意事项

1. **坐标系兼容性**：Shapefile 和 TIF 文件应具有可转换的坐标参考系（CRS）。函数内部会自动将流域几何投影到 TIF 的 CRS。
2. **字段名**：请确保 `code_field` 参数与 Shapefile 中存储编码的字段名完全一致（大小写敏感）。
3. **扩展像素**：`expand` 参数定义的是向外扩展的**像素个数**，而不是地理距离。最终输出矩形的边界会基于 TIF 的分辨率计算。
4. **NoData 处理**：输出掩膜不保留原 TIF 的 NoData 值（自动设为 `None`），避免因原 NoData 值（如 `65535`）与 `uint8` 类型冲突导致写入失败。
5. **输出数据类型**：`uint8`，范围 0-255。若需其他数值（如 255），可在生成后使用 `np.where` 自行转换。

## 输出结果验证

使用以下代码快速检查生成的掩膜是否符合预期：

```python
import rasterio
import numpy as np

with rasterio.open("流域掩膜.tif") as src:
    mask = src.read(1)
    print("唯一值:", np.unique(mask))
    print("流域内像素数:", np.sum(mask == 1))
    print("流域外像素数:", np.sum(mask == 0))
```

期望输出：

```
唯一值: [0 1]
流域内像素数: xxx
流域外像素数: xxx
```

## 常见问题

**Q：为什么输出的掩膜全是 0？**  
A：检查流域几何与 TIF 的范围是否有重叠。可能是坐标系不一致导致几何投影后完全落在 TIF 范围之外。可打印 `basin_info["bounds"]` 和 TIF 的边界进行对比。

**Q：如何修改流域内数值为 255？**  
A：在 `mask_and_crop_tif` 函数中找到：

```python
mask_uint8 = np.where(mask_in, 1, 0).astype(np.uint8)
```

改为：

```python
mask_uint8 = np.where(mask_in, 255, 0).astype(np.uint8)
```

**Q：扩展像素后矩形超出了 TIF 范围会怎样？**  
A：代码以扩展后的边界计算输出尺寸，并基于 TIF 的仿射变换生成新的栅格。若扩展后矩形超出原始 TIF 范围，输出的掩膜会包含原始 TIF 外的区域，这些区域将根据掩膜生成规则赋值为 0（外部）。
