"""电脑端中文图片清晰度提升工具。

运行方式::

    python image_clarity_desktop.py

该模块把图像处理核心函数与 Tkinter 界面分离，便于批量处理与自动化测试。
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DEFAULT_SUFFIX = "_清晰放大"
APP_NAME = "小鸭清晰放大器"
DUCK_YELLOW = "#FFD84D"
DUCK_ORANGE = "#F59E0B"
WATER_BLUE = "#7DD3FC"
WATER_DARK = "#0284C7"
CREAM = "#FFF7D6"


@dataclass(frozen=True)
class EnhanceSettings:
    """图片增强参数。"""

    scale: float = 2.0
    sharpness: float = 1.45
    contrast: float = 1.08
    text_protection: float = 0.72
    denoise: bool = True

    def validate(self) -> None:
        if not 1.0 <= self.scale <= 4.0:
            raise ValueError("放大倍数必须在 1.0 到 4.0 之间")
        if not 0.5 <= self.sharpness <= 3.0:
            raise ValueError("锐化强度必须在 0.5 到 3.0 之间")
        if not 0.5 <= self.contrast <= 2.0:
            raise ValueError("对比度必须在 0.5 到 2.0 之间")
        if not 0.0 <= self.text_protection <= 1.0:
            raise ValueError("字体保护强度必须在 0.0 到 1.0 之间")


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def output_path_for(source: Path, output_dir: Path, suffix: str = DEFAULT_SUFFIX) -> Path:
    """生成不会覆盖原文件的输出路径。"""

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{source.stem}{suffix}{source.suffix}"
    if not target.exists():
        return target

    index = 2
    while True:
        candidate = output_dir / f"{source.stem}{suffix}_{index}{source.suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def duck_x_for_progress(progress: float, width: int, duck_width: int = 58, padding: int = 8) -> int:
    """根据进度计算小鸭子在进度水池中的横向位置。"""

    clamped = min(max(progress, 0.0), 100.0)
    travel_width = max(width - duck_width - padding * 2, 0)
    return round(padding + travel_width * clamped / 100.0)


def _resize_dimensions(size: tuple[int, int], scale: float) -> tuple[int, int]:
    width, height = size
    return max(1, round(width * scale)), max(1, round(height * scale))


def enhance_image(image: Any, settings: EnhanceSettings) -> Any:
    """提升图片清晰度，并通过边缘蒙版减少文字边缘变形。

    处理思路：
    1. 使用高质量 LANCZOS 重采样放大；
    2. 只进行温和去噪，避免抹掉小字笔画；
    3. 用边缘检测生成文字/线条蒙版，对边缘区域做更克制的锐化；
    4. 合成后轻微提升对比度，让扫描件和截图文字更清楚。
    """

    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    settings.validate()
    source = ImageOps.exif_transpose(image)
    original_mode = source.mode

    if source.mode not in {"RGB", "RGBA"}:
        source = source.convert("RGBA" if "A" in source.getbands() else "RGB")

    new_size = _resize_dimensions(source.size, settings.scale)
    resampling = getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
    upscaled = source.resize(new_size, resampling)

    base = upscaled.filter(ImageFilter.MedianFilter(size=3)) if settings.denoise else upscaled
    normal_sharp = ImageEnhance.Sharpness(base).enhance(settings.sharpness)

    edge_mask = ImageOps.grayscale(upscaled).filter(ImageFilter.FIND_EDGES)
    edge_mask = edge_mask.filter(ImageFilter.GaussianBlur(radius=0.45))
    edge_mask = ImageEnhance.Contrast(edge_mask).enhance(2.2)
    edge_mask = ImageEnhance.Brightness(edge_mask).enhance(settings.text_protection)

    text_safe_sharpness = max(1.0, 1.0 + (settings.sharpness - 1.0) * 0.45)
    text_safe = ImageEnhance.Sharpness(upscaled).enhance(text_safe_sharpness)
    combined = Image.composite(text_safe, normal_sharp, edge_mask)
    combined = ImageEnhance.Contrast(combined).enhance(settings.contrast)

    if original_mode == "L":
        return combined.convert("L")
    if original_mode == "RGBA" and combined.mode != "RGBA":
        return combined.convert("RGBA")
    return combined


def process_image_file(source: Path, output_dir: Path, settings: EnhanceSettings) -> Path:
    """处理单张图片并返回生成文件路径。"""

    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"图片不存在: {source}")
    if not is_supported_image(source):
        raise ValueError(f"不支持的图片格式: {source.suffix}")

    from PIL import Image

    with Image.open(source) as image:
        enhanced = enhance_image(image, settings)
        target = output_path_for(source, output_dir)
        save_kwargs = {}
        if target.suffix.lower() in {".jpg", ".jpeg"}:
            enhanced = enhanced.convert("RGB")
            save_kwargs.update({"quality": 95, "subsampling": 0, "optimize": True})
        elif target.suffix.lower() == ".png":
            save_kwargs.update({"optimize": True})
        enhanced.save(target, **save_kwargs)
    return target


def process_many(
    sources: Sequence[Path],
    output_dir: Path,
    settings: EnhanceSettings,
    progress: Callable[[int, int, Path], None] | None = None,
) -> list[Path]:
    """批量处理图片。"""

    results: list[Path] = []
    total = len(sources)
    for index, source in enumerate(sources, start=1):
        target = process_image_file(source, output_dir, settings)
        results.append(target)
        if progress:
            progress(index, total, target)
    return results


class DuckProgressBar(ttk.Frame):
    """用正在游泳的小鸭子表示处理进度。"""

    def __init__(self, parent: tk.Widget, variable: tk.DoubleVar, width: int = 286, height: int = 78) -> None:
        super().__init__(parent)
        self.variable = variable
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(self, width=width, height=height, highlightthickness=0, bg=CREAM)
        self.canvas.pack(fill=tk.X, expand=True)
        self.variable.trace_add("write", self._redraw_from_var)
        self.canvas.bind("<Configure>", self._on_resize)
        self._redraw()

    def _on_resize(self, event: tk.Event) -> None:
        self.width = max(int(event.width), 1)
        self.height = max(int(event.height), 1)
        self._redraw()

    def _redraw_from_var(self, *_args: object) -> None:
        self._redraw()

    def _redraw(self) -> None:
        progress = min(max(float(self.variable.get()), 0.0), 100.0)
        width = max(self.width, 1)
        height = max(self.height, 1)
        water_top = max(36, height - 34)
        duck_x = duck_x_for_progress(progress, width)
        duck_y = max(8, water_top - 32)

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, width, height, fill=CREAM, outline=CREAM)
        self.canvas.create_rectangle(8, water_top, width - 8, height - 8, fill="#BAE6FD", outline=WATER_BLUE, width=2)

        filled = 8 + (width - 16) * progress / 100.0
        self.canvas.create_rectangle(8, water_top, filled, height - 8, fill=WATER_BLUE, outline="")
        for offset in range(-40, width + 40, 44):
            self.canvas.create_arc(offset, water_top - 9, offset + 40, water_top + 13, start=0, extent=180, outline=WATER_DARK, width=2)

        self._draw_duck(duck_x, duck_y)
        self.canvas.create_text(
            width / 2,
            height - 17,
            text=f"{progress:.0f}%  小鸭子正在游过去……",
            fill="#075985",
            font=("Microsoft YaHei UI", 10, "bold"),
        )

    def _draw_duck(self, x: int, y: int) -> None:
        self.canvas.create_oval(x + 9, y + 22, x + 53, y + 48, fill=DUCK_YELLOW, outline="#EAB308", width=2)
        self.canvas.create_oval(x + 30, y + 5, x + 56, y + 31, fill=DUCK_YELLOW, outline="#EAB308", width=2)
        self.canvas.create_polygon(x + 54, y + 16, x + 67, y + 21, x + 54, y + 26, fill=DUCK_ORANGE, outline="#D97706")
        self.canvas.create_oval(x + 46, y + 14, x + 50, y + 18, fill="#111827", outline="#111827")
        self.canvas.create_arc(x + 5, y + 27, x + 34, y + 53, start=20, extent=130, outline="#FBBF24", width=3)


class ImageClarityApp:
    """中文小鸭子风格桌面界面。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"{APP_NAME} - 图片清晰度提升工具")
        self.root.geometry("920x660")
        self.root.minsize(820, 600)
        self.root.configure(bg=CREAM)

        self.files: list[Path] = []
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "清晰图片输出"))
        self.scale = tk.DoubleVar(value=2.0)
        self.sharpness = tk.DoubleVar(value=1.45)
        self.contrast = tk.DoubleVar(value=1.08)
        self.text_protection = tk.DoubleVar(value=0.72)
        self.denoise = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="嘎嘎～请选择单张或多张图片，小鸭子会帮你放大变清晰。")
        self.progress_var = tk.DoubleVar(value=0)
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._configure_style()
        self._build_ui()
        self._poll_events()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Duck.TFrame", background=CREAM)
        style.configure("DuckCard.TLabelframe", background=CREAM, bordercolor="#FBBF24", relief="solid")
        style.configure("DuckCard.TLabelframe.Label", background=CREAM, foreground="#92400E", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Duck.TLabel", background=CREAM, foreground="#334155", font=("Microsoft YaHei UI", 10))
        style.configure("DuckTitle.TLabel", background=CREAM, foreground="#92400E", font=("Microsoft YaHei UI", 22, "bold"))
        style.configure("DuckSubTitle.TLabel", background=CREAM, foreground="#475569", font=("Microsoft YaHei UI", 10))
        style.configure("Duck.TButton", background="#FDE68A", foreground="#78350F", bordercolor="#F59E0B", focusthickness=0, font=("Microsoft YaHei UI", 10, "bold"), padding=8)
        style.map("Duck.TButton", background=[("active", "#FBBF24"), ("pressed", "#F59E0B")])
        style.configure("Duck.TCheckbutton", background=CREAM, foreground="#334155", font=("Microsoft YaHei UI", 10))
        style.configure("Duck.Horizontal.TScale", background=CREAM, troughcolor="#BAE6FD")

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=18, style="Duck.TFrame")
        main.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main, style="Duck.TFrame")
        header.pack(fill=tk.X)
        title = ttk.Label(header, text=f"🦆 {APP_NAME}", style="DuckTitle.TLabel")
        title.pack(anchor=tk.W)
        subtitle = ttk.Label(
            header,
            text="电脑端中文软件｜支持单张/多张上传｜小鸭子游到终点时，清晰图片就处理好啦。",
            style="DuckSubTitle.TLabel",
        )
        subtitle.pack(anchor=tk.W, pady=(4, 16))

        body = ttk.Frame(main, style="Duck.TFrame")
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(body, text="🖼 图片池", padding=12, style="DuckCard.TLabelframe")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        button_bar = ttk.Frame(left, style="Duck.TFrame")
        button_bar.pack(fill=tk.X)
        ttk.Button(button_bar, text="上传单张图片", command=self.add_single_file, style="Duck.TButton").pack(side=tk.LEFT)
        ttk.Button(button_bar, text="上传多张图片", command=self.add_multiple_files, style="Duck.TButton").pack(side=tk.LEFT, padx=8)
        ttk.Button(button_bar, text="清空列表", command=self.clear_files, style="Duck.TButton").pack(side=tk.LEFT)

        self.file_list = tk.Listbox(
            left,
            height=18,
            selectmode=tk.EXTENDED,
            bg="#FFFBEB",
            fg="#334155",
            selectbackground="#FBBF24",
            selectforeground="#111827",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#FCD34D",
            font=("Microsoft YaHei UI", 10),
        )
        self.file_list.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        right = ttk.LabelFrame(body, text="⚙️ 小鸭参数", padding=12, style="DuckCard.TLabelframe")
        right.pack(side=tk.RIGHT, fill=tk.Y)

        self._add_slider(right, "放大倍数", self.scale, 1.0, 4.0, "推荐 2.0；最高 4.0")
        self._add_slider(right, "清晰锐化", self.sharpness, 0.5, 3.0, "过高可能产生白边")
        self._add_slider(right, "文字保护", self.text_protection, 0.0, 1.0, "越高越保护字体边缘")
        self._add_slider(right, "对比度", self.contrast, 0.5, 2.0, "轻微提升更适合文字图")
        ttk.Checkbutton(right, text="温和去噪（推荐）", variable=self.denoise, style="Duck.TCheckbutton").pack(anchor=tk.W, pady=(6, 12))

        output_row = ttk.Frame(right, style="Duck.TFrame")
        output_row.pack(fill=tk.X, pady=(8, 4))
        ttk.Label(output_row, text="输出目录", style="Duck.TLabel").pack(anchor=tk.W)
        ttk.Entry(output_row, textvariable=self.output_dir, width=32).pack(side=tk.LEFT, fill=tk.X, expand=True, pady=(4, 0))
        ttk.Button(output_row, text="选择", command=self.choose_output_dir, style="Duck.TButton").pack(side=tk.LEFT, padx=(6, 0), pady=(4, 0))

        ttk.Button(right, text="🦆 开始提高清晰度", command=self.start_processing, style="Duck.TButton").pack(fill=tk.X, pady=(18, 8))
        self.duck_progress = DuckProgressBar(right, self.progress_var)
        self.duck_progress.pack(fill=tk.X)
        ttk.Label(right, textvariable=self.status, wraplength=282, foreground="#0F766E", background=CREAM, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))

        tips = ttk.LabelFrame(main, text="💡 使用建议", padding=10, style="DuckCard.TLabelframe")
        tips.pack(fill=tk.X, pady=(14, 0))
        ttk.Label(
            tips,
            text="文字截图/票据建议：放大 2x、清晰锐化 1.3-1.6、文字保护 0.7 以上。照片建议降低文字保护并保留温和去噪。",
            style="Duck.TLabel",
        ).pack(anchor=tk.W)

    def _add_slider(self, parent: ttk.Frame, label: str, variable: tk.DoubleVar, start: float, end: float, hint: str) -> None:
        row = ttk.Frame(parent, style="Duck.TFrame")
        row.pack(fill=tk.X, pady=(0, 10))
        header = ttk.Frame(row, style="Duck.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text=label, style="Duck.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, textvariable=variable, style="Duck.TLabel").pack(side=tk.RIGHT)
        ttk.Scale(row, from_=start, to=end, variable=variable, style="Duck.Horizontal.TScale").pack(fill=tk.X, pady=(4, 0))
        ttk.Label(row, text=hint, foreground="#64748B", background=CREAM, font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)

    def add_single_file(self) -> None:
        filetypes = [("图片文件", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"), ("所有文件", "*.*")]
        selected = filedialog.askopenfilename(title="选择图片", filetypes=filetypes)
        if selected:
            self._add_files([Path(selected)])

    def add_multiple_files(self) -> None:
        filetypes = [("图片文件", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"), ("所有文件", "*.*")]
        selected = filedialog.askopenfilenames(title="选择多张图片", filetypes=filetypes)
        self._add_files([Path(item) for item in selected])

    def _add_files(self, paths: Iterable[Path]) -> None:
        added = 0
        existing = set(self.files)
        for path in paths:
            if path not in existing and is_supported_image(path):
                self.files.append(path)
                self.file_list.insert(tk.END, f"🦆 {path}")
                existing.add(path)
                added += 1
        self.status.set(f"嘎嘎～已添加 {added} 张图片，共 {len(self.files)} 张。" if added else "没有添加新的受支持图片。")

    def clear_files(self) -> None:
        self.files.clear()
        self.file_list.delete(0, tk.END)
        self.progress_var.set(0)
        self.status.set("图片池已清空，小鸭子回到起点。")

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择输出目录")
        if selected:
            self.output_dir.set(selected)

    def _settings(self) -> EnhanceSettings:
        return EnhanceSettings(
            scale=round(self.scale.get(), 2),
            sharpness=round(self.sharpness.get(), 2),
            contrast=round(self.contrast.get(), 2),
            text_protection=round(self.text_protection.get(), 2),
            denoise=self.denoise.get(),
        )

    def start_processing(self) -> None:
        if not self.files:
            messagebox.showwarning("提示", "请先上传单张或多张图片。")
            return

        settings = self._settings()
        settings.validate()
        output_dir = Path(self.output_dir.get()).expanduser()
        self.progress_var.set(0)
        self.status.set("小鸭子开始游泳处理图片，请稍候……")

        worker = threading.Thread(target=self._process_worker, args=(list(self.files), output_dir, settings), daemon=True)
        worker.start()

    def _process_worker(self, files: list[Path], output_dir: Path, settings: EnhanceSettings) -> None:
        def report(index: int, total: int, target: Path) -> None:
            self.event_queue.put(("progress", (index, total, target)))

        try:
            results = process_many(files, output_dir, settings, report)
            self.event_queue.put(("done", results))
        except Exception as exc:
            self.event_queue.put(("error", str(exc)))

    def _poll_events(self) -> None:
        while not self.event_queue.empty():
            event, payload = self.event_queue.get_nowait()
            if event == "progress":
                index, total, target = payload
                self.progress_var.set(index / total * 100)
                self.status.set(f"小鸭子已游过 {index}/{total}: {Path(target).name}")
            elif event == "done":
                results = payload
                self.progress_var.set(100)
                self.status.set(f"嘎嘎～处理完成，共生成 {len(results)} 张清晰图片。")
                messagebox.showinfo("完成", f"已生成 {len(results)} 张图片。\n输出目录：{self.output_dir.get()}")
            elif event == "error":
                self.status.set("处理失败，小鸭子卡住了，请检查图片或输出目录。")
                messagebox.showerror("处理失败", str(payload))
        self.root.after(120, self._poll_events)


def main() -> None:
    root = tk.Tk()
    ImageClarityApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
