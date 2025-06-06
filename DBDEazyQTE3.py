import keyboard
import pyautogui
import time
import win32gui, win32ui, win32con
import threading
import numpy as np
from PIL import Image
import winsound
import math
import psutil
import mss
import ctypes
from ctypes import windll
from ctypes import wintypes, byref, sizeof
import cv2
import math
import os
import dxcam

# Press 3 : switch to repairing QTE
# Press 4 : switch to healing QTE
# Press 5 : switch to wiggle QTE
# Press 6 : switch on/off the Hyperfocus perk.

imgdir = 'DBDimg/'
delay_degree = 0
crop_w, crop_h = 200, 200
last_im_a = 0
region = [int((2560 - crop_w) / 2), int((1440 - crop_h) / 2),
          crop_w, crop_h]
toggle = True
keyboard_switch = True
frame_rate = 40 # 录屏帧数
repair_speed = 330
heal_speed = 300
wiggle_speed = 230
shot_delay = 0.00
press_and_release_delay = 0.003206
color_sensitive = 125
delay_pixel = 3
speed_now = repair_speed
hyperfocus = True
red_sensitive = 180
focus_level = 0
use_win32 = True

LOGPIXELSX = 88

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# 拿主屏的 DC
hdc = user32.GetDC(0)
dpi = gdi32.GetDeviceCaps(hdc, LOGPIXELSX)  # 例如 144 表示 150% 缩放
user32.ReleaseDC(0, hdc)

# 计算缩放因子
scale_factor = dpi / 96.0

# cam = dxcam.create(output_idx=0, output_color="RGB", max_buffer_len=2)
# cam.start(target_fps=120)

_sct = mss.mss()
# 开启高精度计时器，让 mss DXGI 路径延迟更稳
windll.winmm.timeBeginPeriod(1)

# —— 平台相关类型 ——
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(
    ctypes.c_ulonglong) else ctypes.c_ulong

# —— 常量 ——
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_SPACE = 0x20


# —— 把鼠标结构也一起定义进来 ——
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUTunion(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUTunion),
    ]


# —— 指定 SendInput 原型 ——
SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = wintypes.UINT


SIN_TABLE = [math.sin(math.radians(d)) for d in range(360)]
COS_TABLE = [math.cos(math.radians(d)) for d in range(360)]

def send_space():
    global use_win32
    if use_win32:
        # 构造两个 INPUT 结构：一个按下，一个抬起
        inp_down = INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.ki = KEYBDINPUT(wVk=VK_SPACE, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
        ret = SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
        if ret != 1:
            # 获取 Win32 错误码
            err = ctypes.GetLastError()
            print(f"[!] SendInput(key down) 返回 {ret}, 错误码 {err}，后续改用 pyautogui")
            use_win32 = False
            pyautogui.press('space')
            return

        # 抬起
        inp_up = INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.ki = KEYBDINPUT(wVk=VK_SPACE, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
        ret = SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
        if ret != 1:
            err = ctypes.GetLastError()
            print(f"[!] SendInput(key up) 返回 {ret}, 错误码 {err}，后续改用 pyautogui")
            use_win32 = False
            pyautogui.press('space')
    else:
        pyautogui.press('space')


def _test_win32_send():
    """
    返回 (ok: bool, err_code: int)；
    ok=True 时表示 SendInput 在按下和抬起都返回 1，ok=False 时 err_code 是 GetLastError()。
    """
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki = KEYBDINPUT(wVk=VK_SPACE, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
    if SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        return False, ctypes.GetLastError()
    inp.ki.dwFlags = KEYEVENTF_KEYUP
    if SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        return False, ctypes.GetLastError()
    return True, 0


def sleep(duration: float):
    """
    高精度等待 duration 秒（busy-wait）
    """
    end_ts = time.perf_counter() + duration
    while time.perf_counter() < end_ts:
        pass


def sleep_to(time_stamp):
    """
    等待到 perf_counter() 达到 target_ts（busy-wait）
    target_ts 应该是用 time.perf_counter() 计算的时间戳
    """
    while time.perf_counter() < time_stamp:
        pass


# def win_screenshot(startw: int, starth: int, w: int, h: int) -> np.ndarray:
#     """
#     直接用 mss.grab 按照绝对桌面坐标抓 region，
#     返回一个 (h, w, 3) 的 RGB ndarray，完全不做插值、不管 DPI。
#     """
#     # 构造一个字典给 mss.grab，用你算好的绝对坐标
#     region = {
#         "left":   startw,
#         "top":    starth-20,
#         "width":  w,
#         "height": h,
#     }
#     shot = _sct.grab(region)                           # BGRA
#     arr  = np.asarray(shot)[:, :, :3]                  # 取前 3 通道 BGR
#     return arr[:, :, ::-1]                             # BGR→RGB


def win_screenshot(_, __, ___, ____):
    img = cam.get_latest_frame()
    if img is None:
        # 如果实在没新帧，可以退而求其次返回最后一帧
        img = cam.get_latest_frame(video_mode=False)
        if img is None:
            raise RuntimeError("读不到帧了")
    return img


def find_red(im_array):
    """
    向量化版 find_red：
     1) 阈值 & 圆形掩码，一次性筛选所有红像素
     2) np.where 拿到坐标列表
     3) 调用原 find_thickest_point 计算最粗点
    """
    h, w, _ = im_array.shape
    # 1) 阈值判断
    r = im_array[:, :, 0]
    g = im_array[:, :, 1]
    b = im_array[:, :, 2]
    mask = (r > red_sensitive) & (g < 20) & (b < 20)
    if not mask.any():
        return None

    # 2) 圆形区域掩码 (可提前全局预算一次)
    yy, xx = np.ogrid[:h, :w]
    cy, cx = h / 2, w / 2
    circle = (yy - cy) ** 2 + (xx - cx) ** 2 <= (h / 2) ** 2
    mask &= circle
    if not mask.any():
        return None

    # 3) 把所有候选坐标提取出来
    ys, xs = np.where(mask)
    # （可选）调试时把这些点标红
    im_array[ys, xs] = [255, 0, 0]

    # 4) 交给原函数计算“最粗”点
    pts = list(zip(ys, xs))
    yi, xi, max_d = find_thickest_point((h, w), pts)
    if max_d < 1:
        return None

    return (yi, xi, max_d)


# def find_thickest_point(im_array,r_i,r_j,target_points):
#     from line_profiler import LineProfiler
#     lp = LineProfiler()
#     lp_wrapper = lp(find_thickest_point_pre)
#     result=lp_wrapper(im_array,r_i,r_j,target_points)
#     lp.print_stats()
#     return result

def find_thickest_point(shape, target_points):
    """
    shape 可能是 (h, w, 3) 或 (h, w)，我们只要前两个值。
    """
    # 支持三元组或二元组
    h, w = shape[:2]

    # 1) 构造二值 mask
    mask = np.zeros((h, w), dtype=np.uint8)
    ys, xs = zip(*target_points)
    mask[list(ys), list(xs)] = 255

    # 2) 距离变换（diamond 结构元半径3×3）
    dist = cv2.distanceTransform(mask, cv2.DIST_C, 3)

    # 3) 找最大值位置
    _, max_val, _, max_loc = cv2.minMaxLoc(dist)
    j, i = max_loc  # cv2 返回 (x=j, y=i)

    # 4) max_val 就是半径 d，坐标是 (i,j)
    return i, j, int(max_val)

def get_sin_cos(deg: float):
    """
    如果 deg 不是整数，就四舍五入到最近的整数再查表，
    也可以直接 int(deg) 取地板，精度差别通常很小。
    """
    idx = int(round(deg)) % 360
    return SIN_TABLE[idx], COS_TABLE[idx]

def find_square(im_array: np.ndarray, crop_h: int, crop_w: int, red=False):
    """
    优化版的 find_square：
    - im_array: RGB ndarray，形状 (H, W, 3)，uint8
    - crop_h, crop_w: 当前帧裁剪区域的高/宽（原来代码里用作“中心坐标计算”）
    - 返回值和原版 find_square 一致：(new_white, pre_white, post_white) 或 None

    关键步骤：
    1) 用向量化生成 mask_whites（所有 [255,255,255]）。
    2) 根据 i,j 坐标一次性剔除中心那个矩形区域。
    3) 用 cv2.distanceTransform 找出“最粗点” (r_i, r_j, max_d)。
    4) 沿射线方向，用 NumPy 批量算坐标并一次性判断，而不是 Python for-loop。
    5) “无情风暴”也用了向量化减掉半径 20 内的点。
    """

    H, W, _ = im_array.shape

    # ————————————————
    # 1. 用 NumPy 一步生成“白色像素”掩码
    #    mask_whites[i,j] = True 当且仅当 im_array[i,j] == [255,255,255]
    # ————————————————
    #  注意：np.all(im_array == 255, axis=2) 会自动把所有通道都对齐比较
    mask_whites = np.all(im_array == 255, axis=2)  # shape = (H, W), bool

    if not mask_whites.any():
        return None

    # ————————————————
    # 2. 计算并一次性剔除“中心矩形”区域
    #    原来代码里：if i > h*0.4 and i < h*0.6 以及 j > w*0.15 and j < w*0.85，就把那些白色改成黑
    #    我们用向量化：
    #       i_coords = 0,1,...,H-1  ； j_coords = 0,1,...,W-1
    #    中心区域：
    #       i ∈ (H*(200-40)/(2·200), H*(200+40)/(2·200))  → (0.4H, 0.6H)
    #       j ∈ (W*(200-140)/(2·200), W*(200+140)/(2·200)) → (0.15W, 0.85W)
    # ————————————————
    i_coords = np.arange(H).reshape((H, 1))   # shape (H,1)
    j_coords = np.arange(W).reshape((1, W))   # shape (1,W)

    i_min = H * (200 - 40) / 2 / 200   # 0.4H
    i_max = H * (200 + 40) / 2 / 200   # 0.6H
    j_min = W * (200 - 140) / 2 / 200  # 0.15W
    j_max = W * (200 + 140) / 2 / 200  # 0.85W

    rect_mask = (i_coords > i_min) & (i_coords < i_max) & (j_coords > j_min) & (j_coords < j_max)
    # 把这部分“在中心矩形里的白色”一并从 mask_whites 中去掉
    mask_whites[rect_mask] = False

    # 同时，如果你还想保持“视觉调试”时把这些中心白像素涂黑，可以：
    # im_array[rect_mask & (np.all(im_array == 255, axis=2))] = [0, 0, 0]
    # 但请注意：这样修改像素会改变后面的距离变换结果；若不需要可注释

    if not mask_whites.any():
        return None

    # ————————————————
    # 3. 直接用距离变换求“最粗点”
    #    cv2.distanceTransform 要求输入是 uint8 二值图，所以先转换
    # ————————————————
    mask_u8 = (mask_whites.astype(np.uint8)) * 255  # 0/255
    dist = cv2.distanceTransform(mask_u8, distanceType=cv2.DIST_C, maskSize=3)
    # cv2.minMaxLoc 找到最大值和位置 (x=j, y=i)
    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(dist)
    if maxVal < 1:
        return None

    max_d = int(maxVal)        # 半径
    center_j, center_i = maxLoc # maxLoc = (j, i)
    r_i, r_j = center_i, center_j

    # ————————————————
    # 4. 计算沿射线方向的角度 sin/cos（与原版保持一致）
    #    原先是：target = cal_degree(r_i - crop_h / 2, r_j - crop_w / 2)
    #    这里 crop_h, crop_w 都是外部给的（你在 driver() 里确定过）
    # ————————————————
    cy = crop_h / 2
    cx = crop_w / 2
    deg = cal_degree(r_i - cy, r_j - cx)
    sin_val, cos_val = get_sin_cos(deg)
    # ————————————————
    # 5. “向外搜索 pre_d”：从 max_d 一直到 20 ，判断哪些像素依旧在 mask_whites 里
    #    原来写法是 Python for-loop，现在用 NumPy 批量生成坐标数组再一次性 compare
    # ————————————————
    # 这里我们假设 max_search_radius = 20（和原代码里写死的一样），如果想从 max_d 到 20：
    radii = np.arange(max_d, 21)  # 比如 max_d=3 → array([3,4,5,...,20])

    # 批量算出这些位置的整数坐标
    pre_is = np.round(r_i - sin_val * radii).astype(np.int32)
    pre_js = np.round(r_j - cos_val * radii).astype(np.int32)
    # 先过滤越界的坐标
    valid_mask = (pre_is >= 0) & (pre_is < H) & (pre_js >= 0) & (pre_js < W)
    pre_is = pre_is[valid_mask]
    pre_js = pre_js[valid_mask]
    pre_radii = radii[valid_mask]

    # 现在 mask_whites[pre_is, pre_js] == True 表示“这个像素线上仍然是白(255,255,255)”
    # 找到第一个值为 False 的索引，若全部 True 则取最后一个 radius
    if pre_is.size == 0:
        pre_d = 0
    else:
        white_vals = mask_whites[pre_is, pre_js]  # bool array
        # np.where(~white_vals) 找到第一处“不是白”的位置
        idx_false = np.nonzero(~white_vals)[0]
        pre_d = int(pre_radii[idx_false[0]]) if idx_false.size > 0 else int(pre_radii[-1])

    # 同理算“post_d”：从 max_d 到 20，方向反过来（sin→+、cos→+）
    post_is = np.round(r_i + sin_val * radii).astype(np.int32)
    post_js = np.round(r_j + cos_val * radii).astype(np.int32)
    valid_mask2 = (post_is >= 0) & (post_is < H) & (post_js >= 0) & (post_js < W)
    post_is = post_is[valid_mask2]
    post_js = post_js[valid_mask2]
    post_radii = radii[valid_mask2]

    if post_is.size == 0:
        post_d = 0
    else:
        white_vals2 = mask_whites[post_is, post_js]
        idx_false2 = np.nonzero(~white_vals2)[0]
        post_d = int(post_radii[idx_false2[0]]) if idx_false2.size > 0 else int(post_radii[-1])

    # 如果 pre_d + post_d < 5，要做“merciless storm”特殊逻辑
    if pre_d + post_d < 5:
        # 原来做法：把所有 (i,j) ∈ target_points, 并且在 center 半径 20 内移除
        # 现在我们直接用向量化：
        yy, xx = np.nonzero(mask_whites)  # 所有白像素的 i,j 列表
        # 过滤掉 |i - r_i|<=20 且 |j - r_j|<=20
        storm_mask = (np.abs(yy - r_i) <= 20) & (np.abs(xx - r_j) <= 20)
        yy2 = yy[~storm_mask]
        xx2 = xx[~storm_mask]
        if yy2.size == 0:
            return None

        # 重新做距离变换：mask2 仅保留没被移除的那些白点
        mask2 = np.zeros((H, W), dtype=np.uint8)
        mask2[yy2, xx2] = 255
        dist2 = cv2.distanceTransform(mask2, cv2.DIST_C, 3)
        minVal2, maxVal2, minLoc2, maxLoc2 = cv2.minMaxLoc(dist2)
        if maxVal2 < 3:
            # 直接取两个“最粗点”看看角度大小，依旧需要再做一次三角函数对比
            r2_j, r2_i = maxLoc2
            deg1 = cal_degree(r_i - cy, r_j - cx)
            deg2 = cal_degree(r2_i - cy, r2_j - cx)
            if deg1 < deg2:
                pre_white = (r_i, r_j)
                post_white = (r2_i, r2_j)
            else:
                pre_white = (r2_i, r2_j)
                post_white = (r_i, r_j)
            new_white = (
                round((pre_white[0] + post_white[0]) / 2),
                round((pre_white[1] + post_white[1]) / 2)
            )
            # focus_level 清零逻辑由外面调用者自行管理
            return (new_white, pre_white, post_white)
        else:
            # 如果 maxVal2 >= 3，不做 storm 逻辑，继续按后续步骤
            r_i2, r_j2 = maxLoc2[1], maxLoc2[0]
            r_i, r_j, max_d = r_i2, r_j2, int(maxVal2)
            deg = cal_degree(r_i - cy, r_j - cx)
            sin_val, cos_val = SIN_TABLE[int(round(target)) % 360], COS_TABLE[int(round(target)) % 360]
            # 重新计算 pre_d, post_d 就像上面一样……
            radii2 = np.arange(max_d, 21)
            pre_is = np.round(r_i - sin_val * radii2).astype(np.int32)
            pre_js = np.round(r_j - cos_val * radii2).astype(np.int32)
            valid_mask = (pre_is >= 0) & (pre_is < H) & (pre_js >= 0) & (pre_js < W)
            pre_is = pre_is[valid_mask]; pre_js = pre_js[valid_mask]; rads = radii2[valid_mask]
            if pre_is.size == 0:
                pre_d = 0
            else:
                vals = mask2[pre_is, pre_js].astype(bool)
                idx_f = np.nonzero(~vals)[0]
                pre_d = int(rads[idx_f[0]]) if idx_f.size > 0 else int(rads[-1])

            post_is = np.round(r_i + sin_val * radii2).astype(np.int32)
            post_js = np.round(r_j + cos_val * radii2).astype(np.int32)
            valid_mask2 = (post_is >= 0) & (post_is < H) & (post_js >= 0) & (post_js < W)
            post_is = post_is[valid_mask2]; post_js = post_js[valid_mask2]; rads2 = radii2[valid_mask2]
            if post_is.size == 0:
                post_d = 0
            else:
                vals2 = mask2[post_is, post_js].astype(bool)
                idx_f2 = np.nonzero(~vals2)[0]
                post_d = int(rads2[idx_f2[0]]) if idx_f2.size > 0 else int(rads2[-1])

            # 继续后面逻辑
            pre_white = (round(r_i - sin_val * pre_d), round(r_j - cos_val * pre_d))
            post_white = (round(r_i + sin_val * post_d), round(r_j + cos_val * post_d))
            new_white = (
                round((pre_white[0] + post_white[0]) / 2),
                round((pre_white[1] + post_white[1]) / 2)
            )
            # 这里不额外打印“new white error”，假设容错
            return (new_white, pre_white, post_white)

    # ————————————————
    # 6. 常规情况：pre_d + post_d >= 5
    # ————————————————
    pre_white = (round(r_i - sin_val * pre_d), round(r_j - cos_val * pre_d))
    post_white = (round(r_i + sin_val * post_d), round(r_j + cos_val * post_d))

    new_white = (
        round((pre_white[0] + post_white[0]) / 2),
        round((pre_white[1] + post_white[1]) / 2)
    )
    # 原代码里还检查了一下 im_array[new_white] 是否是蓝色 [0,0,255]，但此处我们用 mask_whites 表示“是否白”
    # new_white 处只要在 mask_whites 中就肯定是白色
    # 如果一定要跟原版一模一样：可写：
    #     if not (0 <= new_white[0] < H and 0 <= new_white[1] < W and mask_whites[new_white]):
    #         print("new white error")
    #         return

    return (new_white, pre_white, post_white)


def wiggle(t1, deg1, direction, im1):
    speed = wiggle_speed * direction
    target1 = 270
    target2 = 90
    delta_deg1 = (target1 - deg1) % (direction * 360)
    delta_deg2 = (target2 - deg1) % (direction * 360)
    predict_time = min(delta_deg1 / speed, delta_deg2 / speed)
    print("predict time", predict_time)
    # sleep(0.75)
    # return #debug

    click_time = t1 + predict_time - press_and_release_delay + delay_degree / abs(speed)

    delta_t = click_time - time.time()

    # print('delta_t',delta_t)
    if delta_t < 0 and delta_t > -0.1:
        send_space()
        print('quick space!!', delta_t, '\nspeed:', speed)
        sleep(0.13)
        return
    try:
        delta_t = click_time - time.time()
        sleep(delta_t)
        send_space()
        print('space!!', delta_t, '\nspeed:', speed)
        # Image.fromarray(im1).save(imgdir + 'log.png')
        sleep(0.13)
    except ValueError as e:

        # winsound.Beep(230,300)
        print(e, delta_t, deg1, delta_deg1, delta_deg2)


def timer(im1, t1):
    global focus_level
    if not toggle:
        return
    # print('timer',time.time())
    r1 = find_red(im1)
    if not r1:
        return

    deg1 = cal_degree(r1[0] - crop_h / 2, r1[1] - crop_w / 2)

    # print('first seen:',deg1,t1)
    global last_im_a

    # sleep(1.5)
    # return #debug
    im2 = win_screenshot(region[0], region[1], crop_w, crop_h)

    r2 = find_red(im2)

    if not r2:
        return

    deg2 = cal_degree(r2[0] - crop_h / 2, r2[1] - crop_w / 2)
    if deg1 == deg2:
        # print("red same")
        return
    # speed = (deg2-deg1)/(t2-t1)

    if (deg2 - deg1) % 360 > 180:
        direction = -1
    else:
        direction = 1

    if speed_now == wiggle_speed:
        print("wiggle")
        return wiggle(t1, deg1, direction, im1)
    if (hyperfocus):
        speed = direction * speed_now * (1 + 0.04 * focus_level)
    else:
        speed = direction * speed_now

    # im2[pre_i][pre_j][0] > 200 and im2[pre_i][pre_j][1] < 20 and im2[pre_i][pre_j][2] < 20:

    white = find_square(im1, crop_h, crop_w)

    if not white:
        return
    print(white)
    white, pre_white, post_white = white

    if direction < 0:
        pre_white, post_white = post_white, pre_white
    im1[r1[0]][r1[1]] = [0, 255, 0]
    im1[white[0]][white[1]] = [0, 255, 0]
    last_im_a = im1

    print('targeting_time:', time.time() - t1)
    print('speed:', speed)

    target = cal_degree(white[0] - crop_h / 2, white[1] - crop_w / 2)
    # target=180

    # if target< 45 or target > 315 or (target>135 and target<225):
    #     white_2=(white[0],white[1]-max_d)
    #     white_3=(white[0],white[1]+max_d)
    # else:
    #     white_2=(white[0]-max_d,white[1])
    #     white_3=(white[0]+max_d,white[1])

    delta_deg = (target - deg1) % (direction * 360)

    print("predict time", delta_deg / speed)
    # sleep(0.75)
    # return #debug

    click_time = t1 + delta_deg / speed - press_and_release_delay + delay_degree / abs(speed)
    # print("minus ",click_time%(1/frame_rate))
    # click_time-=click_time%(1/frame_rate)
    delta_t = click_time - time.time()

    # sin=math.sin(2*math.pi*target/360)
    # cos=math.cos(2*math.pi*target/360)
    max_d = r1[2]
    global delay_pixel
    start_point = post_white
    sin, cos = SIN_TABLE[int(round(target)) % 360], COS_TABLE[int(round(target)) % 360]
    max_d += delay_pixel
    delta_i = pre_white[0] - white[0]
    delta_j = pre_white[1] - white[1]
    # if hyperfocus:
    #     delta_i*=(1+0.04*focus_level)
    #     delta_j*=(1+0.04*focus_level)
    end_point = [white[0] + round(delta_i - direction * sin * (-max_d)),
                 white[1] + round(delta_j - direction * cos * (-max_d))]
    check_points = []
    if abs(end_point[0] - start_point[0]) < abs(end_point[1] - start_point[1]):
        for j in range(start_point[1], end_point[1], 2 * np.sign(end_point[1] - start_point[1])):
            i = start_point[0] + (end_point[0] - start_point[0]) / (end_point[1] - start_point[1]) * (
                        j - start_point[1])
            i = round(i)
            check_points.append((i, j))
    elif np.sign(end_point[0] - start_point[0]) == 0:
        return
    else:
        for i in range(start_point[0], end_point[0], 2 * np.sign(end_point[0] - start_point[0])):
            j = start_point[1] + (end_point[1] - start_point[1]) / (end_point[0] - start_point[0]) * (
                        i - start_point[0])
            j = round(j)
            check_points.append((i, j))
    check_points.append(end_point)
    print('check points', check_points)
    pre_4deg_check_points = []

    if abs(end_point[0] - start_point[0]) ** 2 + abs(end_point[1] - start_point[1]) ** 2 < 20 ** 2:
        start_point = pre_white
        end_point = (end_point[0] + delta_i, end_point[1] + delta_j)
        # if the white area is  too large dont use pre_4deg
        if abs(end_point[0] - start_point[0]) < abs(end_point[1] - start_point[1]):
            for j in range(start_point[1], end_point[1], 2 * np.sign(end_point[1] - start_point[1])):
                i = start_point[0] + (end_point[0] - start_point[0]) / (end_point[1] - start_point[1]) * (
                            j - start_point[1])
                i = round(i)
                pre_4deg_check_points.append((i, j))
        elif np.sign(end_point[0] - start_point[0]) == 0:
            return
        else:
            for i in range(start_point[0], end_point[0], 2 * np.sign(end_point[0] - start_point[0])):
                j = start_point[1] + (end_point[1] - start_point[1]) / (end_point[0] - start_point[0]) * (
                            i - start_point[0])
                j = round(j)
                pre_4deg_check_points.append((i, j))
        pre_4deg_check_points.append(end_point)
    else:
        print('[!]large white area detected')
        check_points.pop()

    # TODO: extend pre_4deg_check_points for more degs

    print('pre 4 deg check points', pre_4deg_check_points)

    print('delta_t', delta_t)
    if delta_t < 0 and delta_t > -0.1:
        send_space()
        print('[!]quick space!!', delta_t, '\nspeed:', speed)
        # sleep(0.5)

        if (hyperfocus):
            print('focus hit:', focus_level)
            focus_level = (focus_level + 1) % 7
        return
    try:
        delta_t = click_time - time.time()
        # sleep(max(0,delta_t-0.1))

        ## trying to catch
        checks_after_awake = 0
        checkwhen = 0
        im_array_pre_backup = None
        while True:
            out = False
            im_array_pre = win_screenshot(region[0], region[1], crop_w, crop_h)
            checks_after_awake += 1

            for i, j in check_points:
                if im_array_pre[i][j][0] > red_sensitive and im_array_pre[i][j][1] < 20 and im_array_pre[i][j][2] < 20:
                    out = True
                    im_array_pre[i][j] = [0, 255, 255]
                    checkwhen = 1
                    break
            if out:
                break

            for k in range(len(pre_4deg_check_points)):
                i, j = pre_4deg_check_points[k]
                if im_array_pre[i][j][0] > red_sensitive and im_array_pre[i][j][1] < 20 and im_array_pre[i][j][2] < 20:
                    out = True
                    checkwhen = 2
                    im_array_pre[i][j] = [255, 255, 0]
                    t = 4 / speed_now * (1 + k) / len(pre_4deg_check_points) - press_and_release_delay
                    if t > 0:
                        sleep(t)
                    break
            if out:
                break
            if time.time() > click_time + 0.04:
                print('catch time out')
                break
            im_array_pre_backup = im_array_pre
        # if speed < 315:
        if type(im_array_pre_backup) == type(None):
            return

        send_space()
        print('checktime', checkwhen)
        if checks_after_awake <= 1:
            print('[!]awake quick space!!', delta_t, '\nspeed:', speed)
            file_name = 'awake'
        else:
            print('space!!', delta_t, '\nspeed:', speed)
            file_name = ''
        print(im_array_pre[pre_white[0], pre_white[1]])
        # Image.fromarray(im_array3).show()
        # return
        r3 = find_red(im_array_pre)
        shape = im_array_pre_backup.shape
        for i in range(shape[0]):
            for j in range(shape[1]):
                if im_array_pre_backup[i][j][0] > red_sensitive and im_array_pre_backup[i][j][1] < 20 and \
                        im_array_pre_backup[i][j][2] < 20:
                    l1, l2 = i - shape[0] / 2, j - shape[1] / 2
                    if l1 * l1 + l2 * l2 > shape[0] * shape[0] / 4:
                        # print('not in circle:',i,j)
                        continue
                    im_array_pre[i][j] = [255, 0, 0]

        if not r3:
            return

        deg3 = cal_degree(r3[0] - crop_h / 2, r3[1] - crop_w / 2)
        real_delta_deg = deg3 - target

        im_array_pre[r1[0]][r1[1]] = [0, 255, 0]
        im_array_pre[white[0]][white[1]] = [0, 0, 255]

        im_array_pre[r3[0]][r3[1]] = [255, 255, 0]

        for i, j in check_points:
            im_array_pre[i][j] = [255, 255, 0]
        for i, j in pre_4deg_check_points:
            im_array_pre[i][j] = [0, 255, 0]

        im_array_pre[post_white[0]][post_white[1]] = [0, 255, 0]
        im_array_pre[pre_white[0]][pre_white[1]] = [0, 255, 0]
        if hyperfocus:
            file_name += 'log_focus' + str(focus_level) + '_' + str(real_delta_deg) + '_' + str(int(time.time()))
        else:
            file_name += 'log_' + str(real_delta_deg) + '_' + str(int(time.time()))
        file_name += 'speed_' + str(speed) + '.png'
        file_name = imgdir + file_name
        # Image.fromarray(im_array_pre).save(file_name)
        # sleep(0.3)
        if (hyperfocus):
            print('focus hit:', focus_level)
            focus_level = min(6, (focus_level + 1))
    except ValueError as e:
        # Image.fromarray(im1).save(imgdir + 'log.png')
        # winsound.Beep(230,300)
        print(e, delta_t, deg1, deg2, target)

    # TODO: if white in im2


def win_screenshot_phys(region, crop_w, crop_h):
    """
    用物理像素坐标抓图，然后缩回 crop_w×crop_h 逻辑像素。
    region: dict with left/top/width/height（都是物理像素）
    """
    shot = _sct.grab(region)  # 大小 = (phys_h, phys_w)
    arr = np.asarray(shot)[:, :, :3][:, :, ::-1]  # BGRA→RGB
    # 缩回到 (crop_w, crop_h)

    return cv2.resize(arr, (crop_w, crop_h), interpolation=cv2.INTER_NEAREST)


def driver():
    global crop_w, crop_h, region ,cam

    # 1. 取所有物理屏列表（跳过 monitors[0]）
    mons = _sct.monitors[1:]
    # 2. 找主屏（left==0 且 top>=0）
    game_mon = next(m for m in mons if m['left'] == 0 and m['top'] >= 0)

    # 3. 按屏高决定 crop 大小
    screen_h = game_mon["height"]
    if screen_h == 1600:
        crop_w = crop_h = 250
    elif screen_h == 1080:
        crop_w = crop_h = 150
    elif screen_h == 2160:
        crop_w = crop_h = 330
    else:
        crop_w = crop_h = 200

    # 4. 先算“逻辑像素”中心
    startx = game_mon['left'] + (game_mon['width'] - crop_w) // 2
    starty = game_mon['top'] + (game_mon['height'] - crop_h) // 2

    # 5. 转成 DXCam 要的局部坐标 (l, t, r, b)
    lx = startx - game_mon['left']
    ly = starty - game_mon['top'] - 20
    rx = lx + crop_w
    by = ly + crop_h

    cam = dxcam.create(output_idx=0, output_color="RGB", max_buffer_len=1)
    cam.start(
        target_fps=frame_rate,
        region=(lx, ly, rx, by),
        video_mode=False
    )

    # 6. 构造给 mss 的物理像素区域
    region = [
        lx, ly,
        rx, by
    ]

    try:
        os.makedirs(imgdir, exist_ok=True)
        im0 = win_screenshot(region[0], region[1], region[2], region[3])
        Image.fromarray(im0).save(os.path.join(imgdir, 'startup_debug.png'))
    except Exception as e:
        print(f"[!] 调试截图保存失败：{e}")

    # 4. 主循环 —— 保持原逻辑
    try:
        while True:
            t0 = time.time()
            im_array = win_screenshot(region[0], region[1], crop_w, crop_h)  # ← 仍用优化后的函数
            timer(im_array, t0)
    except KeyboardInterrupt:
        pass
        # Image.fromarray(last_im_a).save(imgdir + 'last_log.png')


def cal_degree(x: float, y: float) -> float:
    """
    返回向量 (x,y) 相对于左向量 (-1,0) 的顺时针角度 [0,360)。
    计算式：angle = (atan2(y, x) + π) 转成度，并 mod 360。
    """
    # atan2(y, x) 结果是 [-π, π]，对应从正 X 轴逆时针转到 (x,y)
    # +π 把参考从正 X 轴移到负 X 轴，再转顺时针
    deg = math.degrees(math.atan2(y, x) + math.pi)
    return deg if deg < 360 else deg - 360


def keyboard_callback(x):
    global speed_now, delay_pixel, toggle, focus_level, hyperfocus, keyboard_switch

    if x.name == 'f1':
        if keyboard_switch:
            winsound.Beep(200, 500)
            keyboard_switch = False
            toggle = False
            print('keyboard_switch:', keyboard_switch)
        else:
            winsound.Beep(350, 500)
            keyboard_switch = True
            toggle = True
            print('keyboard_switch:', keyboard_switch)
    if not keyboard_switch:
        return
    if x.name == 'caps lock':
        if toggle:
            winsound.Beep(200, 500)
            toggle = False
            print('toggle:', toggle)
        else:
            winsound.Beep(350, 500)
            toggle = True
            print('toggle:', toggle)

    if not toggle:
        return
    if x.name in 'wasd':
        focus_level = 0
    if x.name == '3':
        toggle = True
        focus_level = 0
        print('change to repair')
        winsound.Beep(262, 500)
        speed_now = repair_speed
    if x.name == '4':
        toggle = True
        focus_level = 0
        winsound.Beep(300, 500)
        print('change to heal')
        speed_now = heal_speed
    if x.name == '5':
        toggle = True
        winsound.Beep(440, 500)
        print('change to wiggle')
        speed_now = wiggle_speed
    if x.name == '6':
        if hyperfocus:
            winsound.Beep(200, 500)
            hyperfocus = False
            print('hyperfocus disabled')
        else:
            winsound.Beep(350, 500)
            hyperfocus = True
            print('hyperfocus enabled')
    if x.name == '=':
        winsound.Beep(460, 500)
        delay_pixel += 2
        print('delay_pixel:', delay_pixel)
    if x.name == '-':
        winsound.Beep(500, 500)
        delay_pixel -= 2
        print('delay_pixel:', delay_pixel)


def bind_to_last_four_cores():
    p = psutil.Process(os.getpid())
    cpu_count = os.cpu_count()
    if cpu_count is not None and cpu_count >= 4:
        # 取最后 4 个核心的索引：从 cpu_count-4 到 cpu_count-1
        cores = list(range(cpu_count - 4, cpu_count))
        p.cpu_affinity(cores)
        print(f"已绑定到 CPU 核心 {cores}")
    else:
        print("CPU 核心不足，无法绑定最后四核")


def main():
    bind_to_last_four_cores()

    if not os.path.exists(imgdir):
        os.mkdir(imgdir)
    keyboard.on_press(keyboard_callback)
    threading.Thread(target=keyboard.wait)
    print('starting')
    driver()


ok, err = _test_win32_send()
if ok:
    print("Win32 SendInput 可用，后续继续使用它")
else:
    use_win32 = False
    print(f"Win32 SendInput 检测失败，错误码：{err}，后续将改用 pyautogui")
if __name__ == "__main__":
    # 提高本进程优先级（可选）
    try:
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        print('已设置为高优先级')
    except Exception as e:
        print(f"无法设置优先级: {e}")

    main()
