// imaging/imaging.go
//
// 说明：
//  1. 只在 Init 时分配中间 Mat，后续帧全部复用，避免 GC/Cgo 抖动；
//  2. FindRed 直接 InRange + 圆形掩码，一步得到最终二值图；
//  3. FindSquare 只阈值一次，再 DistanceTransform；
//  4. DistanceTransform 只要 dist，不再申请 labels；
//  5. 依赖 gocv v0.32+。
package imaging

import (
	//"errors"
	"image"
	"image/color"
	"math"
	"sync"

	"gocv.io/x/gocv"
)

var (
	once         sync.Once
	circleMask   gocv.Mat // 截图尺寸固定后生成
	tmpMask      gocv.Mat // 所有中间单通道图在此复用
	tmpDist      gocv.Mat // DistanceTransform 输出
	cropH, cropW int

	inited bool
)

// Init 在程序启动后、第一次截图前调用。
// crop 为你的截图框宽高（一般正方形 200×200 / 250×250 …）。
func Init(crop int) {
	once.Do(func() {
		cropH, cropW = crop, crop

		// 圆形掩码：用来限制红点搜索范围
		circleMask = gocv.NewMatWithSize(cropH, cropW, gocv.MatTypeCV8U)
		gocv.Circle(
			&circleMask,
			image.Pt(cropW/2, cropH/2),
			cropH/2,
			color.RGBA{255, 255, 255, 0}, // ←★ 这里改成 RGBA
			-1,
		)

		// 复用的临时 Mat
		tmpMask = gocv.NewMatWithSize(cropH, cropW, gocv.MatTypeCV8U)
		tmpDist = gocv.NewMatWithSize(cropH, cropW, gocv.MatTypeCV32F)

		inited = true
	})
}

// ------- 公共工具 -------

func colorScalar(v float64) gocv.Scalar { return gocv.NewScalar(v, v, v, 0) }

// findThickestPoint: 在 tmpDist 上取 maxLoc
func findThickestPoint(bin *gocv.Mat) (pt image.Point, radius int) {
	gocv.DistanceTransform(*bin, &tmpDist, nil,
		gocv.DistC, 3, 0)
	_, maxVal, _, maxLoc := gocv.MinMaxLoc(tmpDist)
	return maxLoc, int(maxVal)
}

// ------- API 1: FindRed -------
// redThresh 一般用 180
func FindRed(src gocv.Mat, redThresh uint8) (image.Point, int, bool) {
	if !inited {
		panic("imaging.Init(...) 未调用")
	}
	// 1) 直接 InRange 得到红色区域
	lower := gocv.NewScalar(0, 0, float64(redThresh), 0)
	upper := gocv.NewScalar(20, 20, 255, 0)
	gocv.InRangeWithScalar(src, lower, upper, &tmpMask)

	// 2) 与圆形掩码相交
	gocv.BitwiseAnd(tmpMask, circleMask, &tmpMask)

	if gocv.CountNonZero(tmpMask) == 0 {
		return image.Point{}, 0, false
	}
	pt, r := findThickestPoint(&tmpMask)
	if r < 1 {
		return image.Point{}, 0, false
	}
	return pt, r, true
}

// ------- API 2: FindSquare -------
// 返回：白块圆心、前缘点、后缘点
func FindSquare(src gocv.Mat) (image.Point, image.Point, image.Point, bool) {
	if !inited {
		panic("imaging.Init(...) 未调用")
	}

	// 1) 阈值纯白
	gocv.InRangeWithScalar(src, colorScalar(255), colorScalar(255), &tmpMask)
	if gocv.CountNonZero(tmpMask) == 0 {
		return image.Point{}, image.Point{}, image.Point{}, false
	}

	// 2) DistanceTransform
	center, rad := findThickestPoint(&tmpMask)
	if rad < 1 {
		return image.Point{}, image.Point{}, image.Point{}, false
	}

	// 3) 计算 pre / post
	dx := float64(center.X - cropW/2)
	dy := float64(center.Y - cropH/2)
	angle := math.Atan2(dy, dx) + math.Pi
	sin, cos := math.Sin(angle), math.Cos(angle)

	pre := image.Pt(
		int(math.Round(float64(center.X)-sin*float64(rad))),
		int(math.Round(float64(center.Y)-cos*float64(rad))),
	)
	post := image.Pt(
		int(math.Round(float64(center.X)+sin*float64(rad))),
		int(math.Round(float64(center.Y)+cos*float64(rad))),
	)
	mid := image.Pt((pre.X+post.X)/2, (pre.Y+post.Y)/2)
	return mid, pre, post, true
}

// ------- 资源释放，可选 -------

func Close() {
	if !inited {
		return
	}
	circleMask.Close()
	tmpMask.Close()
	tmpDist.Close()
	inited = false
}
