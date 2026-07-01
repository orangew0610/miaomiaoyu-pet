#!/usr/bin/env python3
"""
Debug Pet - 桌面宠物Debugger
一个可爱的编程助手，能检测代码错误并给出修复建议
现在不用这个，改用debug_pet_pyqt.py
"""

import sys
import io

# 安全设置终端编码（避免关闭文件问题）
try:
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import PIL.Image
import PIL.ImageTk
import PIL.ImageDraw
import os
import tempfile
import subprocess
import json
import re
import requests
import threading
import random
from datetime import datetime


# ============== 马卡龙配色方案 ==============
MACARON_COLORS = {
    'pink': '#FFB6C1',      # 粉色
    'mint': '#98D8C8',      # 薄荷绿
    'lavender': '#E6E6FA',  # 薰衣草紫
    'peach': '#FFDAB9',     # 蜜桃色
    'blue': '#87CEEB',      # 天蓝
    'yellow': '#FFFACD',    # 柠檬黄
    'coral': '#FF7F7F',     # 珊瑚色
    'green': '#90EE90',     # 浅绿
}


# ============== 气泡菜单类 ==============
class BubbleMenu:
    """气泡式右键菜单"""
    
    def __init__(self, parent):
        self.parent = parent
        self.menu_window = None
        self.items = []
        
    def add_command(self, label, command=None, state='normal'):
        """添加菜单项"""
        self.items.append({
            'label': label,
            'command': command,
            'state': state,
            'type': 'command'
        })
    
    def add_separator(self):
        """添加分隔线"""
        self.items.append({'type': 'separator'})
    
    def post(self, x, y):
        """显示菜单"""
        if self.menu_window:
            self.unpost()
        
        # 创建菜单窗口
        self.menu_window = tk.Toplevel(self.parent)
        self.menu_window.overrideredirect(True)
        self.menu_window.attributes('-topmost', True)
        
        # 计算菜单大小
        menu_width = 180
        item_height = 32
        separator_height = 8
        total_height = 20  # 顶部padding
        
        for item in self.items:
            if item['type'] == 'separator':
                total_height += separator_height
            else:
                total_height += item_height
        total_height += 15  # 底部padding
        
        # 创建背景画布（透明背景）
        canvas = tk.Canvas(
            self.menu_window,
            width=menu_width,
            height=total_height,
            bg='#000000',
            highlightthickness=0
        )
        canvas.pack()
        
        # 绘制圆角背景（无偏移）
        self._draw_rounded_bg(canvas, menu_width, total_height)
        
        # 绘制菜单项（从 y=15 开始，与背景对齐）
        y = 15
        self.item_rects = []
        
        for i, item in enumerate(self.items):
            if item['type'] == 'separator':
                # 绘制分隔线
                canvas.create_line(
                    15, y + 4, menu_width - 15, y + 4,
                    fill='#E0E0E0', width=1
                )
                y += separator_height
            else:
                # 存储菜单项位置信息
                item_rect = {
                    'x1': 5, 'y1': y,
                    'x2': menu_width - 5, 'y2': y + item_height,
                    'item': item,
                    'index': i
                }
                
                # 绘制文字
                text_color = '#888888' if item['state'] == 'disabled' else '#333333'
                text_id = canvas.create_text(
                    menu_width // 2, y + item_height // 2,
                    text=item['label'],
                    font=('Microsoft YaHei UI', 10),
                    fill=text_color,
                    tags=f'item_{i}'
                )
                item_rect['text_id'] = text_id
                self.item_rects.append(item_rect)
                
                # 绑定事件
                if item['state'] != 'disabled' and item.get('command'):
                    canvas.tag_bind(f'item_{i}', '<Enter>', 
                        lambda e, c=canvas: self._on_enter(c))
                    canvas.tag_bind(f'item_{i}', '<Leave>', 
                        lambda e, c=canvas: self._on_leave(c))
                    canvas.tag_bind(f'item_{i}', '<Button-1>', 
                        lambda e, cmd=item['command']: self._on_click(cmd))
                
                y += item_height
        
        # 设置窗口位置（确保在屏幕内）
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        
        if x + menu_width > screen_width:
            x = screen_width - menu_width - 10
        if y + total_height > screen_height:
            y = screen_height - total_height - 10
        
        self.menu_window.geometry(f'{menu_width}x{total_height}+{x}+{y}')
        
        # 设置窗口透明（Windows支持）
        try:
            self.menu_window.attributes('-transparentcolor', '#000000')
            self.menu_window.attributes('-alpha', 0.82)
        except:
            pass
        
        # 点击外部关闭菜单
        self.menu_window.bind('<FocusOut>', lambda e: self.unpost())
        self.menu_window.focus_set()
    
    def _draw_rounded_bg(self, canvas, width, height):
        """绘制圆角背景"""
        # 创建圆角矩形图片
        img = PIL.Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(img)
        
        # 白色背景
        bg_color = (255, 255, 255, 255)
        draw.rounded_rectangle(
            [(0, 0), (width-1, height-1)],
            radius=12,
            fill=bg_color,
            outline=(200, 200, 200, 255),
            width=1
        )
        self.bg_image = PIL.ImageTk.PhotoImage(img)
        canvas.create_image(0, 0, image=self.bg_image, anchor='nw')
    
    def _on_enter(self, canvas):
        """鼠标进入菜单项（选中效果）"""
        # 获取鼠标在 Canvas 上的坐标
        x, y = canvas.winfo_pointerxy()
        x = x - canvas.winfo_rootx()
        y = y - canvas.winfo_rooty()
        
        # 查找鼠标下的菜单项
        for rect in self.item_rects:
            if rect['x1'] <= x <= rect['x2'] and rect['y1'] <= y <= rect['y2']:
                canvas.delete('hover_bg')
                # 创建矩形选中效果
                canvas.create_rectangle(
                    rect['x1'], rect['y1'], rect['x2'] - 1, rect['y2'] - 1,
                    fill='#E3F2FD', outline='#90CAF9', width=1,
                    tags='hover_bg'
                )
                # 确保选中效果在背景之上、文字之下
                canvas.tag_raise('hover_bg')
                for item_rect in self.item_rects:
                    if 'text_id' in item_rect:
                        canvas.tag_raise(item_rect['text_id'])
                break
    
    def _on_leave(self, canvas):
        """鼠标离开菜单项"""
        canvas.delete('hover_bg')
    
    def _on_click(self, command):
        """点击菜单项"""
        self.unpost()
        if command:
            command()
    
    def unpost(self):
        """隐藏菜单"""
        if self.menu_window:
            try:
                self.menu_window.destroy()
            except:
                pass
            self.menu_window = None
    
    def destroy(self):
        """销毁菜单"""
        self.unpost()
    
    def winfo_viewable(self):
        """检查菜单是否可见"""
        return self.menu_window is not None and self.menu_window.winfo_viewable()


# ============== 圆角按钮类 ==============
class RoundedButton(tk.Canvas):
    """圆角按钮（使用Canvas绘制）"""
    
    def __init__(self, parent, text, command=None, bg_color='#98D8C8', 
                 fg_color='white', width=100, height=36, radius=10, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, **kwargs)
        
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.width = width
        self.height = height
        self.radius = radius
        self.text = text
        self.hover_color = self._lighten_color(bg_color)
        self.disabled_color = '#CCCCCC'
        self._disabled = False
        
        # 配置Canvas背景（与窗口背景色一致）
        self.config(bg='#FFF8DC')
        
        self._draw_button()
        
        # 绑定事件
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
    
    def _lighten_color(self, hex_color):
        """使颜色变亮"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, r + 20)
        g = min(255, g + 20)
        b = min(255, b + 20)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _darken_color(self, hex_color):
        """使颜色变暗"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _draw_button(self, hover=False):
        """绘制按钮"""
        self.delete('all')
        
        if self._disabled:
            color = self.disabled_color
        else:
            color = self.hover_color if hover else self.bg_color
        
        # 创建圆角矩形图片（透明背景）
        img = PIL.Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [(0, 0), (self.width-1, self.height-1)],
            radius=self.radius,
            fill=color,
            outline=self._darken_color(color),
            width=1
        )
        
        self.btn_image = PIL.ImageTk.PhotoImage(img)
        self.create_image(0, 0, image=self.btn_image, anchor='nw')
        
        # 绘制文字
        text_color = '#888888' if self._disabled else self.fg_color
        self.create_text(
            self.width // 2, self.height // 2,
            text=self.text,
            font=('Microsoft YaHei UI', 10, 'bold'),
            fill=text_color
        )
    
    def _on_enter(self, event):
        if not self._disabled:
            self._draw_button(hover=True)
            self.config(cursor='hand2')
    
    def _on_leave(self, event):
        self._draw_button(hover=False)
    
    def _on_click(self, event):
        if not self._disabled and self.command:
            self.command()
    
    def configure(self, **kwargs):
        """配置按钮属性"""
        if 'state' in kwargs:
            state = kwargs['state']
            self._disabled = (state == 'disabled')
            self._draw_button()
        elif 'text' in kwargs:
            self.text = kwargs['text']
            self._draw_button()


# ============== 圆角输入框类 ==============
class RoundedEntry(tk.Canvas):
    """圆角输入框"""
    
    def __init__(self, parent, width=300, height=36, radius=8, **kwargs):
        self.entry_var = kwargs.pop('textvariable', None)
        self.show_char = kwargs.pop('show', None)
        
        super().__init__(parent, width=width, height=height, 
                        bg=parent['bg'], highlightthickness=0)
        
        self.width = width
        self.height = height
        self.radius = radius
        
        self._draw_entry()
        
        # 创建内部Entry
        entry_x = 10
        entry_width = width - 20
        
        self.entry = tk.Entry(
            self,
            textvariable=self.entry_var,
            show=self.show_char,
            font=('Microsoft YaHei UI', 10),
            bg='white',
            fg='#333333',
            relief='flat',
            highlightthickness=0,
            insertbackground='#333333'
        )
        self.create_window(entry_x, height//2, window=self.entry, anchor='w', width=entry_width)
    
    def _draw_entry(self):
        """绘制输入框背景"""
        img = PIL.Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [(0, 0), (self.width-1, self.height-1)],
            radius=self.radius,
            fill=(255, 255, 255, 255),
            outline=(200, 200, 200, 255),
            width=1
        )
        
        self.entry_image = PIL.ImageTk.PhotoImage(img)
        self.create_image(0, 0, image=self.entry_image, anchor='nw')
    
    def get(self):
        return self.entry.get()
    
    def insert(self, index, text):
        return self.entry.insert(index, text)


# ============== 配置 ==============
APP_NAME = "Debug Pet"
VERSION = "1.0.0"

# 宠物状态
PET_STATE_IDLE = "idle"
PET_STATE_WALKING = "walking"
PET_STATE_WALKING_LEFT = "walking_left"
PET_STATE_WALKING_RIGHT = "walking_right"
PET_STATE_JUMPING = "jumping"
PET_STATE_JUMPING_LEFT = "jumping_left"
PET_STATE_JUMPING_RIGHT = "jumping_right"
PET_STATE_THINKING = "thinking"
PET_STATE_HAPPY = "happy"
PET_STATE_SAD = "sad"
PET_STATE_WAITING = "waiting"

# 宠物表情对应的颜色（气泡颜色）
STATE_COLORS = {
    PET_STATE_IDLE: "#E8F5E9",      # 浅绿 - 待机
    PET_STATE_WALKING: "#E3F2FD",   # 浅蓝 - 行走
    PET_STATE_THINKING: "#FFF8E1", # 浅黄 - 分析中
    PET_STATE_HAPPY: "#C8E6C9",     # 绿色 - 开心
    PET_STATE_SAD: "#FFCDD2",       # 粉色 - 难过
    PET_STATE_WAITING: "#F3E5F5",  # 浅紫 - 等待
}

# ============== 宠物动画管理器 ==============
class PetAnimator:
    """管理宠物动画帧切换"""

    def __init__(self, label_widget):
        self.label = label_widget
        self.frames = {}
        self.current_state = PET_STATE_IDLE
        self.current_frame_index = 0
        self.animating = False
        self.callback = None
        self.after_id = None
        # idle 有多个子状态，用于随机切换
        self._idle_sub_index = 0
        self._idle_frames_list = []  # 存储各个 idle 文件的帧
        # idle 切换时间控制（毫秒）
        self._idle_switch_min_interval = 5000  # 5秒
        self._last_idle_switch_time = None  # 上次切换时间

    def load_frames(self, state, frames_list):
        """加载某一状态的动画帧（直接接受帧列表）"""
        if frames_list:
            self.frames[state] = frames_list
            # 如果是 idle，保存各个子 idle 的帧
            if state == PET_STATE_IDLE:
                self._idle_frames_list.append(frames_list)

    def set_state(self, state, callback=None):
        """切换状态并播放动画"""
        if state in self.frames and self.frames[state]:
            self.current_state = state
            self.current_frame_index = 0
            self.callback = callback
            # 切换到 idle 状态时重置切换计时器
            if state == PET_STATE_IDLE:
                self._last_idle_switch_time = datetime.now()
                self._idle_switch_count = 0
            if not self.animating:
                self._animate()

    def _animate(self):
        """执行动画帧切换"""
        if not self.frames.get(self.current_state):
            return

        self.animating = True
        frames = self.frames[self.current_state]
        print(f"[ANIM] 切换到 {self.current_state}, 帧数: {len(frames)}")
        # idle 状态：每隔一轮动画随机切换 idle 子状态（需满足最小间隔）
       
        if self.current_state == PET_STATE_IDLE and self._idle_frames_list and len(self._idle_frames_list) > 1:
            print(f"[ANIM] 当前 idle 子状态: idle{self._idle_sub_index+1}")
            # 每播放完一轮动画，有概率切换 idle
            #if self._idle_switch_count >= len(frames):
            if True:
                
                # 检查是否满足最小时间间隔
                now = datetime.now()
                elapsed = 0
                if self._last_idle_switch_time:
                    elapsed = (now - self._last_idle_switch_time).total_seconds() * 1000
                # 只有当满足时间间隔时才能切换
                if elapsed >= self._idle_switch_min_interval and random.random() < 0.3:
                    # 随机选择另一个 idle
                    new_index = random.randint(0, len(self._idle_frames_list) - 1)
                    print(f"[ANIM] idle子状态切换到 idle{new_index + 1}, 间隔: {elapsed:.0f}ms")
                    if new_index != self._idle_sub_index:
                        self._idle_sub_index = new_index
                        self._last_idle_switch_time = now
                        frames = self._idle_frames_list[self._idle_sub_index]
                        self.frames[PET_STATE_IDLE] = frames
                        self.current_frame_index = 0
                        print(f"[ANIM] 切换到 idle{self._idle_sub_index + 1}, 间隔: {elapsed:.0f}ms")
        
        if frames:
            try:
                self.label.configure(image=frames[self.current_frame_index])
                self.current_frame_index = (self.current_frame_index + 1) % len(frames)
                self.after_id = self.label.after(200, self._animate)
            except:
                # 窗口可能已销毁
                self.animating = False
        else:
            self.animating = False

    def stop(self):
        """停止动画"""
        self.animating = False
        if self.after_id:
            try:
                self.label.after_cancel(self.after_id)
            except:
                pass


# ============== 代码检测器 ==============
class CodeChecker:
    """代码错误检测器"""

    def __init__(self, use_ai=False, api_key=None, api_url=None):
        self.use_ai = use_ai
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.api_url = api_url or "https://api.deepseek.com/chat/completions"

    def check_python(self, code_content):
        """使用pylint检测Python代码错误"""
        errors = []

        # 写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code_content)
            temp_file = f.name

        try:
            # 使用python命令（兼容Windows）
            python_cmd = 'python' if os.name == 'nt' else 'python3'
            
            # 运行py_compile检查语法
            result = subprocess.run(
                [python_cmd, '-m', 'py_compile', temp_file],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # 语法错误
                error_lines = result.stderr.split('\n')
                for line in error_lines:
                    if line.strip():
                        # 解析语法错误
                        match = re.search(r'line (\d+)', line)
                        if match:
                            line_num = int(match.group(1))
                            errors.append({
                                'line': line_num,
                                'column': 1,
                                'message': line.strip(),
                                'severity': 'error',
                                'type': 'syntax'
                            })

            # 使用pyflakes检测更细粒度错误
            pyflakes_result = subprocess.run(
                [python_cmd, '-m', 'pyflakes'],
                input=code_content,
                capture_output=True,
                text=True
            )

            if pyflakes_result.returncode != 0:
                # pyflakes输出到stdout
                output = pyflakes_result.stdout + pyflakes_result.stderr
                for line in output.split('\n'):
                    match = re.search(r'<stdin>:(\d+):(\d+)?\s*(.+)', line)
                    if match:
                        errors.append({
                            'line': int(match.group(1)),
                            'column': int(match.group(2)) if match.group(2) else 1,
                            'message': match.group(3),
                            'severity': 'warning',
                            'type': 'pyflakes'
                        })

        except FileNotFoundError:
            errors.append({
                'line': 1,
                'column': 1,
                'message': 'Python编译器未找到，请安装Python3',
                'severity': 'error',
                'type': 'system'
            })
        finally:
            os.unlink(temp_file)

        return errors

    def check_with_ai(self, code_content, filename="test.py"):
        """使用AI API检测代码错误"""
        if not self.api_key:
            return [{
                'line': 1,
                'column': 1,
                'message': '未配置AI API Key，请设置DEEPSEEK_API_KEY环境变量',
                'severity': 'error',
                'type': 'config'
            }]

        # 提取语言
        ext = os.path.splitext(filename)[1]
        lang_map = {'.py': 'python', '.js': 'javascript', '.java': 'java',
                    '.c': 'c', '.cpp': 'cpp', '.h': 'c', '.go': 'go',
                    '.rs': 'rust', '.ts': 'typescript', '.html': 'html'}

        language = lang_map.get(ext, 'unknown')

        prompt = f"""请分析以下{language}代码，找出所有错误并以JSON格式返回。
只返回JSON数组，不要包含其他内容。每个错误格式：
{{"line": 行号, "column": 列号, "message": "错误描述", "severity": "error/warning", "fix": "修复建议"}}

代码：
```{code_content}```"""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            content = result['choices'][0]['message']['content']

            # 提取JSON
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                errors = json.loads(json_match.group())
                return errors
            else:
                return [{
                    'line': 1,
                    'column': 1,
                    'message': 'AI返回格式解析失败',
                    'severity': 'error',
                    'type': 'ai'
                }]

        except requests.exceptions.RequestException as e:
            return [{
                'line': 1,
                'column': 1,
                'message': f'API请求失败: {str(e)}',
                'severity': 'error',
                'type': 'network'
            }]
        except (KeyError, json.JSONDecodeError) as e:
            return [{
                'line': 1,
                'column': 1,
                'message': f'AI响应解析失败: {str(e)}',
                'severity': 'error',
                'type': 'parse'
            }]

    def check(self, code_content, filename="code.py", use_ai=False):
        """统一检测接口"""
        ext = os.path.splitext(filename)[1]

        if ext == '.py' and not use_ai:
            return self.check_python(code_content)
        else:
            return self.check_with_ai(code_content, filename)


# ============== 主应用窗口 ==============
class DebugPetApp:
    """Debug Pet主应用"""

    def __init__(self):
        # 变量
        self.code_content = ""
        self.filename = "code.py"
        self.errors = []
        self.current_error_index = -1
        self.checker = CodeChecker()
        self.animator = None
        
        # 所有定时器ID列表
        self.after_jobs = []
        
        # 宠物移动相关
        self.pet_x = 100
        self.pet_y = 100
        self.move_speed = 2
        self.target_x = None
        self.target_y = None
        self.is_moving = False
        self.is_dragging = False
        self.walk_direction = 1  # 1 = 右, -1 = 左
        
        # 尝试使用tkinterdnd2库
        try:
            from tkinterdnd2 import TkinterDnD
            self.root = TkinterDnD.Tk()
        except ImportError:
            self.root = tk.Tk()
        
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("120x120+100+100")
        
        # 无边框透明窗口
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.0)  # 初始透明
        
        # 创建宠物标签（使用白色背景作为透明占位）
        self.pet_label = tk.Label(self.root, bg='#FFFFFF', bd=0, padx=0, pady=0, highlightthickness=0)
        self.pet_label.pack()
        # 设置标签透明色
        self.pet_label.config(bg='#FFFFFF', highlightbackground='#FFFFFF')
        # 让标签支持透明
        try:
            self.pet_label.winfo_rgb('#FFFFFF')
            # 如果成功，设置透明色
            self.root.attributes('-transparentcolor', '#FFFFFF')    
        except:
            pass
        
        # 初始化动画器
        self.animator = PetAnimator(self.pet_label)
        self._load_pet_frames()
        
        # 初始化宠物
        self._init_pet()
        
        # 初始化无互动检测
        self.last_interaction_time = datetime.now()
        self._start_waiting_check()
        
        # 创建UI和绑定事件
        self._create_ui()
        
        # 设置拖拽
        self._setup_drag_drop()
        
        # 开始宠物行为
        self._start_pet_behavior()
        
        # 淡入窗口
        self.root.after(500, self._fade_in)
        
    def _fade_in(self):
        """窗口淡入效果"""
        try:
            for i in range(1, 21):
                self.root.attributes('-alpha', i / 20.0)
                self.root.update()
                self.root.after(30)
            print("Fade in completed")
        except Exception as e:
            print(f"Fade in error: {e}")
    
    def _init_pet(self):
        """初始化宠物"""
        # 居中显示
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.pet_x = (screen_width - 120) // 2
        self.pet_y = (screen_height - 120) // 2
        self._update_pet_position()
        
        # 设置待机动画
        self.animator.set_state(PET_STATE_IDLE)
    
    def _update_pet_position(self):
        """更新宠物位置"""
        geometry = f"120x120+{int(self.pet_x)}+{int(self.pet_y)}"
        self.root.geometry(geometry)
    
    def _start_waiting_check(self):
        """检查是否需要显示 waiting 动画"""
        # 只在 idle 状态下可能显示 waiting
        if self.animator.current_state == PET_STATE_IDLE:
            # 检查距离上次互动是否超过 60 秒
            idle_time = (datetime.now() - self.last_interaction_time).total_seconds()
            if idle_time > 60:
                # 30% 概率显示 waiting
                if random.random() < 0.3:
                    # 显示 waiting 动画
                    self.animator.set_state(PET_STATE_WAITING)
                    # waiting 持续 3-5 秒
                    waiting_duration = random.randint(5000, 10000)
                    self.root.after(waiting_duration, lambda: self._back_to_idle())
                    return
        
        # 每 10 秒检查一次
        job_id = self.root.after(10000, self._start_waiting_check)
        self.after_jobs.append(job_id)
    
    def _back_to_idle(self):
        """从其他状态返回 idle"""
        if self.animator.current_state in [PET_STATE_WAITING, PET_STATE_HAPPY, PET_STATE_SAD]:
            self.animator.set_state(PET_STATE_IDLE)
    
    def _start_pet_behavior(self):
        """开始宠物行为"""
        # 随机移动
        self._schedule_next_action()
    
    def _schedule_next_action(self):
        """调度下一个动作"""
        delay = random.randint(5000, 15000)  # 5-15秒后执行
        job_id = self.root.after(delay, self._random_action)
        self.after_jobs.append(job_id)
    
    def _random_action(self):
        """随机动作"""
        # 如果正在移动，不要执行任何动作，避免打断移动动画
        if self.is_moving:
            self._schedule_next_action()
            return

        try:
            menu_visible = self.context_menu.winfo_viewable()
        except:
            menu_visible = False
        
        if not menu_visible:
            action = random.choice(['move', 'idle', 'jump'])
            
            if action == 'move':
                self._start_random_walk()
            elif action == 'jump':
                self._jump()
            elif action == 'idle':
                self.animator.set_state(PET_STATE_IDLE)
        
        self._schedule_next_action()
    
    def _start_random_walk(self):
        """开始随机走动"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 随机选择目标位置
        margin = 50
        self.target_x = random.randint(margin, screen_width - 120 - margin)
        self.target_y = random.randint(margin, screen_height - 120 - margin)
        
        # 设置方向并更新动画状态
        if self.target_x > self.pet_x:
            self.walk_direction = 1
            self.animator.set_state(PET_STATE_WALKING_RIGHT)
        else:
            self.walk_direction = -1
            self.animator.set_state(PET_STATE_WALKING_LEFT)
        
        # 开始移动
        self.is_moving = True
        self._move_step()
    
    def _move_step(self):
        """移动一步"""
        if not self.is_moving:
            return
        
        dx = self.target_x - self.pet_x
        dy = self.target_y - self.pet_y
        
        distance = (dx**2 + dy**2) ** 0.5
        
        if distance < 5:
            # 到达目标
            self.is_moving = False
            self.pet_x = self.target_x
            self.pet_y = self.target_y
            self._clamp_position()  # 限制在屏幕内
            self._update_pet_position()
            self.animator.set_state(PET_STATE_IDLE)
            return
        
        # 移动
        step = min(self.move_speed, distance)
        ratio = step / distance
        self.pet_x += dx * ratio
        self.pet_y += dy * ratio
        
        # 限制在屏幕内
        self._clamp_position()
        
        self._update_pet_position()
        
        # 更新方向并切换动画
        if dx > 0 and self.walk_direction != 1:
            self.walk_direction = 1
            self.animator.set_state(PET_STATE_WALKING_RIGHT)
        elif dx < 0 and self.walk_direction != -1:
            self.walk_direction = -1
            self.animator.set_state(PET_STATE_WALKING_LEFT)
        
        job_id = self.root.after(30, self._move_step)
        self.after_jobs.append(job_id)
    
    def _jump(self):
        """跳跃动画"""
        print(f"[JUMP] 开始跳跃 from ({self.pet_x}, {self.pet_y}), direction={self.walk_direction}")
        
        # 根据方向选择不同的跳跃动画
        if self.walk_direction > 0:
            # 向右跳
            self.animator.set_state(PET_STATE_JUMPING_RIGHT)
        elif self.walk_direction < 0:
            # 向左跳
            self.animator.set_state(PET_STATE_JUMPING_LEFT)
        else:
            # 默认跳跃（没有方向）
            self.animator.set_state(PET_STATE_JUMPING)
        
        # 跳跃方向和距离 - 增大跳跃幅度
        jump_distance = 80  # 水平跳跃距离
        jump_direction = self.walk_direction if self.walk_direction != 0 else 1  # 沿当前移动方向跳跃
        
        # 记录原始位置
        start_x = self.pet_x
        start_y = self.pet_y
        print(f"[JUMP] 原始位置 ({start_x}, {start_y})")
        
        # 跳跃分4个阶段：向上、向前、向下、回到IDLE
        def jump_up():
            print(f"[JUMP] 向上跳: ({self.pet_x}, {start_y - 40})")
            self.pet_y = start_y - 40  # 增加跳跃高度
            self._clamp_position()  # 限制在屏幕内
            self._update_pet_position()
            job_id = self.root.after(120, jump_forward)
            self.after_jobs.append(job_id)
        
        def jump_forward():
            new_x = start_x + jump_direction * jump_distance
            print(f"[JUMP] 向前跳: ({new_x}, {self.pet_y})")
            self.pet_x = new_x
            self._clamp_position()  # 限制在屏幕内
            self._update_pet_position()
            job_id = self.root.after(120, jump_down)
            self.after_jobs.append(job_id)
        
        def jump_down():
            print(f"[JUMP] 下落: ({self.pet_x}, {start_y - 20})")
            self.pet_y = start_y - 20  # 下落一部分
            self._clamp_position()  # 限制在屏幕内
            self._update_pet_position()
            job_id = self.root.after(120, jump_land)
            self.after_jobs.append(job_id)
        
        def jump_land():
            print(f"[JUMP] 落地: ({self.pet_x}, {start_y})")
            self.pet_y = start_y
            self._clamp_position()  # 限制在屏幕内
            self._update_pet_position()
            self.animator.set_state(PET_STATE_IDLE)
        
        # 开始跳跃序列
        jump_up()
    
    def _clamp_position(self):
        """限制宠物位置在屏幕边界内"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        pet_width = 120
        pet_height = 120
        
        # 限制X坐标
        self.pet_x = max(0, min(self.pet_x, screen_width - pet_width))
        # 限制Y坐标（留出底部空间）
        self.pet_y = max(0, min(self.pet_y, screen_height - pet_height))

    def _create_ui(self):
        """创建UI组件"""
        # 为宠物标签绑定鼠标事件
        self.pet_label.bind('<Button-1>', self._on_pet_click)
        self.pet_label.bind('<B1-Motion>', self._on_pet_drag)
        self.pet_label.bind('<ButtonRelease-1>', self._on_drag_release)
        self.root.bind('<Button-1>', self._on_pet_click)
        self.root.bind('<B1-Motion>', self._on_pet_drag)
        self.root.bind('<ButtonRelease-1>', self._on_drag_release)
        
        # 创建右键菜单
        self._create_context_menu()
    
    def _create_context_menu(self):
        """创建气泡式右键菜单"""
        self.context_menu = BubbleMenu(self.root)
        self.context_menu.add_command(label='🐛 Debug Pet v' + VERSION, state='disabled')
        self.context_menu.add_separator()
        self.context_menu.add_command(label='🔍 检查代码', command=self._show_code_checker)
        self.context_menu.add_command(label='📁 打开文件', command=self._open_file)
        self.context_menu.add_separator()
        self.context_menu.add_command(label='⚙ 设置', command=self._show_settings)
        self.context_menu.add_command(label='💡 关于', command=self._show_about)
        self.context_menu.add_separator()
        self.context_menu.add_command(label='❌ 退出', command=self._quit_app)
        
        # 绑定右键菜单
        self.pet_label.bind('<Button-3>', self._show_context_menu)
        self.root.bind('<Button-3>', self._show_context_menu)
    
    def _on_pet_click(self, event):
        """宠物点击事件"""
        # 停止移动
        self.is_moving = False
        self.is_dragging = False
        if hasattr(self, 'parabola_after_id'):
            try:
                self.root.after_cancel(self.parabola_after_id)
            except:
                pass
        self.animator.set_state(PET_STATE_HAPPY)
        # 更新最后互动时间
        self.last_interaction_time = datetime.now()
        
        # 记录鼠标起始位置（使用绝对屏幕坐标）
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.drag_last_x = event.x_root
        self.drag_last_y = event.y_root
        self.drag_last_time = datetime.now()

    def _on_pet_drag(self, event):
        """宠物拖拽事件"""
        # 更新最后互动时间
        self.last_interaction_time = datetime.now()
        
        # 如果没有正在拖拽，记录开始
        if not self.is_dragging:
            self.is_dragging = True
            # 拖拽开始时设置跳跃状态
            #self.animator.set_state(PET_STATE_JUMPING_LEFT)
        
        # 计算拖拽速度
        now = datetime.now()
        dt = (now - self.drag_last_time).total_seconds()
        if dt > 0:
            self.drag_velocity_x = (event.x_root - self.drag_last_x) / dt
            self.drag_velocity_y = (event.y_root - self.drag_last_y) / dt
        
        self.drag_last_x = event.x_root
        self.drag_last_y = event.y_root
        self.drag_last_time = now
        
        # 直接使用鼠标在屏幕上的位置更新宠物位置
        new_x = self.pet_x + (event.x_root - self.drag_start_x)
        new_y = self.pet_y + (event.y_root - self.drag_start_y)
        
        # 边界检查
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 只在边界外时限制位置
        if new_x < 0:
            new_x = 0
        elif new_x > screen_width - 120:
            new_x = screen_width - 120
        
        if new_y < 0:
            new_y = 0
        elif new_y > screen_height - 120:
            new_y = screen_height - 120
        
        # 更新位置
        self.pet_x = new_x
        self.pet_y = new_y
        self._update_pet_position()
        
        # 更新起始位置
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root

    def _on_drag_release(self, event):
        """拖拽释放事件 - 实现抛物线效果"""
        if not self.is_dragging:
            return
        
        self.is_dragging = False
        
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        pet_size = 120
        
        # 计算抛物线目标位置
        # 根据速度计算初始速度和方向
        vx = getattr(self, 'drag_velocity_x', 0) * 0.3  # 衰减系数
        vy = getattr(self, 'drag_velocity_y', 0) * 0.3
        
        # 如果速度太小，直接返回 idle
        if abs(vx) < 50 and abs(vy) < 50:
            self.animator.set_state(PET_STATE_IDLE)
            return
        
        # 目标位置：应用速度后的位置
        target_x = self.pet_x + vx
        target_y = self.pet_y + vy
        
        # 边界检查：水平方向限制在屏幕内
        if target_x < 0:
            target_x = 0
            vx = 0  # 碰到左边界，停止水平移动
        elif target_x > screen_width - pet_size:
            target_x = screen_width - pet_size
            vx = 0  # 碰到右边界，停止水平移动
        
        # 目标 Y：落到屏幕底部附近
        target_y = screen_height - pet_size - 20
        
        # 抛物线参数
        start_x = self.pet_x
        start_y = self.pet_y
        end_x = target_x
        end_y = target_y
        
        # 计算抛物线最高点
        # 抛物线方程：y = a*(x-h)^2 + k
        # 其中 h 是最高点的 x 坐标，k 是最高点的 y 坐标
        h = (start_x + end_x) / 2
        # 最高点在起点和终点之间，且 Y 值较小（屏幕上方）
        mid_y = (start_y + end_y) / 2
        # 如果起点在终点上方，最高点应该在起点附近
        # 如果起点在终点下方，最高点应该在终点附近
        if start_y < end_y:
            k = min(start_y, end_y) - abs(vx) * 0.5  # 速度越大，抛得越高
        else:
            k = min(start_y, end_y) - abs(vx) * 0.3
        
        # 动画参数
        steps = 30  # 动画步数
        current_step = [0]
        gravity = 15  # 重力加速度系数
        
        def animate_parabola():
            if current_step[0] >= steps:
                # 动画结束
                self.pet_x = end_x
                self.pet_y = end_y
                self._update_pet_position()
                self.animator.set_state(PET_STATE_IDLE)
                return
            
            t = current_step[0] / steps
            
            # 计算当前 x（线性插值）
            x = start_x + (end_x - start_x) * t
            
            # 计算当前 y（抛物线）
            # 使用简化的抛物线：y = start_y + (end_y - start_y) * t + sin(t*pi) * height_offset
            height_offset = -abs(vx) * 0.3 if abs(vx) > 50 else -50
            y = start_y + (end_y - start_y) * t + (1 - abs(2*t - 1)) * height_offset
            
            # 更新位置
            self.pet_x = x
            self.pet_y = y
            self._update_pet_position()
            
            # 更新动画状态
            if t < 0.3:
                self.animator.set_state(PET_STATE_HAPPY)
            else:
                self.animator.set_state(PET_STATE_JUMPING_RIGHT if vx >= 0 else PET_STATE_JUMPING_LEFT)
            
            current_step[0] += 1
            self.parabola_after_id = self.root.after(30, animate_parabola)
        
        # 开始抛物线动画
        self.parabola_after_id = self.root.after(30, animate_parabola)

    def _show_context_menu(self, event):
        """显示右键菜单"""
        # 先隐藏旧菜单
        self.context_menu.unpost()
        # 显示新菜单
        self.context_menu.post(event.x_root, event.y_root)
    
    def _show_code_checker(self):
        """显示代码检查器窗口"""
         # 停止移动，避免检查器打开时宠物还在漂移
        self.is_moving = False
        
        # 如果已有窗口，先关闭
        if hasattr(self, 'checker_window') and self.checker_window.winfo_exists():
            self.checker_window.lift()
            return
        
        self.animator.set_state(PET_STATE_THINKING)
        
        # 创建代码检查器窗口 - 透明黄色背景
        self.checker_window = tk.Toplevel(self.root)
        self.checker_window.title("🐛 Debug Pet - 代码检查器")
        self.checker_window.geometry("650x580")
        self.checker_window.configure(bg='#FFF8DC')  # 透明黄色背景 (Cornsilk)
        self.checker_window.resizable(True, True)
        
        # 设置窗口半透明
        try:
            self.checker_window.attributes('-alpha', 0.92)
        except:
            pass
        
        # 创建UI
        self._create_checker_ui()
    
    def _create_checker_ui(self):
        """创建代码检查器UI - 马卡龙风格"""
        # 主框架
        main_frame = tk.Frame(self.checker_window, bg='#FFF8DC')
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # 标题区域
        title_frame = tk.Frame(main_frame, bg='#FFF8DC')
        title_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(title_frame, text="🐛 Debug Pet", 
                bg='#FFF8DC', fg='#5D5D5D', font=('Microsoft YaHei UI', 14, 'bold')).pack(side='left')
        
        # 代码输入区域
        code_frame = tk.Frame(main_frame, bg='#FFF8DC')
        code_frame.pack(fill='x', pady=5)
        
        tk.Label(code_frame, text="📋 代码输入", 
                bg='#FFF8DC', fg='#666666', font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        
        # 代码文本框 - 固定高度
        code_container = tk.Frame(code_frame, bg='#FFFFFF', height=150)
        code_container.pack(fill='x')
        code_container.pack_propagate(False)  # 保持固定高度
        code_container.config(highlightbackground='#E0E0E0', highlightthickness=1)
        
        self.code_text = tk.Text(code_container, bg='#FFFFFF', fg='#333333',
                                  font=('Consolas', 10),
                                  insertbackground='#333333', relief='flat',
                                  padx=10, pady=10, wrap='word')
        self.code_text.pack(fill='both', expand=True)
        
        # 错误列表区域
        error_frame = tk.Frame(main_frame, bg='#FFF8DC')
        error_frame.pack(fill='x', pady=10)
        
        tk.Label(error_frame, text="❌ 错误列表", 
                bg='#FFF8DC', fg='#666666', font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
        
        # 错误列表框 - 固定高度
        error_container = tk.Frame(error_frame, bg='#FFFFFF', height=100)
        error_container.pack(fill='x')
        error_container.pack_propagate(False)
        error_container.config(highlightbackground='#E0E0E0', highlightthickness=1)
        
        self.error_listbox = tk.Listbox(error_container, bg='#FFFFFF', fg='#E57373',
                                         font=('Consolas', 9),
                                         selectbackground='#FFB6C1', selectforeground='#333333',
                                         relief='flat', highlightthickness=0)
        self.error_listbox.pack(fill='both', expand=True)
        self.error_listbox.bind('<<ListboxSelect>>', self._on_error_select)
        
        # 按钮区域 - 马卡龙配色圆角按钮
        btn_frame = tk.Frame(main_frame, bg='#FFF8DC')
        btn_frame.pack(fill='x', pady=15)
        
        # 检查代码按钮 - 薄荷绿
        self.check_btn = RoundedButton(
            btn_frame, text="🔍 检查代码", command=self._check_code,
            bg_color=MACARON_COLORS['mint'], fg_color='green',
            width=110, height=38, radius=12
        )
        self.check_btn.pack(side='left', padx=8)
        
        # 打开文件按钮 - 天蓝色
        RoundedButton(
            btn_frame, text="📁 打开文件", command=self._open_file,
            bg_color=MACARON_COLORS['blue'], fg_color='blue',
            width=110, height=38, radius=12
        ).pack(side='left', padx=8)
        
        # 清空按钮 - 蜜桃色
        RoundedButton(
            btn_frame, text="🗑 清空", command=self._clear_all,
            bg_color=MACARON_COLORS['peach'], fg_color='red',
            width=90, height=38, radius=12
        ).pack(side='left', padx=8)

    def force_transparent_color(self, img, target_rgb=(255, 255, 255), white_threshold=240):
        """
        将图片中所有接近白色（RGB 每个分量 > white_threshold）的像素
        转换为精确的 target_rgb，以便 -transparentcolor 将其透明。
        没有用
        """
        img = img.convert('RGBA')
        data = img.getdata()
        new_data = []
        for r, g, b, a in data:
            # 如果像素接近白色（高亮度）
            if r > white_threshold and g > white_threshold and b > white_threshold:
                new_data.append(target_rgb + (255,))   # 变成不透明的目标色
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        return img

    def _load_pet_frames(self):
        """加载宠物动画帧 - 使用外部GIF图片"""
        from PIL import Image
        
        # GIF图片目录
        gif_dir = os.path.join(os.path.dirname(__file__), 'miaomiao-all-actions')
        
        # 状态到GIF文件的映射
        gif_mapping = {
            PET_STATE_IDLE: ['idle1.gif', 'idle2.gif', 'idle3.gif'],  # 多idle图片
            PET_STATE_WALKING_LEFT: 'running-right.gif',  # 只有右移动画（只用前4帧）
            PET_STATE_WALKING_RIGHT: 'running-right.gif',  # 复用右移动画，翻转使用（只用前4帧）
            PET_STATE_JUMPING_LEFT: 'jumping-left.gif',  # 只有左跳动画
            PET_STATE_JUMPING_RIGHT: 'jumping-left.gif',  # 复用左跳动画，翻转使用
            PET_STATE_WAITING: 'waiting.gif',
            PET_STATE_THINKING: 'rewiew.gif',  # 注意原文件名拼写
            PET_STATE_HAPPY: 'waving.gif',
            PET_STATE_SAD: 'failed.gif',
        }
        
        # 存储所有帧（防止垃圾回收）
        self.all_frames = {}
        
        # 需要翻转的状态
        flip_states = {PET_STATE_WALKING_LEFT, PET_STATE_JUMPING_RIGHT}
        
        # 特殊处理：running-right.gif 前4帧用于移动，后面的帧用于 idle4
        running_right_path = os.path.join(gif_dir, 'running-right.gif')
        if os.path.exists(running_right_path):
            try:
                img = Image.open(running_right_path)
                all_frames = []
                all_pil_frames = []  # 保存原始PIL帧用于翻转
                try:
                    while True:
                        frame = img.copy()
                        all_pil_frames.append(frame.copy())  # 保存原始帧
                        frame = frame.resize((120, 120), Image.Resampling.LANCZOS)
                        photo = PIL.ImageTk.PhotoImage(frame)
                        all_frames.append(photo)
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
                
                # 前4帧用于移动
                walking_pil_frames = all_pil_frames[:4]
                walking_frames = all_frames[:4]
                # 后面的帧用于 idle4
                idle4_frames = all_frames[4:] if len(all_frames) > 4 else []
                
                # 加载移动帧（向右走不翻转）
                self.all_frames[PET_STATE_WALKING_RIGHT] = walking_frames
                self.animator.load_frames(PET_STATE_WALKING_RIGHT, walking_frames)
                
                # 加载移动帧（向左走翻转）
                flipped_walking = []
                for pil_frame in walking_pil_frames:
                    flipped = pil_frame.transpose(Image.FLIP_LEFT_RIGHT)
                    flipped = flipped.resize((120, 120), Image.Resampling.LANCZOS)
                    photo = PIL.ImageTk.PhotoImage(flipped)
                    flipped_walking.append(photo)
                self.all_frames[PET_STATE_WALKING_LEFT] = flipped_walking
                self.animator.load_frames(PET_STATE_WALKING_LEFT, flipped_walking)
                
                # 加载 idle4 帧
                if idle4_frames:
                    self.all_frames['idle4'] = idle4_frames
                    self.animator._idle_frames_list.append(idle4_frames)
                    print(f"[LOAD] running-right.gif: 前4帧用于移动，后{len(idle4_frames)}帧用于idle4")
            except Exception as e:
                print(f"[LOAD] 处理 running-right.gif 失败: {e}")
        
        # 加载所有状态的帧
        for state, gif_files in gif_mapping.items():
            # 跳过已经处理的 walking 状态
            if state in [PET_STATE_WALKING_LEFT, PET_STATE_WALKING_RIGHT]:
                continue
            
            # idle 可能有多个文件
            if isinstance(gif_files, str):
                gif_files = [gif_files]
            
            all_state_frames = []
            
            for gif_file in gif_files:
                gif_path = os.path.join(gif_dir, gif_file)
                
                if os.path.exists(gif_path):
                    try:
                        # 打开GIF并提取所有帧
                        img = Image.open(gif_path)
                        frames = []
                        
                        try:
                            while True:
                                # 复制当前帧
                                frame = img.copy()
                                
                                # 如果需要水平翻转
                                if state in flip_states:
                                    frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
                                
                                # 调整大小
                                frame = frame.resize((120, 120), Image.Resampling.LANCZOS)
                                # 强制透明颜色 没有用反而会改变颜色导致透明度问题
                                #frame = self.force_transparent_color(frame)
                                
                                # 转换为PhotoImage
                                photo = PIL.ImageTk.PhotoImage(frame)
                                frames.append(photo)
                                # 下一帧
                                img.seek(img.tell() + 1)
                        except EOFError:
                            pass  # 到达GIF末尾
                        
                        # idle 状态：每个文件单独加载，让 _idle_frames_list 有多个元素
                        if state == PET_STATE_IDLE:
                            self.animator.load_frames(PET_STATE_IDLE, frames)
                            self.all_frames[f'{state}_{gif_file}'] = frames
                        else:
                            all_state_frames.extend(frames)
                        print(f"[LOAD] 加载成功: {gif_file} ({len(frames)} 帧)")
                    except Exception as e:
                        print(f"[LOAD] 加载失败: {gif_file}, 错误: {e}")
                else:
                    print(f"[LOAD] 文件不存在: {gif_file}，跳过...")
            
            # 非 idle 状态：保存合并后的帧
            if all_state_frames and state != PET_STATE_IDLE:
                self.all_frames[state] = all_state_frames
                self.animator.load_frames(state, all_state_frames)
            elif state != PET_STATE_IDLE:
                print(f"[LOAD] 没有帧可加载: {state}")
        
        # 设置默认帧
        idle_frames = self.animator.frames.get(PET_STATE_IDLE, [])
        if idle_frames:
            self.pet_label.configure(image=idle_frames[0])
            self.animator.set_state(PET_STATE_IDLE)
    
    
    def _setup_drag_drop(self):
        """设置拖拽功能"""
        try:
            # 检查是否使用的是TkinterDnD窗口
            if hasattr(self.root, 'drop_target_register'):
                self.root.drop_target_register('DND_Files')
                self.root.dnd_bind('<<Drop>>', self._on_drop)
        except Exception as e:
            # 拖拽功能不可用，静默忽略
            pass

    def _on_drop(self, event):
        """处理文件拖拽事件"""
        # 更新最后互动时间
        self.last_interaction_time = datetime.now()
        
        try:
            # 获取拖拽的文件路径
            file_path = event.data.strip()
            # 去除可能的大括号
            if file_path.startswith('{') and file_path.endswith('}'):
                file_path = file_path[1:-1]
            
            # 处理可能的多个文件路径
            file_path = file_path.split()[0] if ' ' in file_path else file_path
            
            # 检查是否是文件
            if os.path.isfile(file_path):
                self._open_dropped_file(file_path)
        except Exception as e:
            self._update_bubble(f"拖拽文件失败: {str(e)}", PET_STATE_SAD)

    def _open_dropped_file(self, filepath):
        """打开拖拽的文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            self.code_text.delete('1.0', 'end')
            self.code_text.insert('1.0', content)
            self.filename = os.path.basename(filepath)
            self._update_bubble(f"📂 已加载: {self.filename}", PET_STATE_HAPPY)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")

    def _show_settings(self):
        """显示设置对话框"""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("⚙ 设置")
        settings_win.geometry("400x300")
        settings_win.configure(bg='#2D2D2D')
        settings_win.resizable(False, False)

        tk.Label(settings_win, text="🔧 API设置", font=('Arial', 12, 'bold'),
                bg='#2D2D2D', fg='white').pack(pady=10)

        # API Key
        tk.Label(settings_win, text="DeepSeek API Key:", bg='#2D2D2D', fg='white').pack(anchor='w', padx=20, pady=5)
        api_key_var = tk.StringVar(value=os.environ.get("DEEPSEEK_API_KEY", ""))
        api_key_entry = tk.Entry(settings_win, textvariable=api_key_var, width=40, show='*')
        api_key_entry.pack(padx=20)

        # API URL
        tk.Label(settings_win, text="API URL:", bg='#2D2D2D', fg='white').pack(anchor='w', padx=20, pady=5)
        api_url_var = tk.StringVar(value=getattr(self.checker, 'api_url', 'https://api.deepseek.com/chat/completions'))
        api_url_entry = tk.Entry(settings_win, textvariable=api_url_var, width=40)
        api_url_entry.pack(padx=20)

        # 使用AI开关
        use_ai_var = tk.BooleanVar(value=self.checker.use_ai)
        tk.Checkbutton(settings_win, text="启用AI分析（需要API Key）",
                      variable=use_ai_var, bg='#2D2D2D', fg='white',
                      selectcolor='#2D2D2D').pack(pady=10)

        def save_settings():
            self.checker.api_key = api_key_var.get()
            self.checker.api_url = api_url_var.get()
            self.checker.use_ai = use_ai_var.get()
            settings_win.destroy()
            self.animator.set_state(PET_STATE_HAPPY)

        tk.Button(settings_win, text="保存", command=save_settings,
                 bg='#4CAF50', fg='white', padx=20).pack(pady=20)
    
    def _show_about(self):
        """显示关于对话框"""
        messagebox.showinfo("💡 关于", 
                          f"🐛 Debug Pet v{VERSION}\n\n"
                          f"一个可爱的桌面宠物编程助手\n\n"
                          f"功能：\n"
                          f"• 支持代码静态检测\n"
                          f"• AI智能分析（需配置API Key）\n"
                          f"• 错误高亮和修复建议\n\n"
                          f"使用方法：\n"
                          f"• 右键点击宠物查看菜单\n"
                          f"• 点击\"检查代码\"开始分析\n"
                          f"• 拖拽宠物到任意位置\n"
                          f"• 宠物会自动在屏幕上走动")
    
    def _quit_app(self, event=None):
        """退出应用"""
        # 停止所有动画和定时器
        if self.animator:
            self.animator.stop()
        for job_id in self.after_jobs[:]:
            try:
                self.root.after_cancel(job_id)
            except:
                pass
        self.after_jobs.clear()
        
        # 隐藏并销毁右键菜单
        if hasattr(self, 'context_menu'):
            try:
                self.context_menu.unpost()
                self.context_menu.destroy()
            except:
                pass
        
        # 退出应用
        def final_exit():
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
            os._exit(0)
        
        self.root.withdraw()
        self.root.after(200, final_exit)
    
    def _update_bubble(self, message, state=PET_STATE_IDLE):
        """更新气泡消息"""
        # 如果没有checker_window，直接返回
        if not hasattr(self, 'checker_window') or not self.checker_window.winfo_exists():
            return
        try:
            if hasattr(self, 'bubble_label'):
                color = STATE_COLORS.get(state, '#E8F5E9')
                self.bubble_label.configure(text=message, bg=color)
                self.animator.set_state(state)
        except:
            pass

    def _check_code(self):
        """检查代码"""
        code = self.code_text.get('1.0', 'end-1c').strip()
        if not code:
            self._update_bubble("请先输入或拖拽代码！", PET_STATE_SAD)
            return

        self.code_content = code

        # 显示思考动画
        self._update_bubble("🤔 正在分析代码...", PET_STATE_THINKING)
        self.check_btn.configure(state='disabled')

        # 在后台线程中运行检查
        def do_check():
            errors = self.checker.check(code, self.filename, self.checker.use_ai)

            # 回到主线程更新UI
            job_id = self.root.after(0, lambda: self._on_check_complete(errors))
            self.after_jobs.append(job_id)

        thread = threading.Thread(target=do_check)
        thread.start()

    def _on_check_complete(self, errors):
        """检查完成后的UI更新"""
        self.errors = errors
        self.check_btn.configure(state='normal')

        if not errors:
            self._update_bubble("🎉 太棒了！代码没有发现错误！", PET_STATE_HAPPY)
            self.error_listbox.delete(0, 'end')
            return

        # 显示错误
        self.error_listbox.delete(0, 'end')
        for i, err in enumerate(errors):
            msg = f"第{err['line']}行: {err['message']}"
            self.error_listbox.insert(i, msg)

        # 选中第一个错误
        if errors:
            self.error_listbox.select_set(0)
            self.current_error_index = 0
            self._on_error_select(None)

    def _on_error_select(self, event):
        """选中错误项"""
        selection = self.error_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx < len(self.errors):
            err = self.errors[idx]
            self.current_error_index = idx

            # 高亮对应行
            self._highlight_line(err['line'])

            # 更新气泡显示修复建议
            fix = err.get('fix', '请手动检查该行代码')
            message = f"📍 第{err['line']}行 {err.get('type', '').upper()}\n💡 {fix}"
            self._update_bubble(message, PET_STATE_WALKING)

    def _highlight_line(self, line_num):
        """高亮显示指定行"""
        self.code_text.tag_remove('highlight', '1.0', 'end')

        try:
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            self.code_text.tag_add('highlight', line_start, line_end)
            self.code_text.tag_config('highlight', background='#FFEB3B', foreground='#000')
            self.code_text.see(line_start)
        except:
            pass

    def _clear_all(self):
        """清空所有内容"""
        self.code_text.delete('1.0', 'end')
        self.error_listbox.delete(0, 'end')
        self.errors = []
        self.code_content = ""
        self.filename = "code.py"
        self._update_bubble("👋 拖拽代码文件到窗口，我来帮你检查！", PET_STATE_IDLE)

    def _open_file(self):
        """打开文件"""
        filepath = filedialog.askopenfilename(
            title="选择代码文件",
            filetypes=[
                ("所有代码文件", "*.py *.js *.java *.c *.cpp *.h *.go *.rs *.ts *.html"),
                ("Python文件", "*.py"),
                ("JavaScript文件", "*.js"),
                ("Java文件", "*.java"),
                ("所有文件", "*.*")
            ]
        )

        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.code_text.delete('1.0', 'end')
                self.code_text.insert('1.0', content)
                self.filename = os.path.basename(filepath)
                self._update_bubble(f"📂 已加载: {self.filename}", PET_STATE_HAPPY)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件: {str(e)}")

    def run(self):
        """启动应用"""
        # 设置窗口图标（如果有）
        self.root.mainloop()


# ============== 入口 ==============
if __name__ == "__main__":
    # 使用 ASCII 字符避免编码问题
    print("=" * 45)
    print(f"  Debug Pet v{VERSION} - 桌面宠物Debugger")
    print("=" * 45)
    print("  特点:")
    print("  - 可爱的桌面宠物交互界面")
    print("  - 支持拖拽/打开代码文件")
    print("  - pylint静态检测 + AI智能分析")
    print("  - 错误行高亮 + 修复建议气泡")
    print("=" * 45)
    print("  使用方法:")
    print("  1. 右键点击宠物打开菜单")
    print("  2. 点击'检查代码'开始分析")
    print("  3. 可以拖拽宠物到任意位置")
    print("=" * 45)
    print("  环境变量(可选):")
    print("  DEEPSEEK_API_KEY - 启用AI分析")
    print("=" * 45)
    
    app = DebugPetApp()
    app.run()
