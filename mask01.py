# 导入 rasterio 库，用于读写栅格数据（如 GeoTIFF 文件）
import rasterio
# 导入 numpy 库，用于数组操作和数值计算
import numpy as np
# 从 rasterio.windows 模块中导入 Window 类，用于定义裁剪窗口
from rasterio.windows import Window

# 定义函数：提取指定流域的最小外接矩形（向外扩展一格），输出二值掩膜 TIFF 文件
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
    # 使用 with 语句打开输入 TIFF 文件，确保文件正确关闭
    with rasterio.open(tif_path) as src:
        # 读取整个栅格的第一波段数据（二维数组）
        # 假设内存足够，若文件巨大可分块处理，但此处简化
        data = src.read(1)
        # 获取栅格的行数（高度）和列数（宽度）
        height, width = data.shape

        # 查找所有等于目标 pfbas_code 的像元位置，返回行索引列表和列索引列表
        rows, cols = np.where(data == pfbas_code)
        # 如果没有找到任何匹配像元，抛出异常并提示编码不存在
        if len(rows) == 0:
            raise ValueError(f"PFBAS 编码 {pfbas_code} 不存在于输入文件中。")

        # 计算匹配像元的最小行号、最大行号、最小列号、最大列号（即外接矩形边界）
        min_row, max_row = rows.min(), rows.max()
        min_col, max_col = cols.min(), cols.max()

        # 向外扩展一个像元，并确保不超出原始数据边界
        min_row = max(0, min_row - 1)               # 上边界减1，不能小于0
        max_row = min(height - 1, max_row + 1)      # 下边界加1，不能超过最大行索引
        min_col = max(0, min_col - 1)               # 左边界减1，不能小于0
        max_col = min(width - 1, max_col + 1)       # 右边界加1，不能超过最大列索引

        # 基于扩展后的行列范围创建 Window 对象，用于裁剪
        window = Window(col_off=min_col, row_off=min_row,
                        width=max_col - min_col + 1,
                        height=max_row - min_row + 1)

        # 使用上面定义的窗口，从源文件中读取该窗口内的原始数据（第一波段）
        window_data = src.read(1, window=window)

        # 创建一个与窗口数据形状相同、数据类型为 uint8 的数组，初始全为 0
        out_data = np.zeros(window_data.shape, dtype=np.uint8)
        # 将窗口中等于目标编码的像元在输出数组中设为 1，其余保持 0
        out_data[window_data == pfbas_code] = 1

        # 根据原始地理变换和窗口偏移量，计算裁剪后栅格的新地理变换（仿射变换）
        new_transform = rasterio.windows.transform(window, src.transform)

        # 复制源文件的元数据（如坐标系、数据类型等）
        out_meta = src.meta.copy()
        # 更新输出文件的元数据，适配二值掩膜输出
        out_meta.update({
            'driver': 'GTiff',           # 输出格式为 GeoTIFF
            'height': window.height,     # 输出图像高度（窗口高度）
            'width': window.width,       # 输出图像宽度（窗口宽度）
            'dtype': 'uint8',            # 输出数据类型为无符号8位整型
            'transform': new_transform,  # 使用新计算的地理变换
            'nodata': nodata,            # 设置无数据值（默认为255）
            'compress': 'lzw'            # 使用 LZW 压缩减少文件体积
        })

        # 以写入模式打开输出 TIFF 文件，使用更新后的元数据
        with rasterio.open(output_tif_path, 'w', **out_meta) as dst:
            # 将 out_data 写入输出文件的第一个波段
            dst.write(out_data, 1)

    # 函数执行完毕，打印成功信息，包含输出文件路径
    print(f"成功输出流域 {pfbas_code} 的二值掩膜矩形至：{output_tif_path}")

# 以下代码块仅在直接运行该脚本时执行（而非作为模块导入时执行）
if __name__ == "__main__":
    # 调用函数，处理 "PFBAS8.tif" 文件，提取编码为 1215 的流域，输出为 "output_mask.tif"
    extract_watershed_bbox_with_mask("PFBAS8.tif", pfbas_code=1215, output_tif_path="output_mask.tif")
    # 打开刚生成的输出文件，验证其内容
    with rasterio.open("output_mask.tif") as src:
        # 读取输出文件的第一波段数据
        arr = src.read(1)
        # 打印数组中所有唯一值，检查是否仅为 0、1 或 255 等
        print(np.unique(arr))
