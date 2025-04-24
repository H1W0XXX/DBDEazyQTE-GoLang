# DBD Easy QTE - Go 重写版

这是 [`En73r/DBDEazyQTE`](https://github.com/En73r/DBDEazyQTE) 项目的 **Go 语言重写版本**。



## 🔧 环境依赖

> 本项目使用 [GoCV](https://gocv.io) 调用 OpenCV 进行图像识别，因此需要 OpenCV 库环境。


### 🐧 基于 MSYS2 MINGW64 的安装建议：

```bash
pacman -Syu
pacman -S --needed mingw-w64-x86_64-gcc mingw-w64-x86_64-opencv mingw-w64-x86_64-pkg-config

export CGO_ENABLED=1
export PKG_CONFIG_PATH=/mingw64/lib/pkgconfig
export CGO_CPPFLAGS="$(pkg-config --cflags opencv4)"
export CGO_LDFLAGS="$(pkg-config --libs opencv4)"



go build -trimpath -ldflags="-s -w" -tags=dxgi,customenv -o goqte.exe