_H='log.png'
_G='space!!'
_F='predict time'
_E='height'
_D='space'
_C='\nspeed:'
_B=False
_A=True
import keyboard,pyautogui,time,win32gui,win32ui,win32con,threading,numpy as np
from PIL import Image
import winsound,math,psutil,mss
from ctypes import windll
import cv2,math
imgdir='DBDimg/'
delay_degree=0
crop_w,crop_h=200,200
last_im_a=0
region=[int((2560-crop_w)/2),int((1440-crop_h)/2),crop_w,crop_h]
toggle=_A
keyboard_switch=_A
frame_rate=60
repair_speed=330
heal_speed=300
wiggle_speed=230
shot_delay=.0
press_and_release_delay=.003206
color_sensitive=125
delay_pixel=1
speed_now=repair_speed
hyperfocus=_B
red_sensitive=180
focus_level=0
_sct=mss.mss()
windll.winmm.timeBeginPeriod(1)
def sleep(t):
	st=time.time()
	while _A:
		offset=time.time()-st
		if offset>=t:break
def sleep_to(time_stamp):
	while _A:
		offset=time.time()-time_stamp
		if offset>=0:break
def win_screenshot(startw,starth,w,h):shot=_sct.grab({'left':startw,'top':starth,'width':w,_E:h});img=np.asarray(shot)[:,:,:3];return img[:,:,::-1]
def find_red(im_array):
	h,w,_=im_array.shape;r=im_array[:,:,0];g=im_array[:,:,1];b=im_array[:,:,2];mask=(r>red_sensitive)&(g<20)&(b<20)
	if not mask.any():return
	yy,xx=np.ogrid[:h,:w];cy,cx=h/2,w/2;circle=(yy-cy)**2+(xx-cx)**2<=(h/2)**2;mask&=circle
	if not mask.any():return
	ys,xs=np.where(mask);im_array[ys,xs]=[255,0,0];pts=list(zip(ys,xs));yi,xi,max_d=find_thickest_point((h,w),pts)
	if max_d<1:return
	return yi,xi,max_d
def find_thickest_point(shape,target_points):h,w=shape[:2];mask=np.zeros((h,w),dtype=np.uint8);ys,xs=zip(*target_points);mask[list(ys),list(xs)]=255;dist=cv2.distanceTransform(mask,cv2.DIST_C,3);_,max_val,_,max_loc=cv2.minMaxLoc(dist);j,i=max_loc;return i,j,int(max_val)
def find_square(im_array):
	r_i=None;shape=im_array.shape;target_points=[];global focus_level
	for i in range(shape[0]):
		for j in range(shape[1]):
			if list(im_array[i][j])==[255,255,255]:
				if i>shape[0]*160/2/200 and i<shape[0]*240/2/200 and j>shape[1]*60/2/200 and j<shape[1]*340/2/200:im_array[i][j]=[0,0,0];continue
				target_points.append((i,j));im_array[i][j]=[0,0,255]
	if not target_points:return
	r_i,r_j,max_d=find_thickest_point(shape,target_points)
	if not r_i or not r_j:return
	pre_d=0;post_d=0;target=cal_degree(r_i-crop_h/2,r_j-crop_w/2);sin=math.sin(2*math.pi*target/360);cos=math.cos(2*math.pi*target/360)
	for i in range(max_d,21):
		pre_i=round(r_i-sin*i);pre_j=round(r_j-cos*i)
		if list(im_array[pre_i][pre_j])==[0,0,255]:pre_d=i
		else:break
	for i in range(max_d,21):
		pre_i=round(r_i+sin*i);pre_j=round(r_j+cos*i)
		if list(im_array[pre_i][pre_j])==[0,0,255]:post_d=i
		else:break
	print(pre_d,post_d)
	if pre_d+post_d<5:
		print('merciless storm');to_be_deleted=[]
		for(i,j)in target_points:
			if abs(i-r_i)<=20 and abs(j-r_j)<=20:to_be_deleted.append((i,j))
		print('before',target_points)
		for i in to_be_deleted:target_points.remove(i)
		print('after',target_points)
		if not target_points:return
		r2_i,r2_j,max_d=find_thickest_point(shape,target_points)
		if max_d<3:
			target1=cal_degree(r_i-crop_h/2,r_j-crop_w/2);target2=cal_degree(r2_i-crop_h/2,r2_j-crop_w/2);print('storm points',r_i,r_j,r2_i,r2_j)
			if target1<target2:pre_white=r_i,r_j;post_white=r2_i,r2_j
			else:pre_white=r2_i,r2_j;post_white=r_i,r_j
			new_white=round((pre_white[0]+post_white[0])/2),round((pre_white[1]+post_white[1])/2);focus_level=0;return new_white,pre_white,post_white
	pre_white=round(r_i-sin*pre_d),round(r_j-cos*pre_d);post_white=round(r_i+sin*post_d),round(r_j+cos*post_d);new_white=round((pre_white[0]+post_white[0])/2),round((pre_white[1]+post_white[1])/2)
	if list(im_array[new_white[0]][new_white[1]])!=[0,0,255]:print('new white error');return
	return new_white,pre_white,post_white
def wiggle(t1,deg1,direction,im1):
	speed=wiggle_speed*direction;target1=270;target2=90;delta_deg1=(target1-deg1)%(direction*360);delta_deg2=(target2-deg1)%(direction*360);predict_time=min(delta_deg1/speed,delta_deg2/speed);print(_F,predict_time);click_time=t1+predict_time-press_and_release_delay+delay_degree/abs(speed);delta_t=click_time-time.time()
	if delta_t<0 and delta_t>-.1:keyboard.press_and_release(_D);print('quick space!!',delta_t,_C,speed);sleep(.13);return
	try:delta_t=click_time-time.time();sleep(delta_t);keyboard.press_and_release(_D);print(_G,delta_t,_C,speed);Image.fromarray(im1).save(imgdir+_H);sleep(.13)
	except ValueError as e:print(e,delta_t,deg1,delta_deg1,delta_deg2)
def timer(im1,t1):
	B='focus hit:';A='_';global focus_level
	if not toggle:return
	r1=find_red(im1)
	if not r1:return
	deg1=cal_degree(r1[0]-crop_h/2,r1[1]-crop_w/2);global last_im_a;im2=win_screenshot(region[0],region[1],crop_w,crop_h);r2=find_red(im2)
	if not r2:return
	deg2=cal_degree(r2[0]-crop_h/2,r2[1]-crop_w/2)
	if deg1==deg2:return
	if(deg2-deg1)%360>180:direction=-1
	else:direction=1
	if speed_now==wiggle_speed:print('wiggle');return wiggle(t1,deg1,direction,im1)
	if hyperfocus:speed=direction*speed_now*(1+.04*focus_level)
	else:speed=direction*speed_now
	white=find_square(im1)
	if not white:return
	print(white);white,pre_white,post_white=white
	if direction<0:pre_white,post_white=post_white,pre_white
	im1[r1[0]][r1[1]]=[0,255,0];im1[white[0]][white[1]]=[0,255,0];last_im_a=im1;print('targeting_time:',time.time()-t1);print('speed:',speed);target=cal_degree(white[0]-crop_h/2,white[1]-crop_w/2);delta_deg=(target-deg1)%(direction*360);print(_F,delta_deg/speed);click_time=t1+delta_deg/speed-press_and_release_delay+delay_degree/abs(speed);delta_t=click_time-time.time();max_d=r1[2];global delay_pixel;start_point=post_white;sin=math.sin(2*math.pi*target/360);cos=math.cos(2*math.pi*target/360);max_d+=delay_pixel;delta_i=pre_white[0]-white[0];delta_j=pre_white[1]-white[1];end_point=[white[0]+round(delta_i-direction*sin*-max_d),white[1]+round(delta_j-direction*cos*-max_d)];check_points=[]
	if abs(end_point[0]-start_point[0])<abs(end_point[1]-start_point[1]):
		for j in range(start_point[1],end_point[1],2*np.sign(end_point[1]-start_point[1])):i=start_point[0]+(end_point[0]-start_point[0])/(end_point[1]-start_point[1])*(j-start_point[1]);i=round(i);check_points.append((i,j))
	elif np.sign(end_point[0]-start_point[0])==0:return
	else:
		for i in range(start_point[0],end_point[0],2*np.sign(end_point[0]-start_point[0])):j=start_point[1]+(end_point[1]-start_point[1])/(end_point[0]-start_point[0])*(i-start_point[0]);j=round(j);check_points.append((i,j))
	check_points.append(end_point);print('check points',check_points);pre_4deg_check_points=[]
	if abs(end_point[0]-start_point[0])**2+abs(end_point[1]-start_point[1])**2<20**2:
		start_point=pre_white;end_point=end_point[0]+delta_i,end_point[1]+delta_j
		if abs(end_point[0]-start_point[0])<abs(end_point[1]-start_point[1]):
			for j in range(start_point[1],end_point[1],2*np.sign(end_point[1]-start_point[1])):i=start_point[0]+(end_point[0]-start_point[0])/(end_point[1]-start_point[1])*(j-start_point[1]);i=round(i);pre_4deg_check_points.append((i,j))
		elif np.sign(end_point[0]-start_point[0])==0:return
		else:
			for i in range(start_point[0],end_point[0],2*np.sign(end_point[0]-start_point[0])):j=start_point[1]+(end_point[1]-start_point[1])/(end_point[0]-start_point[0])*(i-start_point[0]);j=round(j);pre_4deg_check_points.append((i,j))
		pre_4deg_check_points.append(end_point)
	else:print('[!]large white area detected');check_points.pop()
	print('pre 4 deg check points',pre_4deg_check_points);print('delta_t',delta_t)
	if delta_t<0 and delta_t>-.1:
		keyboard.press_and_release(_D);print('[!]quick space!!',delta_t,_C,speed)
		if hyperfocus:print(B,focus_level);focus_level=(focus_level+1)%7
		return
	try:
		delta_t=click_time-time.time();checks_after_awake=0;checkwhen=0;im_array_pre_backup=None
		while _A:
			out=_B;im_array_pre=win_screenshot(region[0],region[1],crop_w,crop_h);checks_after_awake+=1
			for(i,j)in check_points:
				if im_array_pre[i][j][0]>red_sensitive and im_array_pre[i][j][1]<20 and im_array_pre[i][j][2]<20:out=_A;im_array_pre[i][j]=[0,255,255];checkwhen=1;break
			if out:break
			for k in range(len(pre_4deg_check_points)):
				i,j=pre_4deg_check_points[k]
				if im_array_pre[i][j][0]>red_sensitive and im_array_pre[i][j][1]<20 and im_array_pre[i][j][2]<20:
					out=_A;checkwhen=2;im_array_pre[i][j]=[255,255,0];t=4/speed_now*(1+k)/len(pre_4deg_check_points)-press_and_release_delay
					if t>0:sleep(t)
					break
			if out:break
			if time.time()>click_time+.04:print('catch time out');break
			im_array_pre_backup=im_array_pre
		if type(im_array_pre_backup)==type(None):return
		keyboard.press_and_release(_D);print('checktime',checkwhen)
		if checks_after_awake<=1:print('[!]awake quick space!!',delta_t,_C,speed);file_name='awake'
		else:print(_G,delta_t,_C,speed);file_name=''
		print(im_array_pre[pre_white[0],pre_white[1]]);r3=find_red(im_array_pre);shape=im_array_pre_backup.shape
		for i in range(shape[0]):
			for j in range(shape[1]):
				if im_array_pre_backup[i][j][0]>red_sensitive and im_array_pre_backup[i][j][1]<20 and im_array_pre_backup[i][j][2]<20:
					l1,l2=i-shape[0]/2,j-shape[1]/2
					if l1*l1+l2*l2>shape[0]*shape[0]/4:continue
					im_array_pre[i][j]=[255,0,0]
		if not r3:return
		deg3=cal_degree(r3[0]-crop_h/2,r3[1]-crop_w/2);real_delta_deg=deg3-target;im_array_pre[r1[0]][r1[1]]=[0,255,0];im_array_pre[white[0]][white[1]]=[0,0,255];im_array_pre[r3[0]][r3[1]]=[255,255,0]
		for(i,j)in check_points:im_array_pre[i][j]=[255,255,0]
		for(i,j)in pre_4deg_check_points:im_array_pre[i][j]=[0,255,0]
		im_array_pre[post_white[0]][post_white[1]]=[0,255,0];im_array_pre[pre_white[0]][pre_white[1]]=[0,255,0]
		if hyperfocus:file_name+='log_focus'+str(focus_level)+A+str(real_delta_deg)+A+str(int(time.time()))
		else:file_name+='log_'+str(real_delta_deg)+A+str(int(time.time()))
		file_name+='speed_'+str(speed)+'.png';file_name=imgdir+file_name;Image.fromarray(im_array_pre).save(file_name)
		if hyperfocus:print(B,focus_level);focus_level=min(6,focus_level+1)
	except ValueError as e:Image.fromarray(im1).save(imgdir+_H);print(e,delta_t,deg1,deg2,target)
def driver():
	global crop_w,crop_h,region;mon=_sct.monitors[1];screen_w,screen_h=mon['width'],mon[_E]
	if screen_h==1600:crop_w=crop_h=250
	elif screen_h==1080:crop_w=crop_h=150
	elif screen_h==2160:crop_w=crop_h=330
	else:crop_w=crop_h=200
	region=[(screen_w-crop_w)//2,(screen_h-crop_h)//2,crop_w,crop_h]
	try:
		while _A:t0=time.time();im_array=win_screenshot(*region);timer(im_array,t0)
	except KeyboardInterrupt:Image.fromarray(last_im_a).save(imgdir+'last_log.png')
def cal_degree(x,y):deg=math.degrees(math.atan2(y,x)+math.pi);return deg if deg<360 else deg-360
def keyboard_callback(x):
	C='delay_pixel:';B='toggle:';A='keyboard_switch:';global speed_now,delay_pixel,toggle,focus_level,hyperfocus,keyboard_switch
	if x.name=='f1':
		if keyboard_switch:winsound.Beep(200,500);keyboard_switch=_B;toggle=_B;print(A,keyboard_switch)
		else:winsound.Beep(350,500);keyboard_switch=_A;toggle=_A;print(A,keyboard_switch)
	if not keyboard_switch:return
	if x.name=='caps lock':
		if toggle:winsound.Beep(200,500);toggle=_B;print(B,toggle)
		else:winsound.Beep(350,500);toggle=_A;print(B,toggle)
	if not toggle:return
	if x.name in'wasd':focus_level=0
	if x.name=='3':toggle=_A;focus_level=0;print('change to repair');winsound.Beep(262,500);speed_now=repair_speed
	if x.name=='4':toggle=_A;focus_level=0;winsound.Beep(300,500);print('change to heal');speed_now=heal_speed
	if x.name=='5':toggle=_A;winsound.Beep(440,500);print('change to wiggle');speed_now=wiggle_speed
	if x.name=='6':
		if hyperfocus:winsound.Beep(200,500);hyperfocus=_B;print('hyperfocus disabled')
		else:winsound.Beep(350,500);hyperfocus=_A;print('hyperfocus enabled')
	if x.name=='=':winsound.Beep(460,500);delay_pixel+=2;print(C,delay_pixel)
	if x.name=='-':winsound.Beep(500,500);delay_pixel-=2;print(C,delay_pixel)
def main():
	import os
	if not os.path.exists(imgdir):os.mkdir(imgdir)
	keyboard.on_press(keyboard_callback);threading.Thread(target=keyboard.wait);print('starting');driver()
all_processes=psutil.process_iter()
for process in all_processes:
	try:
		process_name=process.name()
		if process_name=='python.exe':process.nice(psutil.HIGH_PRIORITY_CLASS);print('Python 进程优先级已调整为高')
	except(psutil.NoSuchProcess,psutil.AccessDenied,psutil.ZombieProcess):pass
if __name__=='__main__':main()
