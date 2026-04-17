import rasterio
import numpy as np
from rasterio.windows import Window

def extract_watershed_bbox_with_mask(tif_path, pfbas_code, output_tif_path, nodata=255):
    """
    提取指定流域的最小外接矩形（向外扩展一格），输出二值掩膜：
    1 = 原流域，0 = 矩形内其他区域。

    Parameters
    ----------
    tif_path : str
        输入的 TIFF 文件路径（包含流域编码）。
    pfbas_code : int or float
        目标流域的 PFBAS 编码。
    output_tif_path : str
        输出的 TIFF 文件路径。
    nodata : int, optional
        输出文件的无效值，默认 255（适合 uint8）。
    """
    with rasterio.open(tif_path) as src:
        # 读取整个栅格（假设内存足够）
        data = src.read(1)
        height, width = data.shape

        # 定位目标流域像元
        rows, cols = np.where(data == pfbas_code)
        if len(rows) == 0:
            raise ValueError(f"PFBAS 编码 {pfbas_code} 不存在于输入文件中。")

        # 最小外接矩形行列范围
        min_row, max_row = rows.min(), rows.max()
        min_col, max_col = cols.min(), cols.max()

        # 向外扩展一个像元，并限制边界
        min_row = max(0, min_row - 1)
        max_row = min(height - 1, max_row + 1)
        min_col = max(0, min_col - 1)
        max_col = min(width - 1, max_col + 1)

        # 定义窗口
        window = Window(col_off=min_col, row_off=min_row,
                        width=max_col - min_col + 1,
                        height=max_row - min_row + 1)

        # 读取窗口内的原始数据
        window_data = src.read(1, window=window)

        # 创建输出数组：全 0，然后将等于目标编码的位置设为 1
        out_data = np.zeros(window_data.shape, dtype=np.uint8)
        out_data[window_data == pfbas_code] = 1

        # 计算新的地理变换
        new_transform = rasterio.windows.transform(window, src.transform)

        # 准备输出元数据
        out_meta = src.meta.copy()
        out_meta.update({
            'driver': 'GTiff',
            'height': window.height,
            'width': window.width,
            'dtype': 'uint8',
            'transform': new_transform,
            'nodata': nodata,
            'compress': 'lzw'   # 可选，减少文件体积
        })

        # 写入新文件
        with rasterio.open(output_tif_path, 'w', **out_meta) as dst:
            dst.write(out_data, 1)

    print(f"成功输出流域 {pfbas_code} 的二值掩膜矩形至：{output_tif_path}")

# 示例用法
if __name__ == "__main__":
    extract_watershed_bbox_with_mask("PFBAS8.tif", pfbas_code=1215, output_tif_path="output_mask.tif")
with rasterio.open("output_mask.tif") as src:
    arr = src.read(1)
    print(np.unique(arr))
