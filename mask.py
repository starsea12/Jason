import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features


def extract_basin_boundary(pfbas_code, shp_path, code_field="PFBAS_ID"):
    """
    从 Shapefile 中识别指定流域并输出其几何对象和原始边界。

    参数
    ----------
    pfbas_code : str or int
        目标流域的 PFBAS 编码。
    shp_path : str
        Shapefile 文件路径。
    code_field : str, optional
        Shapefile 中存储流域编码的字段名，默认为 "PFBAS"。

    返回
    -------
    dict
        包含以下键的字典：
        - 'geometry' : shapely.geometry.Polygon 或 MultiPolygon
        - 'bounds' : tuple (xmin, ymin, xmax, ymax)  原始坐标系下的边界
        - 'crs' : pyproj.CRS 或 rasterio.crs.CRS  原始坐标系
    """
    gdf = gpd.read_file(shp_path)
    basin = gdf[gdf[code_field] == pfbas_code]
    if basin.empty:
        raise ValueError(f"未找到编码为 {pfbas_code} 的流域，请检查字段名 '{code_field}' 或编码值。")

    if len(basin) > 1:
        geom = basin.geometry.unary_union
    else:
        geom = basin.geometry.iloc[0]

    bounds = geom.bounds
    return {
        "geometry": geom,
        "bounds": bounds,
        "crs": gdf.crs,
    }


def mask_and_crop_tif(tif_path, basin_info, output_tif_path, expand=1):
    """
    根据流域几何，从 TIF 文件中裁剪出流域的最小外接矩形（向外扩展 expand 像素），
    生成掩膜栅格：流域内部为 1，外部为 0。

    参数
    ----------
    tif_path : str
        输入 TIF 文件路径。
    basin_info : dict
        extract_basin_boundary 函数返回的字典。
    output_tif_path : str
        输出掩膜 TIF 文件路径。
    expand : int, optional
        向外扩展的像素数，默认为 1（上下左右各扩展一格）。
    """
    geom_orig = basin_info["geometry"]
    orig_crs = basin_info["crs"]

    with rasterio.open(tif_path) as src:
        # 将流域几何转换到 TIF 的投影坐标系
        gdf_geom = gpd.GeoDataFrame(geometry=[geom_orig], crs=orig_crs)
        geom_proj = gdf_geom.to_crs(src.crs).geometry.iloc[0]

        xmin, ymin, xmax, ymax = geom_proj.bounds
        transform = src.transform
        pixel_width = abs(transform.a)
        pixel_height = abs(transform.e)

        new_xmin = xmin - expand * pixel_width
        new_xmax = xmax + expand * pixel_width
        new_ymin = ymin - expand * pixel_height
        new_ymax = ymax + expand * pixel_height

        width = int(round((new_xmax - new_xmin) / pixel_width))
        height = int(round((new_ymax - new_ymin) / pixel_height))

        out_transform = rasterio.Affine(
            pixel_width, 0.0, new_xmin,
            0.0, -pixel_height, new_ymax
        )

        # 生成掩膜：多边形内部 = True，外部 = False
        mask_in = features.geometry_mask(
            [geom_proj],
            out_shape=(height, width),
            transform=out_transform,
            invert=False,      # 内部为 True
            all_touched=False,
        )
        # 反转：内部变为 1，外部变为 0
        mask_uint8 = np.where(mask_in, 0, 1).astype(np.uint8)

        profile = src.profile
        profile.update({
            "driver": "GTiff",
            "height": height,
            "width": width,
            "transform": out_transform,
            "dtype": rasterio.uint8,
            "count": 1,
            "compress": "lzw",
            "nodata": None,      # 避免原 nodata=65535 与 uint8 冲突
        })

        with rasterio.open(output_tif_path, "w", **profile) as dst:
            dst.write(mask_uint8, 1)

    print(f"掩膜栅格已生成：{output_tif_path}")


# 示例用法
if __name__ == "__main__":
    # 用户需修改以下参数
    shp_file = "PFBAS8.shp"
    tif_file = "PFBAS8.tif"
    pfbas = "01010105000000"
    output_mask = "masknew01.tif"
    expand_pixels = 1
    code_field = "PFBAS_ID"   # 根据实际字段名修改

    basin_info = extract_basin_boundary(pfbas, shp_file, code_field=code_field)
    print("原始边界 (xmin, ymin, xmax, ymax):", basin_info["bounds"])

    mask_and_crop_tif(tif_file, basin_info, output_mask, expand=expand_pixels)
