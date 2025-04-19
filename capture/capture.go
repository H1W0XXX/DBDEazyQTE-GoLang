//go:build windows && dxgi
// +build windows,dxgi

package capture

import (
	"image"

	"github.com/kbinani/screenshot"
	"gocv.io/x/gocv"
)

// CaptureRegionLeftInto 用 DXGI 通道截图到 dst。记得用 go build -tags=dxgi 才会编译进来。
func CaptureRegionLeftInto(dst *gocv.Mat, x, y, w, h int) error {
	// 找最左屏
	leftID, minX := 0, screenshot.GetDisplayBounds(0).Min.X
	for i := 1; i < screenshot.NumActiveDisplays(); i++ {
		b := screenshot.GetDisplayBounds(i)
		if b.Min.X < minX {
			minX, leftID = b.Min.X, i
		}
	}
	bounds := screenshot.GetDisplayBounds(leftID)
	abs := image.Rect(
		bounds.Min.X+x,
		bounds.Min.Y+y,
		bounds.Min.X+x+w,
		bounds.Min.Y+y+h,
	)

	// 下面这一行在加了 dxgi tag 后会走 DXGI duplication
	img, err := screenshot.CaptureRect(abs)
	if err != nil {
		return err
	}
	src, err := gocv.ImageToMatRGB(img)
	if err != nil {
		return err
	}
	defer src.Close()

	src.CopyTo(dst)
	return nil
}
