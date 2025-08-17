#!/usr/bin/env python3
from typing import List, Optional, Tuple

import cv2
import numpy as np
import zxingcpp

from .logger import get_logger

ZXING_AVAILABLE = True


def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img


def gen_variants(img: np.ndarray) -> List[np.ndarray]:
    """生成一组预处理变体，提升解码成功率。"""
    variants = []

    # 原图
    variants.append(img)

    # 灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    variants.append(gray)

    # 提高对比度
    gray_high = cv2.convertScaleAbs(gray, alpha=1.6, beta=0)
    variants.append(gray_high)

    # 中值滤波（去噪点）
    med = cv2.medianBlur(gray_high, 3)
    variants.append(med)

    # 高斯模糊 + OTSU 二值化
    gauss = cv2.GaussianBlur(gray_high, (3, 3), 0)
    _, otsu = cv2.threshold(gauss, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(otsu)

    # 自适应阈值（二值化）
    adap = cv2.adaptiveThreshold(gray_high, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 25, 2)
    variants.append(adap)

    # 形态学闭运算（填补细小断裂）
    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel, iterations=1)
    variants.append(closed)

    return variants


def try_decode_zxing(img: np.ndarray) -> Optional[str]:
    if not ZXING_AVAILABLE:
        return None
    try:
        # zxingcpp 支持 numpy 图像（BGR/Gray），返回可能多码
        results = zxingcpp.read_barcodes(img)
        for r in results:
            txt = (r.text or "").strip()
            if txt:
                return txt
    except Exception:
        pass
    return None


def try_decode_opencv(img: np.ndarray) -> Optional[str]:
    try:
        det = cv2.QRCodeDetector()
        # 先试单码
        data, _, _ = det.detectAndDecode(img)
        if data:
            return data.strip()
        # 再试多码
        success, datas, _, _ = det.detectAndDecodeMulti(img)
        if success and isinstance(datas, (list, tuple)):
            for d in datas:
                if d:
                    return d.strip()
    except Exception:
        pass
    return None


def decode_qr_with_fallback(img: np.ndarray) -> Tuple[Optional[str], str]:
    """返回 (内容, 使用的解码器标识)。"""
    # 生成多种预处理版本
    variants = gen_variants(img)

    # 优先 zxing
    if ZXING_AVAILABLE:
        for v in variants:
            r = try_decode_zxing(v)
            if r:
                return r, "zxing-cpp"

    # 退回 OpenCV
    for v in variants:
        r = try_decode_opencv(v)
        if r:
            return r, "opencv"

    return None, ""


def print_ascii_qr(text: str):
    logger = get_logger(__name__)
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)  # 边框小一些，方便在终端放大显示
        qr.add_data(text)
        qr.make(fit=True)
        # 反相打印，提升终端显示对比度（部分终端/主题需要关闭 invert）
        qr.print_ascii(invert=True)
        logger.info("用手机对准终端二维码扫描即可")
    except Exception as e:
        logger.warning(f"ASCII QR render failed: {e}")


def display_qr_code(qr_image_path: str):
    logger = get_logger(__name__)
    img = load_image(qr_image_path)
    content, _ = decode_qr_with_fallback(img)
    if content:
        print_ascii_qr(content)
    else:
        logger.error(f"无法解码二维码图片: {qr_image_path}")
