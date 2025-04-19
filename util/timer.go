// util/timer.go
package util

import (
	"math"
	"syscall"
	"time"
	"unsafe"
)

// 把 kernel32.dll 握在手里
var (
	modkernel32              = syscall.NewLazyDLL("kernel32.dll")
	procTimeBeginPeriod      = modkernel32.NewProc("timeBeginPeriod")
	procCreateWaitableTimerW = modkernel32.NewProc("CreateWaitableTimerW")
	procSetWaitableTimer     = modkernel32.NewProc("SetWaitableTimer")
	procWaitForSingleObject  = modkernel32.NewProc("WaitForSingleObject")
	procCloseHandle          = modkernel32.NewProc("CloseHandle")
)

func init() {
	// 提高系统定时器精度到 1ms
	// DWORD timeBeginPeriod(UINT uPeriod);
	procTimeBeginPeriod.Call(uintptr(1))
}

// SleepUntil 用 Win32 高精度 WaitableTimer 等待到 ts
func SleepUntil(ts time.Time) {
	// 计算相对时间差
	diff := ts.Sub(time.Now())
	if diff <= 0 {
		return
	}

	// 创建一个一次性、手动重置的定时器
	// HANDLE CreateWaitableTimerW(LPSECURITY_ATTRIBUTES, BOOL bManualReset, LPCWSTR lpTimerName);
	hTimer, _, _ := procCreateWaitableTimerW.Call(0, 1, 0)
	if hTimer == 0 {
		return
	}
	defer procCloseHandle.Call(hTimer)

	// Windows 要求：dueTime 以 100ns 为单位，
	// 负值表示“relative to current time”
	// e.g. -5_000_000 表示 0.5 秒后触发
	dueTime := -diff.Nanoseconds() / 100

	// BOOL SetWaitableTimer(
	//   HANDLE hTimer,
	//   const LARGE_INTEGER *pDueTime,
	//   LONG lPeriod,               // 周期(ms)，0=一次性
	//   PTIMERAPCROUTINE,
	//   LPVOID,
	//   BOOL fResume
	// );
	procSetWaitableTimer.Call(
		hTimer,
		uintptr(unsafe.Pointer(&dueTime)),
		0, // 一次性
		0,
		0,
		0,
	)

	// DWORD WaitForSingleObject(HANDLE hHandle, DWORD dwMilliseconds);
	// INFINITE = 0xFFFFFFFF
	procWaitForSingleObject.Call(hTimer, 0xFFFFFFFF)
}

// CalDegree 保持不变…
func CalDegree(x, y float64) float64 {
	deg := (math.Atan2(y, x) + math.Pi) * 180.0 / math.Pi
	if deg >= 360 {
		return deg - 360
	}
	return deg
}
