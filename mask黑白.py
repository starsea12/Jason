import rasterio
import numpy as np
from rasterio.windows import Window


def extract_watershed_bbox_with_mask(tif_path, pfbas_code, output_tif_path):
    """
    提取指定流域的最小外接矩形（四周扩展1格）
    输出：
        流域像元 = 255
        其他像元 = 0
    """

    with rasterio.open(tif_path) as src:
        data = src.read(1)
        height, width = data.shape

        rows, cols = np.where(data == pfbas_code)

        if len(rows) == 0:
            raise ValueError(f"PFBAS 编码 {pfbas_code} 不存在")

        min_row = max(0, rows.min() - 1)
        max_row = min(height - 1, rows.max() + 1)
        min_col = max(0, cols.min() - 1)
        max_col = min(width - 1, cols.max() + 1)

        window = Window(
            col_off=min_col,
            row_off=min_row,
            width=max_col - min_col + 1,
            height=max_row - min_row + 1
        )

        window_data = src.read(1, window=window)

        out_data = np.zeros(window_data.shape, dtype=np.uint8)

        # 为了显示明显，赋值255
        out_data[window_data == pfbas_code] = 255

        new_transform = rasterio.windows.transform(window, src.transform)

        meta = src.meta.copy()
        meta.update({
            "driver": "GTiff",
            "height": out_data.shape[0],
            "width": out_data.shape[1],
            "count": 1,
            "dtype": "uint8",
            "transform": new_transform,
            "nodata": 0,
            "compress": "lzw"
        })

        with rasterio.open(output_tif_path, "w", **meta) as dst:
            dst.write(out_data, 1)

    print(f"已输出: {output_tif_path}")
if __name__ == "__main__":
    extract_watershed_bbox_with_mask("PFBAS8.tif", pfbas_code=1215, output_tif_path="output_mask.tif")