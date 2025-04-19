package capture

import (
	"errors"

	"github.com/go-vgo/robotgo"
	"gocv.io/x/gocv"
)

// CaptureRegionLeft grabs the [x,y,w,h] rectangle on the
// left‑most monitor using RobotGo (more direct than GDI).
func CaptureRegionLeft(x, y, w, h int) (gocv.Mat, error) {
	// robotgo uses absolute desktop coords.
	bitmap := robotgo.CaptureScreen(x, y, w, h)
	if bitmap == nil {
		return gocv.Mat{}, errors.New("robotgo: failed to capture screen")
	}
	defer robotgo.FreeBitmap(bitmap)

	img := robotgo.ToImage(bitmap)
	if img == nil {
		return gocv.Mat{}, errors.New("robotgo: failed to convert bitmap to image")
	}

	mat, err := gocv.ImageToMatRGB(img)
	if err != nil {
		return gocv.Mat{}, err
	}
	return mat, nil
}
