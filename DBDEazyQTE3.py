import keyboard
import pyautogui
import time
import win32gui,win32ui,win32con
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

imgdir='DBDimg/'
delay_degree = 0
crop_w, crop_h = 200, 200
last_im_a=0
region=[int((2560-crop_w)/2), int((1440-crop_h)/2),
                  crop_w, crop_h]
toggle=True
keyboard_switch=True
frame_rate=60
repair_speed=330
heal_speed=300
wiggle_speed=230
shot_delay= 0.00
press_and_release_delay= 0.003206
color_sensitive=125
delay_pixel=3
speed_now = repair_speed
hyperfocus=False
red_sensitive=180
focus_level=0
use_win32 = True

LOGPIXELSX = 88

user32 = ctypes.windll.user32
gdi32  = ctypes.windll.gdi32

# 拿主屏的 DC
hdc = user32.GetDC(0)
dpi = gdi32.GetDeviceCaps(hdc, LOGPIXELSX)  # 例如 144 表示 150% 缩放
user32.ReleaseDC(0, hdc)

# 计算缩放因子
scale_factor = dpi / 96.0

cam = dxcam.create(output_idx=0, output_color="RGB", max_buffer_len=2)
# cam.start(target_fps=120)

_sct = mss.mss()                                 
# 开启高精度计时器，让 mss DXGI 路径延迟更稳
windll.winmm.timeBeginPeriod(1)

# —— 平台相关类型 ——
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_ulonglong) else ctypes.c_ulong

# —— 常量 ——
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_SPACE = 0x20

# —— 把鼠标结构也一起定义进来 ——
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",        wintypes.LONG),
        ("dy",        wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags",   wintypes.DWORD),
        ("time",      wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",        wintypes.WORD),
        ("wScan",      wintypes.WORD),
        ("dwFlags",    wintypes.DWORD),
        ("time",       wintypes.DWORD),
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
        ("u",    _INPUTunion),
    ]

# —— 指定 SendInput 原型 ——
SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype  = wintypes.UINT

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
        img = cam.get_latest_frame(video_mode=True)
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
    circle = (yy - cy)**2 + (xx - cx)**2 <= (h/2)**2
    mask &= circle
    if not mask.any():
        return None

    # 3) 把所有候选坐标提取出来
    ys, xs = np.where(mask)
    #（可选）调试时把这些点标红
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
    j, i = max_loc    # cv2 返回 (x=j, y=i)

    # 4) max_val 就是半径 d，坐标是 (i,j)
    return i, j, int(max_val) 
    
def find_square(im_array):
    
    r_i = None
    shape = im_array.shape
    target_points=[]
    global focus_level
    for i in range(shape[0]):
        for j in range(shape[1]):
            if list(im_array[i][j]) == [255, 255, 255]:
                if i > shape[0]*(200-40)/2/200 and i < shape[0]*(200+40)/2/200 and j > shape[1]*(200-140)/2/200 and j < shape[1]*(200+140)/2/200:
                    im_array[i][j]=[0, 0, 0]
                    continue
                target_points.append((i,j))
                im_array[i][j]=[0, 0, 255]

    if not target_points:
        return
    
    r_i,r_j,max_d= find_thickest_point(shape,target_points)
    
    # print("white square:",r_i, r_j)
    if not r_i or not r_j:
        return
    # if max_d < 1:
    #     return 
    pre_d=0
    post_d=0
    target = cal_degree(r_i-crop_h/2, r_j-crop_w/2)
    sin=math.sin(2*math.pi*target/360)
    cos=math.cos(2*math.pi*target/360)
    for i in range(max_d,21):
        pre_i=round(r_i-sin*i)
        pre_j=round(r_j-cos*i)
        if list(im_array[pre_i][pre_j]) ==[0, 0, 255]:
            pre_d=i
        else:
            break
    for i in range(max_d,21):
        pre_i=round(r_i+sin*i)
        pre_j=round(r_j+cos*i)
        if list(im_array[pre_i][pre_j]) ==[0, 0, 255]:
            post_d=i
        else:
            break
    print(pre_d,post_d)
    
    if pre_d + post_d < 5:
        print('merciless storm')
        # Image.fromarray(im_array).save(imgdir+'merciless.png')
        to_be_deleted=[]
        for i,j in target_points:
            if abs(i - r_i) <= 20 and abs(j - r_j) <= 20:
                to_be_deleted.append((i,j))
        print('before',target_points)
    
        for i in to_be_deleted:
            target_points.remove(i)
        print('after',target_points)
        if not target_points:
            return
        r2_i,r2_j,max_d= find_thickest_point(shape,target_points)
        if max_d < 3:
            target1= cal_degree(r_i-crop_h/2, r_j-crop_w/2)
            target2= cal_degree(r2_i-crop_h/2, r2_j-crop_w/2)
            print('storm points',r_i,r_j,r2_i,r2_j)
            if target1 < target2:
                pre_white=(r_i,r_j)
                post_white=(r2_i,r2_j)
            else:
                pre_white=(r2_i,r2_j)
                post_white=(r_i,r_j)
            new_white=(round((pre_white[0]+post_white[0])/2),round((pre_white[1]+post_white[1])/2))
            focus_level=0
            return (new_white,pre_white,post_white)
    
    pre_white=(round(r_i-sin*pre_d),round(r_j-cos*pre_d))
    post_white=(round(r_i+sin*post_d),round(r_j+cos*post_d))

    new_white=(round((pre_white[0]+post_white[0])/2),round((pre_white[1]+post_white[1])/2))
    if list(im_array[new_white[0]][new_white[1]]) != [0, 0, 255]:
        print("new white error")
        return
    # 
               
    return (new_white,pre_white,post_white)

def wiggle(t1,deg1,direction,im1):
    speed=wiggle_speed*direction
    target1=270
    target2=90
    delta_deg1=(target1-deg1)%(direction*360)
    delta_deg2=(target2-deg1)%(direction*360)
    predict_time=min(delta_deg1/speed ,delta_deg2/speed)
    print("predict time",predict_time)
    # sleep(0.75)
    # return #debug 
    
    click_time = t1 + predict_time - press_and_release_delay + delay_degree/abs(speed)

    delta_t = click_time-time.time() 
    
    # print('delta_t',delta_t)
    if delta_t < 0 and delta_t > -0.1:
        send_space()
        print('quick space!!', delta_t, '\nspeed:', speed)
        sleep(0.13)
        return 
    try:
        delta_t = click_time-time.time() 
        sleep(delta_t)
        send_space()
        print('space!!', delta_t, '\nspeed:', speed)
        Image.fromarray(im1).save(imgdir+'log.png')
        sleep(0.13)
    except ValueError as e:
        
        # winsound.Beep(230,300)
        print(e,delta_t, deg1, delta_deg1, delta_deg2)

def timer(im1, t1):
    global focus_level
    if not toggle:
        return
    # print('timer',time.time())
    r1 = find_red(im1)
    if not r1:
        return

    deg1 = cal_degree(r1[0]-crop_h/2, r1[1]-crop_w/2)


    
    # print('first seen:',deg1,t1)
    global last_im_a
    
    # sleep(1.5)
    # return #debug 
    im2 = win_screenshot(region[0],region[1],crop_w, crop_h)

    r2 = find_red(im2)
    
    if not r2:
        return 
    
    
    deg2 = cal_degree(r2[0]-crop_h/2, r2[1]-crop_w/2)
    if deg1 == deg2:
        # print("red same")
        return
    # speed = (deg2-deg1)/(t2-t1)
    
    if (deg2-deg1)%360 > 180:
        direction=-1
    else:
        direction=1
    
    
    
    
    
    if speed_now==wiggle_speed:
        print("wiggle")
        return wiggle(t1,deg1,direction,im1)
    if(hyperfocus):
        speed = direction*speed_now*(1+0.04*focus_level)
    else:
        speed = direction*speed_now
    
    
    # im2[pre_i][pre_j][0] > 200 and im2[pre_i][pre_j][1] < 20 and im2[pre_i][pre_j][2] < 20:
    

    
    
    
    white = find_square(im1)
    
    
    if not white:
        return
    print(white)
    white,pre_white,post_white=white

    if direction < 0:
        pre_white,post_white=post_white,pre_white
    im1[r1[0]][r1[1]]=[0,255,0]
    im1[white[0]][white[1]]=[0,255,0]
    last_im_a=im1
    
    
    print('targeting_time:',time.time()-t1)
    print('speed:',speed)
    
    
    
    target = cal_degree(white[0]-crop_h/2, white[1]-crop_w/2)
    # target=180
    

    # if target< 45 or target > 315 or (target>135 and target<225):
    #     white_2=(white[0],white[1]-max_d)
    #     white_3=(white[0],white[1]+max_d)
    # else:
    #     white_2=(white[0]-max_d,white[1])
    #     white_3=(white[0]+max_d,white[1])

    delta_deg=(target-deg1)%(direction*360)
    
    print("predict time",delta_deg/speed)
    # sleep(0.75)
    # return #debug 
    
    click_time = t1 + delta_deg/speed -press_and_release_delay + delay_degree/abs(speed)
    # print("minus ",click_time%(1/frame_rate))
    # click_time-=click_time%(1/frame_rate)
    delta_t = click_time-time.time() 
    
    
    # sin=math.sin(2*math.pi*target/360)
    # cos=math.cos(2*math.pi*target/360) 
    max_d=r1[2]
    global delay_pixel
    start_point=post_white
    sin=math.sin(2*math.pi*target/360)
    cos=math.cos(2*math.pi*target/360)
    max_d+=delay_pixel
    delta_i=pre_white[0]-white[0]
    delta_j=pre_white[1]-white[1]
    # if hyperfocus:
    #     delta_i*=(1+0.04*focus_level)
    #     delta_j*=(1+0.04*focus_level)
    end_point=[white[0]+round(delta_i-direction*sin*(-max_d)),white[1]+round(delta_j-direction*cos*(-max_d))]
    check_points=[]
    if abs(end_point[0]-start_point[0]) < abs(end_point[1]-start_point[1]):
        for j in range(start_point[1],end_point[1],2*np.sign(end_point[1]-start_point[1])):
            i=start_point[0]+(end_point[0]-start_point[0])/(end_point[1]-start_point[1])*(j-start_point[1])
            i=round(i)
            check_points.append((i,j))
    elif np.sign(end_point[0]-start_point[0])==0:
        return
    else:
        for i in range(start_point[0],end_point[0],2*np.sign(end_point[0]-start_point[0])):
            j=start_point[1]+(end_point[1]-start_point[1])/(end_point[0]-start_point[0])*(i-start_point[0])
            j=round(j)
            check_points.append((i,j))
    check_points.append(end_point)
    print('check points',check_points)
    pre_4deg_check_points=[]
    
    if abs(end_point[0]-start_point[0])**2 + abs(end_point[1]-start_point[1])**2 < 20**2: 
        start_point=pre_white
        end_point=(end_point[0]+delta_i,end_point[1]+delta_j)
        # if the white area is  too large dont use pre_4deg
        if abs(end_point[0]-start_point[0]) < abs(end_point[1]-start_point[1]):
            for j in range(start_point[1],end_point[1],2*np.sign(end_point[1]-start_point[1])):
                i=start_point[0]+(end_point[0]-start_point[0])/(end_point[1]-start_point[1])*(j-start_point[1])
                i=round(i)
                pre_4deg_check_points.append((i,j))
        elif np.sign(end_point[0]-start_point[0])==0:
            return
        else:
            for i in range(start_point[0],end_point[0],2*np.sign(end_point[0]-start_point[0])):
                j=start_point[1]+(end_point[1]-start_point[1])/(end_point[0]-start_point[0])*(i-start_point[0])
                j=round(j)
                pre_4deg_check_points.append((i,j))
        pre_4deg_check_points.append(end_point)
    else:
        print('[!]large white area detected')
        check_points.pop()

    #TODO: extend pre_4deg_check_points for more degs
    
    print('pre 4 deg check points',pre_4deg_check_points)
    
    print('delta_t',delta_t)
    if delta_t < 0 and delta_t > -0.1:
        send_space()
        print('[!]quick space!!', delta_t, '\nspeed:', speed)
        # sleep(0.5)

        if(hyperfocus):
            print('focus hit:',focus_level)
            focus_level=(focus_level+1)%7
        return 
    try:
        delta_t = click_time-time.time() 
        # sleep(max(0,delta_t-0.1))
            
        ## trying to catch
        checks_after_awake=0
        checkwhen=0
        im_array_pre_backup=None
        while True:
            out=False
            im_array_pre = win_screenshot(region[0],region[1],crop_w, crop_h)
            checks_after_awake+=1
            
            for i,j in check_points:
                if  im_array_pre[i][j][0] > red_sensitive and im_array_pre[i][j][1] < 20 and im_array_pre[i][j][2] < 20:
                    out=True
                    im_array_pre[i][j]=[0,255,255]
                    checkwhen=1
                    break
            if out:
                break  
            
            for k in range(len(pre_4deg_check_points)):
                i,j=pre_4deg_check_points[k]
                if  im_array_pre[i][j][0] > red_sensitive and im_array_pre[i][j][1] < 20 and im_array_pre[i][j][2] < 20:
                    out=True
                    checkwhen=2
                    im_array_pre[i][j]=[255,255,0]
                    t=4/speed_now*(1+k)/len(pre_4deg_check_points)-press_and_release_delay
                    if t > 0:
                        sleep(t)
                    break
            if out:
                break  
            if time.time() > click_time+0.04:
                print('catch time out')
                break
            im_array_pre_backup=im_array_pre
        # if speed < 315:
        if type(im_array_pre_backup)==type(None):
           return
            
        send_space()
        print('checktime',checkwhen)
        if checks_after_awake <=1:
            print('[!]awake quick space!!', delta_t, '\nspeed:', speed)
            file_name='awake'
        else:
            print('space!!', delta_t, '\nspeed:', speed)
            file_name=''
        print(im_array_pre[pre_white[0],pre_white[1]])
        # Image.fromarray(im_array3).show()
        # return
        r3= find_red(im_array_pre)
        shape = im_array_pre_backup.shape
        for i in range(shape[0]):
            for j in range(shape[1]):
                if im_array_pre_backup[i][j][0] > red_sensitive and im_array_pre_backup[i][j][1] < 20 and im_array_pre_backup[i][j][2] < 20:
                    l1,l2=i-shape[0]/2,j-shape[1]/2
                    if l1*l1+l2*l2 > shape[0]*shape[0]/4:
                        # print('not in circle:',i,j)
                        continue
                    im_array_pre[i][j]=[255,0,0]
        
        if not r3:
            return
        
        
        deg3=cal_degree(r3[0]-crop_h/2, r3[1]-crop_w/2)
        real_delta_deg=deg3-target
        
        im_array_pre[r1[0]][r1[1]]=[0,255,0]
        im_array_pre[white[0]][white[1]]=[0,0,255]
        
        im_array_pre[r3[0]][r3[1]]=[255,255,0]
        
        for i,j in check_points:
            im_array_pre[i][j]=[255,255,0]
        for i,j in pre_4deg_check_points:
            im_array_pre[i][j]=[0,255,0]
            
        im_array_pre[post_white[0]][post_white[1]]=[0,255,0]
        im_array_pre[pre_white[0]][pre_white[1]]=[0,255,0]
        if hyperfocus:
            file_name+='log_focus'+str(focus_level)+'_'+str(real_delta_deg)+'_'+str(int(time.time()))
        else:
            file_name+='log_'+str(real_delta_deg)+'_'+str(int(time.time()))
        file_name+='speed_'+str(speed)+'.png'
        file_name=imgdir+file_name
        Image.fromarray(im_array_pre).save(file_name)
        # sleep(0.3)
        if(hyperfocus):
            print('focus hit:',focus_level)
            focus_level=min(6,(focus_level+1))
    except ValueError as e:
        Image.fromarray(im1).save(imgdir+'log.png')
        # winsound.Beep(230,300)
        print(e,delta_t, deg1, deg2, target)

    # TODO: if white in im2

def win_screenshot_phys(region, crop_w, crop_h):
    """
    用物理像素坐标抓图，然后缩回 crop_w×crop_h 逻辑像素。
    region: dict with left/top/width/height（都是物理像素）
    """
    shot = _sct.grab(region)                          # 大小 = (phys_h, phys_w)
    arr  = np.asarray(shot)[:, :, :3][:, :, ::-1]     # BGRA→RGB
    # 缩回到 (crop_w, crop_h)

    return cv2.resize(arr, (crop_w, crop_h), interpolation=cv2.INTER_NEAREST)


def driver():
    global crop_w, crop_h, region

    # 1. 取所有物理屏列表（跳过 monitors[0]）
    mons = _sct.monitors[1:]
    # 2. 找主屏（left==0 且 top>=0）
    game_mon = next(m for m in mons if m['left']==0 and m['top']>=0)

    # 3. 按屏高决定 crop 大小
    screen_h = game_mon["height"]
    if   screen_h == 1600: crop_w = crop_h = 250
    elif screen_h == 1080: crop_w = crop_h = 150
    elif screen_h == 2160: crop_w = crop_h = 330
    else:    crop_w = crop_h = 200

    # 4. 先算“逻辑像素”中心
    startx = game_mon['left'] + (game_mon['width']  - crop_w)//2
    starty = game_mon['top']  + (game_mon['height'] - crop_h)//2

    # 5. 转成 DXCam 要的局部坐标 (l, t, r, b)
    lx = startx - game_mon['left']
    ly = starty - game_mon['top']
    rx = lx + crop_w
    by = ly + crop_h

    cam = dxcam.create(output_idx=0, output_color="RGB", max_buffer_len=1)
    cam.start(
        target_fps=40,
        region=(lx, ly, rx, by),
        video_mode=True
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
            im_array = win_screenshot(region[0],region[1],crop_w, crop_h)   # ← 仍用优化后的函数
            timer(im_array, t0)
    except KeyboardInterrupt:
        Image.fromarray(last_im_a).save(imgdir + 'last_log.png')

        
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
    global speed_now,delay_pixel,toggle,focus_level,hyperfocus,keyboard_switch
    
    if x.name=='f1':
        if keyboard_switch:
            winsound.Beep(200,500)
            keyboard_switch=False
            toggle=False
            print('keyboard_switch:', keyboard_switch)
        else:
            winsound.Beep(350,500)
            keyboard_switch=True
            toggle=True
            print('keyboard_switch:', keyboard_switch)
    if not keyboard_switch: 
        return
    if x.name=='caps lock':
        if toggle:
            winsound.Beep(200,500)
            toggle=False
            print('toggle:', toggle)
        else:
            winsound.Beep(350,500)
            toggle=True
            print('toggle:', toggle)
    
    if not toggle: 
        return
    if x.name in 'wasd':    
        focus_level=0
    if x.name=='3':
        toggle=True
        focus_level=0
        print('change to repair')
        winsound.Beep(262,500)
        speed_now=repair_speed
    if x.name=='4':
        toggle=True
        focus_level=0
        winsound.Beep(300,500)
        print('change to heal')
        speed_now=heal_speed
    if x.name=='5':
        toggle=True
        winsound.Beep(440,500)
        print('change to wiggle')
        speed_now=wiggle_speed
    if x.name=='6':
        if hyperfocus:
            winsound.Beep(200,500)
            hyperfocus=False
            print('hyperfocus disabled')
        else:
            winsound.Beep(350,500)
            hyperfocus=True
            print('hyperfocus enabled')
    if x.name=='=':
        winsound.Beep(460,500)
        delay_pixel+=2
        print('delay_pixel:',delay_pixel)
    if x.name=='-': 
        winsound.Beep(500,500)
        delay_pixel-=2
        print('delay_pixel:',delay_pixel)


def bind_to_last_core():
    p = psutil.Process(os.getpid())
    cpu_count = os.cpu_count()
    if cpu_count is not None and cpu_count > 1:
        last_core = cpu_count - 1
        p.cpu_affinity([last_core])
        print(f"已绑定到 CPU 核心 #{last_core}")
    else:
        print("CPU 核心不足，无法绑定")


def main():
    bind_to_last_core()  # ← 在主函数最开始绑定

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
