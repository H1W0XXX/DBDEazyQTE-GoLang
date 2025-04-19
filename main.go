// main.go
// 本项目是对 En73r/DBDEazyQTE (https://github.com/En73r/DBDEazyQTE) 的重写。
package main

import (
	"fmt"
	"image"
	//"image/color"
	"math"
	//"path/filepath"
	"runtime"
	"syscall"
	"time"

	"github.com/kbinani/screenshot"
	"github.com/you/go-qte/capture"
	"github.com/you/go-qte/imaging"
	"github.com/you/go-qte/input"
	"github.com/you/go-qte/util"
	"gocv.io/x/gocv"
)

const (
	repairSpeed = 330.0
	healSpeed   = 300.0
	wiggleSpeed = 230.0
)

func dumpDisplays() { /* ... 保持不变 ... */ }

func init() {
	// timeBeginPeriod(1)
	syscall.NewLazyDLL("winmm.dll").NewProc("timeBeginPeriod").Call(1)
	// 优先级
	k32 := syscall.NewLazyDLL("kernel32.dll")
	h, _, _ := k32.NewProc("GetCurrentProcess").Call()
	const HIGH = 0x00000080
	k32.NewProc("SetPriorityClass").Call(h, HIGH)
	// 得到逻辑 CPU 数
	numCPU := runtime.NumCPU()
	// 只保留最高位那一颗
	// 比如 numCPU=8, mask = 1<<(8-1) = 0x80
	mask := uintptr(1 << (numCPU - 1))

	setAffinity := k32.NewProc("SetProcessAffinityMask")
	// 第一个参数是进程句柄，第二个参数是亲和性掩码
	setAffinity.Call(h, mask)

}

func dumpFrame(mat gocv.Mat, ptRed, ptWhite image.Point, tag string) { /* ... */ }

func main() {
	input.StartHook()
	input.SpeedMode = 3
	// 选最左显示器、算截图区域
	leftID, minX := 0, screenshot.GetDisplayBounds(0).Min.X
	for i := 1; i < screenshot.NumActiveDisplays(); i++ {
		b := screenshot.GetDisplayBounds(i)
		if b.Min.X < minX {
			minX, leftID = b.Min.X, i
		}
	}
	b := screenshot.GetDisplayBounds(leftID)
	const crop = 200
	baseX := b.Min.X + (b.Dx()-crop)/2
	baseY := b.Min.Y + (b.Dy()-crop)/2

	//baseY := b.Min.Y + (b.Dy()-crop)/2 - 20

	ticker := time.NewTicker(time.Second / 120)
	defer ticker.Stop()
	var focusLevel float64

	for t0 := range ticker.C {
		if !input.Toggle {
			continue
		}

		mat, err := capture.CaptureRegionLeft(baseX, baseY, crop, crop)
		if err != nil {
			continue
		}

		// 红点
		ptRed, _, ok := imaging.FindRed(mat, 180)
		if !ok {
			mat.Close()
			continue
		}
		// 白框
		ptWhite, _, _, ok := imaging.FindSquare(mat)
		if !ok {
			mat.Close()
			continue
		}

		// 计算角度差
		degRed := util.CalDegree(
			float64(ptRed.X-crop/2),
			float64(ptRed.Y-crop/2),
		)

		// ----- 新增：测第二帧角度，判断方向 -----
		time.Sleep(10 * time.Millisecond)
		mat2, err2 := capture.CaptureRegionLeft(baseX, baseY, crop, crop)
		if err2 != nil {
			mat.Close()
			continue
		}
		ptRed2, _, ok2 := imaging.FindRed(mat2, 180)
		mat2.Close()
		direction := 1
		if ok2 {
			deg2 := util.CalDegree(
				float64(ptRed2.X-crop/2),
				float64(ptRed2.Y-crop/2),
			)
			if math.Mod(deg2-degRed+360, 360) > 180 {
				direction = -1
			}
		}
		fmt.Printf("方向：%s\n", map[int]string{1: "顺时针", -1: "逆时针"}[direction])

		// 原来的角度差，用 direction 修正符号
		degWhite := util.CalDegree(
			float64(ptWhite.X-crop/2),
			float64(ptWhite.Y-crop/2),
		)
		delta := math.Mod(float64(direction)*(degWhite-degRed)+360.0, 360.0)

		// 选速度
		var speed float64
		switch input.SpeedMode {
		case 3:
			speed = repairSpeed
		case 4:
			speed = healSpeed
		case 5:
			speed = wiggleSpeed
		default:
			speed = wiggleSpeed
		}
		if input.HyperFocus {
			speed *= 1 + 0.04*focusLevel
		}

		waitSec := delta / speed
		clickTime := t0.Add(time.Duration(waitSec * float64(time.Second)))

		// —— 加入调试输出 ——
		//fmt.Printf("DEBUG: delta=%.2f°, speed=%.1f°/s, wait=%.3fs, clickTime=%s, now=%s\n",
		//	delta, speed, waitSec,
		//	clickTime.Format("15:04:05.000"), time.Now().Format("15:04:05.000"),
		//)

		util.SleepUntil(clickTime)

		//fmt.Println("DEBUG: woke up @", time.Now().Format("15:04:05.000"))
		//fmt.Println("DEBUG: calling SendSpace()")
		util.SendSpace()

		mat.Close()
	}
}
