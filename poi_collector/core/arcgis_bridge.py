"""ArcGIS 桥接：检测安装、启动并加载数据、写入指定工程文件。

本模块不依赖 arcpy——它只用标准库检测本机 ArcGIS 安装位置，并通过
操作系统 / 调用 ArcGIS 自带的 Python 来完成操作。这样我们的 PySide6 工具
（自带 Python 运行时）无需安装 ArcGIS 即可使用。

按钮 A（启动并加载数据）：用 os.startfile 让 Windows 以默认程序（ArcGIS）打开
    shapefile，相当于"双击文件"。若已关联 ArcGIS，数据会直接进入地图。
按钮 B（写入工程文件）：调用 ArcGIS 自带的 python.exe 运行内嵌 arcpy 脚本，
    将 shapefile 图层 addLayer 进指定的 .aprx(Pro) / .mxd(ArcMap) 并保存。

注意：按钮 B 要求 ArcGIS 已安装且其 arcpy 可被外部调用（Pro 需先登录一次或
离线授权）。若工程正被 ArcGIS 打开，写入后需要重开工程才能看到新图层。
"""
import os
import subprocess
import sys
import tempfile

# Windows 下隐藏子进程控制台窗口（避免"不断弹出命令行"）
try:
    CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
except Exception:
    CREATE_NO_WINDOW = 0x08000000

# ArcGIS Pro 安装根目录（标准路径）
_PRO_ROOT = r"C:\Program Files\ArcGIS\Pro"
# ArcMap 常见版本（从高到低探测）
_ARCMAP_VERS = [
    "10.9.1", "10.9", "10.8.2", "10.8.1", "10.8", "10.7",
    "10.6.1", "10.6", "10.5", "10.4", "10.3", "10.2",
]
# 额外搜索盘符（默认 C/D，可按需扩展）
_SEARCH_DRIVES = ["C", "D", "E", "F", "G"]
# 注册表关键路径（优先查询，最可靠）
_PRO_REG_PATHS = [
    (r"SOFTWARE\ESRI\ArcGIS Pro", "InstallDir"),          # 64 位视图
    (r"SOFTWARE\WOW6432Node\ESRI\ArcGIS Pro", "InstallDir"),
]
_ARCMAP_REG_ROOTS = [
    r"SOFTWARE\ESRI\Desktop10.9.1",
    r"SOFTWARE\ESRI\Desktop10.9",
    r"SOFTWARE\ESRI\Desktop10.8.2",
    r"SOFTWARE\ESRI\Desktop10.8.1",
    r"SOFTWARE\ESRI\Desktop10.8",
    r"SOFTWARE\ESRI\Desktop10.7",
    r"SOFTWARE\ESRI\Desktop10.6.1",
    r"SOFTWARE\ESRI\Desktop10.6",
    r"SOFTWARE\ESRI\Desktop10.5",
    r"SOFTWARE\ESRI\Desktop10.4",
    r"SOFTWARE\ESRI\Desktop10.3",
    r"SOFTWARE\ESRI\Desktop10.2",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.9.1",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.9",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.8.2",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.8.1",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.8",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.7",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.6.1",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.6",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.5",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.4",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.3",
    r"SOFTWARE\WOW6432Node\ESRI\Desktop10.2",
]
_ARCMAP_REG_VALUE = "InstallDir"


def _iter_drives():
    """返回本机所有存在的盘符根路径。"""
    drives = []
    for d in _SEARCH_DRIVES:
        root = f"{d}:\\"
        if os.path.exists(root):
            drives.append(root)
    return drives


def _read_reg_value(key_path, value_name):
    """从 Windows 注册表读取字符串值；失败返回 None。使用 reg 命令行（兼容性最好）。"""
    try:
        proc = subprocess.run(
            ["reg", "query", key_path, "/v", value_name],
            capture_output=True, text=True, timeout=10,
            encoding="gbk", errors="ignore",
            creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode != 0:
            return None
        # 解析 "InstallDir    REG_SZ    C:\ArcGIS\Pro\"
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith(value_name):
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    return parts[2].strip()
    except Exception:
        return None
    return None


def _where_search(filename, max_drives=("C", "D", "E")):
    for drv in max_drives:
        root = f"{drv}:\\"
        if not os.path.exists(root):
            continue
        try:
            proc = subprocess.run(
                ["where", "/r", root, filename],
                capture_output=True, text=True, timeout=30,
                encoding="gbk", errors="ignore",
                creationflags=CREATE_NO_WINDOW,
            )
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line and os.path.exists(line):
                    return line
        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue
    return None


def is_pro_running():
    """检测 ArcGIS Pro 是否正在运行（进程级）。用于导入前友好提示。

    注意：只能判断 Pro 是否开着，无法跨进程可靠得知"当前打开的是哪个工程"
    （Pro 工程状态存于专有内存/二进制，非标准注册表项）。因此本工具不试图
    自动填入"当前工程"，而是靠 recent_projects 的最近列表 + 默认目录猜测。
    """
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq ArcGISPro.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
            encoding="gbk", errors="ignore",
            creationflags=CREATE_NO_WINDOW,
        )
        return "ArcGISPro.exe" in proc.stdout
    except Exception:
        return False


def detect_arcgis():
    """检测本机已安装的 ArcGIS，返回列表：[{
        "name": 显示名, "type": "pro"/"desktop", "exe": 主程序路径, "python": arcpy 解释器
    }, ...]

    检测优先级（开源场景鲁棒性）：
        1) 注册表查询（最可靠，官方安装会写 InstallDir）
        2) 多盘符 + 标准/扁平路径扫描（覆盖自定义安装）
        3) `where` 全盘搜索（兜底，仅在前两层失败时触发，较慢）
    """
    installs = []

    # ---- 1) ArcGIS Pro ----
    pro_base = None
    # 1a) 注册表
    for key_path, val in _PRO_REG_PATHS:
        reg_dir = _read_reg_value(key_path, val)
        if reg_dir and os.path.exists(reg_dir):
            pro_base = reg_dir
            break
    # 1b) 路径扫描（多盘 + 扁平）
    if not pro_base:
        for drv in _iter_drives():
            cands = [
                os.path.join(drv, "ArcGIS", "Pro"),
                os.path.join(drv, "Program Files", "ArcGIS", "Pro"),
                os.path.join(drv, "Program Files (x86)", "ArcGIS", "Pro"),
                os.path.join(drv, "ArcGISPRO"),
                os.path.join(drv, "ArcGIS Pro"),
                os.path.join(drv, "Program Files", "ArcGISPRO"),
                os.path.join(drv, "Program Files (x86)", "ArcGISPRO"),
            ]
            for c in cands:
                if os.path.exists(os.path.join(c, "bin", "ArcGISPro.exe")):
                    pro_base = c
                    break
            if pro_base:
                break
    # 1c) where 兜底
    if not pro_base:
        hit = _where_search("ArcGISPro.exe")
        if hit:
            pro_base = os.path.dirname(os.path.dirname(hit))  # ...\bin\ArcGISPro.exe -> root
    if pro_base:
        pro_exe = os.path.join(pro_base, "bin", "ArcGISPro.exe")
        pro_py = None
        for c in [
            os.path.join(pro_base, "bin", "Python", "envs", "arcgispro-py3", "python.exe"),
            os.path.join(pro_base, "bin", "Python", "python.exe"),
        ]:
            if os.path.exists(c):
                pro_py = c
                break
        installs.append({
            "name": "ArcGIS Pro",
            "type": "pro",
            "exe": pro_exe if os.path.exists(pro_exe) else None,
            "python": pro_py,
        })

    # ---- 2) ArcMap (Desktop) ----
    arcmap_done = False
    for ver in _ARCMAP_VERS:
        if arcmap_done:
            break
        found = False
        # 2a) 路径扫描优先（能拿到真实安装版本号）
        for drv in _iter_drives():
            bases = [
                os.path.join(drv, "ArcGIS", f"Desktop{ver}"),
                os.path.join(drv, "Program Files (x86)", "ArcGIS", f"Desktop{ver}"),
                os.path.join(drv, "Program Files", "ArcGIS", f"Desktop{ver}"),
            ]
            for base in bases:
                arc_exe = os.path.join(base, "bin", "arcmap.exe")
                if os.path.exists(arc_exe):
                    installs.append({
                        "name": f"ArcMap {ver}",
                        "type": "desktop",
                        "exe": arc_exe,
                        "python": f"C:\\Python27\\ArcGIS{ver}\\python.exe"
                                  if os.path.exists(f"C:\\Python27\\ArcGIS{ver}\\python.exe") else None,
                    })
                    found = True
                    break
            if found:
                break
        if found:
            arcmap_done = True
            continue
        # 2b) 注册表（同一版本号下 InstallDir 有效）
        for key_root in (r"SOFTWARE\ESRI", r"SOFTWARE\WOW6432Node\ESRI"):
            reg_dir = _read_reg_value(f"{key_root}\\Desktop{ver}", _ARCMAP_REG_VALUE)
            if reg_dir and os.path.exists(os.path.join(reg_dir, "bin", "arcmap.exe")):
                installs.append({
                    "name": f"ArcMap {ver}",
                    "type": "desktop",
                    "exe": os.path.join(reg_dir, "bin", "arcmap.exe"),
                    "python": f"C:\\Python27\\ArcGIS{ver}\\python.exe"
                              if os.path.exists(f"C:\\Python27\\ArcGIS{ver}\\python.exe") else None,
                })
                arcmap_done = True
                break
        if arcmap_done:
            continue
    # 2c) where 兜底（仅当上面都没找到）
    if not arcmap_done:
        hit = _where_search("arcmap.exe")
        if hit:
            installs.append({
                "name": "ArcMap (版本未知)",
                "type": "desktop",
                "exe": hit,
                "python": None,
            })

    return installs


# ---- 内嵌 arcpy 脚本（运行时写入临时文件，由 ArcGIS 自带 python 执行）---- #
_ARCPY_PRO_SCRIPT = """\
import arcpy, sys, os
proj = sys.argv[1]
shp = sys.argv[2]
aprx = arcpy.mp.ArcGISProject(proj)
maps = aprx.listMaps()
if not maps:
    sys.stderr.write("工程中没有可用地图")
    sys.exit(2)
m = maps[0]
m.addDataFromPath(shp)
# 尝试直接保存；若工程被 Pro 占锁（OSError），则另存为副本
try:
    aprx.save()
    print("OK")
except OSError:
    base, ext = os.path.splitext(proj)
    copy_path = base + "_POI导入" + ext
    aprx.saveACopy(copy_path)
    print("OK_COPY", copy_path)
"""

_ARCPY_DESKTOP_SCRIPT = """\
import arcpy, sys
mxd = sys.argv[1]
shp = sys.argv[2]
doc = arcpy.mapping.MapDocument(mxd)
df = arcpy.mapping.ListDataFrames(doc)[0]
lyr = arcpy.mapping.Layer(shp)
arcpy.mapping.AddLayer(df, lyr, "TOP")
doc.save()
print("OK")
"""


def _find_pro_template(pro_base):
    """定位 ArcGIS Pro 默认工程模板（用于新建空白工程再加载图层）。"""
    cands = [
        os.path.join(pro_base, "Resources", "ArcGIS Pro Project Template.aprx"),
        os.path.join(pro_base, "Resources", "ProjectTemplates",
                     "ArcGIS Pro Project Template.aprx"),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def _ascii_safe_path(shapefile_path):
    """若路径含非 ASCII 字符，复制 .shp/.shx/.dbf/.prj 到临时目录用 ASCII 名。

    ArcMap 10.2 等老版本对命令行参数中的中文/日文路径支持不佳，
    会导致"无法打开指定文件"错误。此函数返回 ASCII 安全的副本路径，
    原文件保留不动。

    返回 (ascii_path: str, cleanup_fn: callable)：
        ascii_path 可直接传给 ArcMap；cleanup_fn 用于使用后清理临时副本。
    """
    try:
        # 路径全 ASCII 则直接返回
        shapefile_path.encode("ascii")
        return shapefile_path, lambda: None
    except UnicodeEncodeError:
        pass

    import shutil
    tmp_dir = tempfile.mkdtemp(prefix="poi_ascii_")
    base = os.path.basename(shapefile_path)
    name_no_ext = os.path.splitext(base)[0]
    # 临时文件名只用 ASCII（pid + 时间戳）
    import time
    ascii_name = f"poi_{os.getpid()}_{int(time.time())}"
    tmp_shp = os.path.join(tmp_dir, ascii_name + ".shp")
    # 复制 Shapefile 四件套
    copied = []
    for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        src = os.path.splitext(shapefile_path)[0] + ext
        if os.path.exists(src):
            dst = os.path.splitext(tmp_shp)[0] + ext
            try:
                shutil.copy2(src, dst)
                copied.append(dst)
            except Exception:
                pass

    def cleanup():
        for f in copied:
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    return tmp_shp, cleanup


def open_in_arcgis(shapefile_path):
    """按钮 A：启动本机 ArcGIS 并直接加载 shapefile。

    不再依赖 os.startfile —— 若 .shp 被关联到记事本等程序，startfile 会错误地
    打开文本文档。改为：优先用检测到的 ArcGIS 主程序显式打开。

    - ArcMap：命令行直接传入 .shp 即可作为图层打开（原生支持）。
      若路径含中文等非 ASCII 字符，先复制到临时 ASCII 路径（ArcMap 10.2 命令行
      对中文路径支持差）。
    - ArcGIS Pro：命令行不接受 .shp；改为用 arcpy 新建一个含该图层的临时工程，
      再用 Pro 打开该工程，确保数据可见。
    返回 (成功: bool, 信息: str)。
    """
    if not os.path.exists(shapefile_path):
        return False, f"未找到文件：{shapefile_path}"

    installs = detect_arcgis()
    if not installs:
        return False, ("未检测到本机安装 ArcGIS / ArcGIS Pro。\n"
                       "请先安装后再使用此功能；或改用「导入到工程文件」按钮。")

    # 若路径含非 ASCII，复制到临时 ASCII 路径（兼容 ArcMap 10.2）
    open_path, cleanup_fn = _ascii_safe_path(shapefile_path)
    cleanup_log = ""
    if open_path != shapefile_path:
        cleanup_log = f"（已复制到临时 ASCII 路径：{open_path}）"

    # 1) 优先 ArcMap
    # 经测试，ArcMap 10.2 通过命令行 + .shp 时会错误地追加 .mxd 后缀；
    # 且 os.startfile 依赖 DDE 配置（多数 Windows 上不生效，会落到默认关联=记事本）。
    # 最可靠方案：仅启动 ArcMap（无参数），把 shapefile 路径明确告诉用户，
    # 由用户在 ArcMap 中用「文件 → 添加数据 → 添加数据」加载（Ctrl+O）。
    for inst in installs:
        if inst["type"] == "desktop" and inst.get("exe") and os.path.exists(inst["exe"]):
            try:
                # 仅启动 ArcMap，无参数（ArcMap 会打开空白地图或上次文档）
                subprocess.Popen([inst["exe"]], creationflags=CREATE_NO_WINDOW)
                # ASCII 副本先留着，给用户复制粘贴用，60 秒后再清
                import threading
                def delayed_cleanup():
                    import time as _t
                    _t.sleep(60)
                    cleanup_fn()
                threading.Thread(target=delayed_cleanup, daemon=True).start()
                return True, (
                    f"已启动 {inst['name']}（空白地图/上次文档）。\n\n"
                    f"POI 数据已导出为 Shapefile：\n{shapefile_path}\n\n"
                    f"请在 ArcMap 中点击「文件 → 添加数据 → 添加数据」"
                    f"（或按 Ctrl+O），选择上述路径的 .shp 文件即可加载。\n\n"
                    f"（提示：可先将 ArcMap 的 .shp 文件关联改为 ArcMap 本程序，"
                    f"这样今后双击 .shp 就能直接在 ArcMap 中打开）")
            except Exception as e:
                cleanup_fn()
                return False, f"启动 {inst['name']} 失败：{e}"

    # 2) 仅 ArcGIS Pro：生成临时工程并加载图层，再打开
    for inst in installs:
        if inst["type"] == "pro":
            if not inst.get("python") or not os.path.exists(inst["python"]):
                cleanup_fn()
                return False, ("检测到 ArcGIS Pro，但其自带 Python（含 arcpy）不可用，"
                               "无法自动加载数据。请改用「导入到工程文件」按钮。")
            pro_base = os.path.dirname(os.path.dirname(inst["exe"])) \
                if inst.get("exe") else None
            try:
                return _open_pro_with_data(inst, open_path, pro_base)
            finally:
                cleanup_fn()

    # 兜底：检测到安装但主程序/自带 Python 均不可用
    cleanup_fn()
    return False, ("检测到 ArcGIS，但其主程序或自带 Python 不可用，无法自动加载数据。\n"
                   "请尝试修复安装，或手动在 ArcGIS 中添加导出的 Shapefile。")


def _open_pro_with_data(inst, shapefile_path, pro_base):
    """用 Pro 自带 arcpy 新建含 shapefile 图层的临时工程，并用 Pro 打开它。"""
    tmp_dir = tempfile.gettempdir()
    tmp_aprx = os.path.join(tmp_dir, f"POI_Open_{os.getpid()}.aprx")
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="arcgis_open_")
    try:
        # 若检测到模板则基于模板新建，否则尝试直接新建空白工程
        template = _find_pro_template(pro_base) if pro_base else None
        script = _ARCPY_OPEN_PRO_SCRIPT.format(
            shp=shapefile_path.replace("\\", "\\\\"),
            out=tmp_aprx.replace("\\", "\\\\"),
            template=(template or "").replace("\\", "\\\\"),
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)
        proc = subprocess.run(
            [inst["python"], script_path],
            capture_output=True, text=True, timeout=120,
            creationflags=CREATE_NO_WINDOW,
        )
        out = (proc.stdout + proc.stderr).strip()
        if proc.returncode != 0 or "OK" not in out:
            if "NotInitialized" in out or "sign in" in out.lower():
                return False, ("arcpy 未初始化：ArcGIS Pro 需先登录账户（或离线授权），"
                              "请先启动一次 ArcGIS Pro 并登录，再重试。")
            if "createMap" in out and "has no attribute" in out:
                return False, ("当前 ArcGIS Pro 版本不支持自动创建地图。"
                              "请改用「导入到工程文件」按钮，选择你已有的 .aprx 工程。")
            return False, f"生成临时工程失败：{out[:400]}"
        if not os.path.exists(tmp_aprx):
            return False, "临时工程生成失败，无法打开 ArcGIS Pro"
        subprocess.Popen([inst["exe"], tmp_aprx], creationflags=CREATE_NO_WINDOW)
        return True, (f"已启动 ArcGIS Pro 并加载 {os.path.basename(shapefile_path)}"
                      f"（临时工程：{tmp_aprx}）")
    except subprocess.TimeoutExpired:
        return False, "ArcGIS Pro 加载超时（>120 秒）"
    except Exception as e:
        return False, f"打开 ArcGIS Pro 失败：{e}"
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass


_ARCPY_OPEN_PRO_SCRIPT = """\
import arcpy, sys, os
shp = r"{shp}"
out = r"{out}"
template = r"{template}"
if template and os.path.exists(template):
    aprx = arcpy.mp.ArcGISProject(template)
else:
    aprx = arcpy.mp.ArcGISProject("")
maps = aprx.listMaps()
if not maps:
    # 空白工程无地图时，主动创建一个地图容器再加载数据
    m = aprx.createMap("POI地图")
else:
    m = maps[0]
m.addDataFromPath(shp)
try:
    aprx.saveACopy(out)
    print("OK")
except Exception as e:
    sys.stderr.write("save failed: " + str(e))
    sys.exit(3)
"""


def import_to_project(shapefile_path, project_path):
    """按钮 B：将 shapefile 图层写入指定工程文件(.aprx/.mxd)。
    返回 (成功, 信息, 实际保存的工程路径) — 第三个值用于成功后自动启动 ArcGIS 打开。
    """
    if not os.path.exists(shapefile_path):
        return False, f"未找到文件：{shapefile_path}", ""
    project_path = (project_path or "").strip()
    if not project_path:
        return False, "未指定工程文件路径", ""

    ext = os.path.splitext(project_path)[1].lower()
    if ext == ".aprx":
        inst_type, script = "pro", _ARCPY_PRO_SCRIPT
    elif ext == ".mxd":
        inst_type, script = "desktop", _ARCPY_DESKTOP_SCRIPT
    else:
        return False, f"不支持的工程文件类型：{ext}（仅支持 .aprx / .mxd）", ""

    target = None
    for inst in detect_arcgis():
        if inst["type"] == inst_type:
            target = inst
            break
    if not target or not target.get("python") or not os.path.exists(target["python"]):
        need = "ArcGIS Pro" if inst_type == "pro" else "ArcMap"
        return False, (f"未检测到 {need} 自带的 Python（含 arcpy），无法写入工程。"
                       f"请确认已安装 {need}。"), ""

    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="arcgis_import_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)
        proc = subprocess.run(
            [target["python"], script_path, project_path, shapefile_path],
            capture_output=True, text=True, timeout=120,
            creationflags=CREATE_NO_WINDOW,
        )
        out = (proc.stdout + proc.stderr).strip()
        if proc.returncode == 0:
            if "OK_COPY" in out:
                # 工程被 Pro 占锁，已另存为副本
                parts = out.split("OK_COPY")
                copy_path = parts[-1].strip() if len(parts) > 1 else "(未知路径)"
                return True, (f"工程当前被 ArcGIS Pro 打开，无法直接保存。"
                              f"已将含 POI 图层的副本保存至：\n{copy_path}\n"
                              f"请关闭原工程后打开此副本查看新图层。"), copy_path
            if "OK" in out:
                return True, (f"已将 {os.path.basename(shapefile_path)} 写入工程 "
                              f"{os.path.basename(project_path)}（若工程正打开，请重开以查看新图层）"), project_path
        if "NotInitialized" in out or "sign in" in out.lower() or "未授权" in out:
            return False, ("arcpy 未初始化：ArcGIS Pro 需先登录账户（或离线授权），"
                          "请先启动一次 ArcGIS Pro 并登录，再重试。"), ""
        return False, f"arcpy 执行失败（返回码 {proc.returncode}）：{out[:500]}", ""
    except subprocess.TimeoutExpired:
        return False, "arcpy 执行超时（>120 秒）", ""
    except Exception as e:
        return False, f"调用 ArcGIS Python 失败：{e}", ""
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass


def launch_arcgis_with_project(project_path):
    """用对应的 ArcGIS 程序（Pro / ArcMap）打开已写入的工程文件。

    用于按钮 B 写入成功后自动打开 .aprx/.mxd，让用户立即看到新图层。
    返回 (ok, msg)。
    """
    if not project_path or not os.path.exists(project_path):
        return False, f"工程文件不存在：{project_path}"
    ext = os.path.splitext(project_path)[1].lower()
    inst_type = "pro" if ext == ".aprx" else ("desktop" if ext == ".mxd" else None)
    if not inst_type:
        return False, f"不支持的工程文件类型：{ext}"

    target = None
    for inst in detect_arcgis():
        if inst["type"] == inst_type and inst.get("exe") and os.path.exists(inst["exe"]):
            target = inst
            break
    if not target:
        need = "ArcGIS Pro" if inst_type == "pro" else "ArcMap"
        return False, f"未检测到 {need} 主程序，无法打开工程"

    try:
        subprocess.Popen([target["exe"], project_path], creationflags=CREATE_NO_WINDOW)
        return True, f"已启动 {target['name']} 并打开 {os.path.basename(project_path)}"
    except Exception as e:
        return False, f"启动 {target['name']} 失败：{e}"
