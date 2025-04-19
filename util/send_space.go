// util/send_space.go
package util

import (
	"log"
	"syscall"
	"time"
	//"unsafe"
)

var (
	user32         = syscall.NewLazyDLL("user32.dll")
	procKeybdEvent = user32.NewProc("keybd_event")
)

const (
	// 虚拟键码
	VK_SPACE = 0x20
	// keybd_event 标志
	KEYEVENTF_KEYDOWN = 0x0000
	KEYEVENTF_KEYUP   = 0x0002
)

// SleepUntil 会一直忙等待直到目标时刻到来
//func SleepUntil(t time.Time) {
//	for {
//		if now := time.Now(); !now.Before(t) {
//			return
//		}
//	}
//}

// SendSpace 通过 Win32 keybd_event 模拟一次 “空格” 按下和松开
func SendSpace() {
	// 按下
	_, _, err := procKeybdEvent.Call(
		uintptr(VK_SPACE),
		uintptr(0),
		uintptr(KEYEVENTF_KEYDOWN),
		uintptr(0),
	)
	if err != syscall.Errno(0) {
		log.Println("SendSpace keydown error:", err)
	}
	// 保证按下被系统处理
	time.Sleep(10 * time.Millisecond)
	// 松开
	_, _, err = procKeybdEvent.Call(
		uintptr(VK_SPACE),
		uintptr(0),
		uintptr(KEYEVENTF_KEYUP),
		uintptr(0),
	)
	if err != syscall.Errno(0) {
		log.Println("SendSpace keyup error:", err)
	}
}
