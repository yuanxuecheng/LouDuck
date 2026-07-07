"""验证 numpy.linalg.inv 的 monkey-patch 是否正确工作"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np

# 导入 ear_renderer 会触发 monkey-patch
from renderers import ear_renderer


def test_inv_patch():
    # 非 C-contiguous 的 3x3 矩阵
    positions = np.array([[1.0, 0.0, 0.0],
                          [0.0, 1.0, 0.0],
                          [0.0, 0.0, 1.0]], dtype=np.float64, order='F')
    assert not positions.flags.c_contiguous

    inv = np.linalg.inv(positions)
    expected = np.eye(3)
    assert np.allclose(inv, expected), f"求逆结果错误: {inv}"
    print("[OK] monkey-patch 后的 np.linalg.inv 可正确处理非 C-contiguous 矩阵")


if __name__ == "__main__":
    test_inv_patch()
