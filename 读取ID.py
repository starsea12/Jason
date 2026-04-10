import rasterio
from rasterio.mask import mask
import geopandas as gpd
import numpy as np


def get_pfaf_codes(basin_shp, pfaf_tif):
    # 读取流域边界
    basin = gpd.read_file(basin_shp)
    if basin.empty:
        raise ValueError("流域边界文件为空")

    with rasterio.open(pfaf_tif) as src:
        # 统一坐标系
        if basin.crs != src.crs:
            basin = basin.to_crs(src.crs)

        # 裁剪
        out_image, out_transform = mask(src, basin.geometry, crop=True)

        # 获取有效像元
        nodata = src.nodata
        pfaf_array = out_image[0]

        if nodata is not None:
            valid = pfaf_array[pfaf_array != nodata]
        else:
            # 如果没有 NoData 定义，则假设所有像元有效
            valid = pfaf_array.flatten()

        unique_codes = np.unique(valid)

        if len(unique_codes) == 0:
            print("警告：未找到有效 Pfafstetter 编码，请检查边界或数据。")
        elif len(unique_codes) == 1:
            print(f"流域 Pfafstetter 编码：{unique_codes[0]}")
        else:
            print(f"流域跨越多个 Pfafstetter 子流域：{unique_codes}")
        return unique_codes


if __name__ == "__main__":
    get_pfaf_codes("PFBAS14.shp", "PFBAS14.tif")