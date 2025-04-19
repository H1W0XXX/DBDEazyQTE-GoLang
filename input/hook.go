package input

import (
	"fmt"
	"os"
	"time"

	hook "github.com/robotn/gohook"
)

var (
	Toggle      = true
	SpeedMode   = 3 // 3=repair,4=heal,5=wiggle
	HyperFocus  = false
	DelayOffset = -time.Millisecond // 全局点击时间偏移
)

// StartHook 注册按键钩子
func StartHook() {
	// Esc：退出
	hook.Register(hook.KeyDown, []string{"esc"}, func(e hook.Event) {
		fmt.Println("退出程序")
		os.Exit(0)
	})
	// F1：开关
	hook.Register(hook.KeyDown, []string{"f1"}, func(e hook.Event) {
		Toggle = !Toggle
		fmt.Println("Toggle:", Toggle)
	})
	// 模式 3/4/5/6
	hook.Register(hook.KeyDown, []string{"3"}, func(e hook.Event) {
		SpeedMode = 3
		fmt.Println("Mode: repair")
	})
	hook.Register(hook.KeyDown, []string{"4"}, func(e hook.Event) {
		SpeedMode = 4
		fmt.Println("Mode: heal")
	})
	hook.Register(hook.KeyDown, []string{"5"}, func(e hook.Event) {
		SpeedMode = 5
		fmt.Println("Mode: wiggle")
	})
	hook.Register(hook.KeyDown, []string{"6"}, func(e hook.Event) {
		HyperFocus = !HyperFocus
		fmt.Println("HyperFocus:", HyperFocus)
	})
	// 加号：增加延迟 1ms
	hook.Register(hook.KeyDown, []string{"+"}, func(e hook.Event) {
		DelayOffset += time.Millisecond
		fmt.Printf("DelayOffset: %+dms\n", DelayOffset.Milliseconds())
	})
	// 减号：减少延迟 1ms
	hook.Register(hook.KeyDown, []string{"-"}, func(e hook.Event) {
		DelayOffset -= time.Millisecond
		fmt.Printf("DelayOffset: %+dms\n", DelayOffset.Milliseconds())
	})
	// 启动监听
	go func() {
		s := hook.Start()
		<-hook.Process(s)
	}()
}
