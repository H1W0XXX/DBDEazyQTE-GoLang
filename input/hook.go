package input

import (
	"fmt"
	"os"

	hook "github.com/robotn/gohook"
)

var (
	Toggle     = true
	SpeedMode  = 0
	HyperFocus = false
)

func StartHook() {
	// 注册 Esc: 退出程序
	hook.Register(hook.KeyDown, []string{"esc"}, func(e hook.Event) {
		fmt.Println("退出程序")
		os.Exit(0)
	})
	// 注册 F1: 切换开关
	hook.Register(hook.KeyDown, []string{"f1"}, func(e hook.Event) {
		Toggle = !Toggle
		fmt.Println("toggle:", Toggle)
	})
	// 注册数字键 3/4/5/6
	hook.Register(hook.KeyDown, []string{"3"}, func(e hook.Event) {
		SpeedMode = 3

		fmt.Println("mode: repair")
	})
	hook.Register(hook.KeyDown, []string{"4"}, func(e hook.Event) {
		SpeedMode = 4
		fmt.Println("mode: heal")
	})
	hook.Register(hook.KeyDown, []string{"5"}, func(e hook.Event) {
		SpeedMode = 5
		fmt.Println("mode: wiggle")
	})
	hook.Register(hook.KeyDown, []string{"6"}, func(e hook.Event) {
		HyperFocus = !HyperFocus
		fmt.Println("hyperfocus:", HyperFocus)
	})

	// 启动监听，并在后台 goroutine 中处理事件
	go func() {
		s := hook.Start()
		<-hook.Process(s)
	}()
}
