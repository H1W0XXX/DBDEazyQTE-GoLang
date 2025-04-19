package imaging

import (
	"image"
	"math"

	"gocv.io/x/gocv"
)

// FindThickestPoint performs a distance transform on a binary mask and returns the farthest point and its radius.
func FindThickestPoint(bin gocv.Mat) (pt image.Point, radius int) {
	dist := gocv.NewMat()
	labels := gocv.NewMat()
	defer dist.Close()
	defer labels.Close()

	// DistanceTransform(src, dst, labels, distType, maskSize, labelType)
	// Use DIST_C, 3x3 mask, pixel-based labels.
	gocv.DistanceTransform(
		bin, &dist, &labels,
		gocv.DistC,
		3,
		0,
	)

	_, maxVal, _, maxLoc := gocv.MinMaxLoc(dist)
	return maxLoc, int(maxVal)
}

// FindRed uses a single-step BGR InRange to detect red pixels, then finds the thickest point as the red center.
func FindRed(src gocv.Mat, redThresh uint8) (pt image.Point, radius int, ok bool) {
	mask := gocv.NewMat()
	defer mask.Close()

	// In BGR space: B<20, G<20, R>redThresh
	lower := gocv.NewScalar(0, 0, float64(redThresh), 0)
	upper := gocv.NewScalar(20, 20, 255, 0)
	gocv.InRangeWithScalar(src, lower, upper, &mask)

	if gocv.CountNonZero(mask) == 0 {
		return image.Point{}, 0, false
	}

	pt, radius = FindThickestPoint(mask)
	if radius < 1 {
		return image.Point{}, 0, false
	}
	return pt, radius, true
}

// FindSquare detects a white square by thresholding for pure white and returns its center and edge points.
func FindSquare(src gocv.Mat) (newPt, prePt, postPt image.Point, ok bool) {
	h, w := src.Rows(), src.Cols()
	mask := gocv.NewMat()
	defer mask.Close()

	// Threshold for pure white (255,255,255)
	lower := gocv.NewScalar(255, 255, 255, 0)
	upper := gocv.NewScalar(255, 255, 255, 0)
	gocv.InRangeWithScalar(src, lower, upper, &mask)
	if gocv.CountNonZero(mask) == 0 {
		return image.Point{}, image.Point{}, image.Point{}, false
	}

	bin := gocv.NewMat()
	defer bin.Close()
	gocv.Threshold(mask, &bin, 1, 255, gocv.ThresholdBinary)

	center, rad := FindThickestPoint(bin)
	if rad < 1 {
		return image.Point{}, image.Point{}, image.Point{}, false
	}

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
