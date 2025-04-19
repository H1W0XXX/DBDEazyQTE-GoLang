package util

import (
	"math"
	"syscall"
	"time"
)

// 调高定时器精度
func init() {
	dll := syscall.NewLazyDLL("winmm.dll")
	proc := dll.NewProc("timeBeginPeriod")
	proc.Call(uintptr(1))
}

// SleepUntil 忙等到指定时间点
func SleepUntil(ts time.Time) {
	for {
		now := time.Now()
		if !now.Before(ts) {
			return
		}
	}
}

// CalDegree 计算 (x,y) 相对 (-1,0) 的顺时针角度
func CalDegree(x, y float64) float64 {
	deg := (math.Atan2(y, x) + math.Pi) * 180.0 / math.Pi
	if deg >= 360 {
		return deg - 360
	}
	return deg
}
