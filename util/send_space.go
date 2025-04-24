// util/send_space.go
package util

import (
	"log"
	"syscall"
	"time"
	"unsafe"
)

var (
	user32        = syscall.NewLazyDLL("user32.dll")
	procSendInput = user32.NewProc("SendInput")
)

const (
	INPUT_KEYBOARD    = 1
	KEYEVENTF_KEYDOWN = 0x0000
	KEYEVENTF_KEYUP   = 0x0002
	VK_SPACE          = 0x20
)

// KEYBDINPUT 对应 C 端 tagKEYBDINPUT
type KEYBDINPUT struct {
	wVk         uint16
	wScan       uint16
	dwFlags     uint32
	time        uint32
	dwExtraInfo uintptr // ULONG_PTR
}

// INPUT 对应 C 端 tagINPUT：
//
//	DWORD type;
//	union { MOUSEINPUT mi; KEYBDINPUT ki; };
//
// 我们只填 ki，然后 pad 到 32 字节 union 大小，保证 sizeof(INPUT)==40
type INPUT struct {
	Type uint32
	_    [4]byte // 4 字节填充，对齐到 8 字节边界
	Ki   KEYBDINPUT
	_    [8]byte // pad 到 32 字节 union
}

func SendSpace() {
	// 构造“按下”
	inp := INPUT{
		Type: INPUT_KEYBOARD,
		Ki: KEYBDINPUT{
			wVk:         VK_SPACE,
			wScan:       0,
			dwFlags:     KEYEVENTF_KEYDOWN,
			time:        0,
			dwExtraInfo: 0,
		},
	}

	// 调用 SendInput
	ret, _, err := procSendInput.Call(
		uintptr(1),
		uintptr(unsafe.Pointer(&inp)),
		uintptr(unsafe.Sizeof(inp)),
	)
	if ret == 0 {
		log.Println("SendInput keydown failed:", err)
	}

	// 等几毫秒，让系统处理“按下”
	time.Sleep(5 * time.Millisecond)

	// 再发送“抬起”
	inp.Ki.dwFlags = KEYEVENTF_KEYUP
	ret, _, err = procSendInput.Call(
		uintptr(1),
		uintptr(unsafe.Pointer(&inp)),
		uintptr(unsafe.Sizeof(inp)),
	)
	if ret == 0 {
		log.Println("SendInput keyup failed:", err)
	}
}
