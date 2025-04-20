// main.go
// MINGW64
// go build -tags customenv,dxgi -o /z/go-qte.exe
// 本项目还原“固定速率模型”，并加上“+/-键调节延迟”功能。
// 只在外面 NewMat，一次分配，循环里用 CaptureRegionLeftInto 覆盖。

package main

import (
	"math"
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
	redThresh   = 180

	pressAndReleaseDelay = 0.003206 // 约 3.2 ms
	delayDegreeOffset    = 0.0      // 视你调试再填正负
)

func init() {
	// 提高系统定时器精度到 1ms
	syscall.NewLazyDLL("winmm.dll").NewProc("timeBeginPeriod").Call(1)
	// 提升进程优先级到 HIGH
	k32 := syscall.NewLazyDLL("kernel32.dll")
	h, _, _ := k32.NewProc("GetCurrentProcess").Call()
	k32.NewProc("SetPriorityClass").Call(h, uintptr(0x00000080))
}

func main() {
	// 启动按键钩子，默认开且模式为 Repair
	input.StartHook()
	input.Toggle = true
	input.SpeedMode = 3

	// 选最左显示器，算截图区域中心
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

	// **一次性**分配 Mat，循环内复用
	mat := gocv.NewMat()
	defer mat.Close()

	// 主循环 120 FPS
	ticker := time.NewTicker(time.Second / 120)
	defer ticker.Stop()

	for t0 := range ticker.C {
		if !input.Toggle {
			continue
		}

		// 截图到 mat（复用同一块内存）
		if err := capture.CaptureRegionLeftInto(&mat, baseX, baseY, crop, crop); err != nil {
			continue
		}

		// 先检测白框
		ptW, _, _, okW := imaging.FindSquare(mat)
		if !okW {
			continue
		}

		// 再检测红点
		ptR, _, okR := imaging.FindRed(mat, redThresh)
		if !okR {
			continue
		}

		// 计算从红点到白框的最短角度差
		degR := util.CalDegree(
			float64(ptR.X-crop/2),
			float64(ptR.Y-crop/2),
		)
		degW := util.CalDegree(
			float64(ptW.X-crop/2),
			float64(ptW.Y-crop/2),
		)
		delta := math.Mod(degW-degR+360.0, 360.0)

		// 选择固定速度
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
			speed *= 1.04
		}

		// 计算精准点击时刻，加上 +/- 键调节的偏移
		waitSec := delta / speed
		// 从 t0 开始加上预测时间，再减去硬件延迟，同时加上一个按度数的补偿
		clickTime := t0.
			Add(time.Duration(waitSec * float64(time.Second))).
			Add(-time.Duration(pressAndReleaseDelay * float64(time.Second))).
			Add(time.Duration((delayDegreeOffset / speed) * float64(time.Second)))

		// Busy‑wait 到时刻按空格
		util.SleepUntil(clickTime)
		util.SendSpace()
	}
}
