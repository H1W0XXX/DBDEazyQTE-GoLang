// imaging/processing.go
package imaging

import (
	"image"
	"image/color"
	"math"

	"gocv.io/x/gocv"
)

// Init initializes the imaging package. Currently a no-op.
func Init(_ int) {
	// no-op, accepts an integer for compatibility with main
}

// findThickestPoint performs a distance transform on a binary 8‑bit mask
// and returns the farthest point and its radius.
func findThickestPoint(bin gocv.Mat) (pt image.Point, radius int) {
	// Guard: must be non-empty, 8‑bit single channel
	if bin.Empty() || bin.Type() != gocv.MatTypeCV8U {
		return image.Point{}, 0
	}

	dist := gocv.NewMat()
	labels := gocv.NewMat()
	defer dist.Close()
	defer labels.Close()

	// DistanceTransform(src, dst, labels, distType, maskSize, labelType)
	gocv.DistanceTransform(bin, &dist, &labels, gocv.DistC, 3, 0)

	_, maxVal, _, maxLoc := gocv.MinMaxLoc(dist)
	return maxLoc, int(maxVal)
}

// FindRed thresholds BGR for red pixels, applies a circular mask, and finds the thickest point.
// Returns center point, radius, and ok=true if found.
func FindRed(src gocv.Mat, redThresh uint8) (pt image.Point, radius int, ok bool) {
	// 1) 拆通道
	chans := gocv.Split(src)
	defer func() {
		for _, m := range chans {
			m.Close()
		}
	}()
	b, g, r := chans[0], chans[1], chans[2]

	// 2) 分别阈值
	rMask := gocv.NewMat()
	defer rMask.Close()
	gocv.Threshold(r, &rMask, float32(redThresh), 255, gocv.ThresholdBinary)

	gMask := gocv.NewMat()
	defer gMask.Close()
	gocv.Threshold(g, &gMask, 20, 255, gocv.ThresholdBinaryInv)

	bMask := gocv.NewMat()
	defer bMask.Close()
	gocv.Threshold(b, &bMask, 20, 255, gocv.ThresholdBinaryInv)

	// 3) 合并三张掩码
	mask := gocv.NewMat()
	defer mask.Close()
	gocv.BitwiseAnd(rMask, gMask, &mask)
	gocv.BitwiseAnd(mask, bMask, &mask)

	// 4) 圆形区域掩码
	h, w := mask.Rows(), mask.Cols()
	circle := gocv.NewMatWithSize(h, w, gocv.MatTypeCV8U)
	defer circle.Close()
	// 在中心画个半径 h/2 的白色实心圆
	gocv.Circle(&circle, image.Pt(w/2, h/2), h/2, color.RGBA{255, 255, 255, 0}, -1)
	gocv.BitwiseAnd(mask, circle, &mask)

	// 5) 如果没有红点，直接返回
	if mask.Empty() || gocv.CountNonZero(mask) == 0 {
		return image.Point{}, 0, false
	}

	// 6) 距离变换找到最粗红点
	pt, radius = findThickestPoint(mask)
	if radius < 1 {
		return image.Point{}, 0, false
	}
	return pt, radius, true
}

// FindSquare detects pure-white pixels, finds the thickest cluster, and returns
// the mid-point between its two extreme edge points.
func FindSquare(src gocv.Mat) (newPt, prePt, postPt image.Point, ok bool) {
	h, w := src.Rows(), src.Cols()
	mask := gocv.NewMat()
	defer mask.Close()

	// Threshold for pure white (255,255,255)
	lower := gocv.NewScalar(255, 255, 255, 0)
	upper := gocv.NewScalar(255, 255, 255, 0)
	gocv.InRangeWithScalar(src, lower, upper, &mask)
	if mask.Empty() || gocv.CountNonZero(mask) == 0 {
		return image.Point{}, image.Point{}, image.Point{}, false
	}

	// Binary mask → distance transform
	bin := gocv.NewMat()
	defer bin.Close()
	gocv.Threshold(mask, &bin, 1, 255, gocv.ThresholdBinary)

	center, rad := findThickestPoint(bin)
	if rad < 1 {
		return image.Point{}, image.Point{}, image.Point{}, false
	}

	// Compute extreme points along the radius
	dx := float64(center.X - w/2)
	dy := float64(center.Y - h/2)
	angle := math.Atan2(dy, dx) + math.Pi
	sin, cos := math.Sin(angle), math.Cos(angle)

	prePt = image.Pt(
		int(math.Round(float64(center.X)-sin*float64(rad))),
		int(math.Round(float64(center.Y)-cos*float64(rad))),
	)
	postPt = image.Pt(
		int(math.Round(float64(center.X)+sin*float64(rad))),
		int(math.Round(float64(center.Y)+cos*float64(rad))),
	)
	newPt = image.Pt((prePt.X+postPt.X)/2, (prePt.Y+postPt.Y)/2)
	return newPt, prePt, postPt, true
}
