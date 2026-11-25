#!/usr/bin/env python3
"""
Debug Pet - 桌面宠物Debugger (PyQt5 版本)
一切UI以粉色紫红蓝主题背景展示
"""

import sys
import os
import random
import subprocess
import tempfile
import re
import json
import html
import uuid
import math
from datetime import datetime

from debugpet.services.api import ModelApiClient
from debugpet.services.behavior import BehaviorState, DiagnosticBehavior
from debugpet.services.config import ConfigService, ModelConfig
from debugpet.services.diagnostics import DiagnosticEvent, DiagnosticGate, Severity
from debugpet.services.ipc import DiagnosticIpcServer
from debugpet.services.memory import NullMemoryService, SQLiteMemoryService
from debugpet.services.screens import DesktopRect, clamp_window, nearest_rect, union_rects
from debugpet.services.visual_locator import locate_vscode_decoration
from debugpet.services.window_locator import (
    enable_per_monitor_dpi_awareness,
    find_vscode_anchor,
    find_vscode_window,
    is_foreground_window,
)
from debugpet.services.workers import ApiRequestWorker

# PyQt5 导入
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QMenu, QMessageBox,
    QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QScrollArea, QFrame, QDialog, QLineEdit, QFileDialog, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog
)
from PyQt5.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation, 
    QEasingCurve, QRect, pyqtSignal, QThread
)
from PyQt5.QtGui import (
    QMovie, QPixmap, QImage, QPainter, QPen, QColor,
    QCursor, QIcon, QFont, QKeySequence, QPainterPath, QFontMetrics
)
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

# 尝试导入 requests（用于 AI 检测）
try:
    import requests
except ImportError:
    requests = None


# ============== 配置 ==============
APP_NAME = "Debug Pet"
VERSION = "1.0.0"
GIF_DIR = "miaomiao-all-actions"

# 获取资源文件路径（支持 PyInstaller 打包）
def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

GIF_DIR_FULL = get_resource_path(GIF_DIR)

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
PET_STATE_FAILED = "failed"

# GIF 文件映射
GIF_FILES = {
    PET_STATE_IDLE: ['idle1.gif', 'idle2.gif', 'idle3.gif'],
    PET_STATE_WALKING_LEFT: 'running-right.gif',
    PET_STATE_WALKING_RIGHT: 'running-right.gif',
    PET_STATE_JUMPING_LEFT: 'jumping-left.gif',
    PET_STATE_JUMPING_RIGHT: 'jumping-left.gif',
    PET_STATE_THINKING: 'rewiew.gif',
    PET_STATE_HAPPY: 'waving.gif',
    PET_STATE_SAD: 'failed.gif',
    PET_STATE_WAITING: 'waiting.gif',
    PET_STATE_FAILED: 'failed.gif',
}

# 气泡颜色
STATE_COLORS = {
    PET_STATE_IDLE: "#CE93D8",      # 紫粉色
    PET_STATE_WALKING: "#AB47BC",   # 紫色
    PET_STATE_THINKING: "#90CAF9",  # 蓝色
    PET_STATE_HAPPY: "#F48FB1",     # 粉色
    PET_STATE_SAD: "#9FA8DA",       # 蓝紫色
    PET_STATE_WAITING: "#EF5350",   # 红色
    PET_STATE_FAILED: "#E57373",    # 红色系
}

STATE_BUBBLE_BACKGROUNDS = {
    PET_STATE_IDLE: "#FCE8F3",
    PET_STATE_WALKING: "#F3E5F5",
    PET_STATE_WALKING_LEFT: "#F3E5F5",
    PET_STATE_WALKING_RIGHT: "#F3E5F5",
    PET_STATE_JUMPING_LEFT: "#EDE7F6",
    PET_STATE_JUMPING_RIGHT: "#EDE7F6",
    PET_STATE_THINKING: "#E3F2FD",
    PET_STATE_HAPPY: "#FCE4EC",
    PET_STATE_SAD: "#E8EAF6",
    PET_STATE_WAITING: "#FFEBEE",
    PET_STATE_FAILED: "#FFCDD2",
}


class CloudBubbleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.background_color = QColor("#FCE8F3")
        self.border_color = QColor("#CE93D8")

    def set_colors(self, background, border):
        self.background_color = QColor(background)
        self.border_color = QColor(border)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        width = max(1, self.width() - 1)
        height = max(1, self.height() - 1)
        path = QPainterPath()
        path.moveTo(width * 0.13, height * 0.78)
        path.cubicTo(width * 0.01, height * 0.72, width * 0.01, height * 0.43,
                     width * 0.16, height * 0.38)
        path.cubicTo(width * 0.13, height * 0.18, width * 0.33, height * 0.08,
                     width * 0.43, height * 0.20)
        path.cubicTo(width * 0.53, height * 0.02, width * 0.75, height * 0.10,
                     width * 0.76, height * 0.27)
        path.cubicTo(width * 0.94, height * 0.23, width * 0.99, height * 0.48,
                     width * 0.88, height * 0.59)
        path.cubicTo(width * 0.98, height * 0.76, width * 0.83, height * 0.93,
                     width * 0.68, height * 0.84)
        path.cubicTo(width * 0.57, height * 0.98, width * 0.36, height * 0.94,
                     width * 0.31, height * 0.84)
        path.cubicTo(width * 0.23, height * 0.92, width * 0.14, height * 0.88,
                     width * 0.13, height * 0.78)
        path.closeSubpath()
        painter.fillPath(path, self.background_color)
        painter.setPen(QPen(self.border_color, 3))
        painter.drawPath(path)


# ============== PyQt5 主窗口类 ==============
class PetWindow(QWidget):
    """宠物主窗口 - 使用 PyQt5 实现透明背景"""
    
    def __init__(self):
        super().__init__()
        
        # 宠物位置
        self.pet_x = 100
        self.pet_y = 100
        # The process uses one coordinate system: native Windows pixels.
        self.pet_physical_width = 300
        self.pet_physical_height = 300
        self.pet_width = self.pet_physical_width
        self.pet_height = self.pet_physical_height
        
        # 移动相关
        self.is_moving = False
        self.is_dragging = False
        self.walk_direction = 1
        self._motion_token = 0
        self._motion_mode = None
        
        # 拖拽速度
        self.drag_velocity_x = 0
        self.drag_velocity_y = 0
        self.drag_last_x = 0
        self.drag_last_y = 0
        self.drag_last_time = datetime.now()
        
        # 互动时间
        self.last_interaction_time = datetime.now()
        
        # 初始化 UI（包含加载动画）
        self._init_ui()
        
        # 设置定时器
        self._setup_timers()

        # VSCode diagnostics use authenticated loopback IPC. No source is
        # required for the local reaction path.
        self.diagnostic_gate = DiagnosticGate()
        self.diagnostic_behavior = DiagnosticBehavior()
        self.locator_worker = None
        self.current_diagnostic = None
        self.resolution_timers = {}
        self.ipc_server = DiagnosticIpcServer(parent=self)
        self.ipc_server.diagnostic_received.connect(self._on_diagnostic_event)
        self.ipc_server.protocol_error.connect(
            lambda error: print(f"[IPC] {error}")
        )
        if not self.ipc_server.start():
            print("[IPC] failed to start")
        
        # 启动移动定时器
        self.move_timer.start()
    
    def _init_ui(self):
        """初始化 UI"""
        # 窗口配置
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.Window | 
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |   # 置顶
            Qt.Tool |                  # 不在任务栏显示
            Qt.WindowDoesNotAcceptFocus
        )
        
        # 设置透明背景（关键！）
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        # 设置窗口大小和位置
        self.setFixedSize(self.pet_width, self.pet_height)
        self.move(self.pet_x, self.pet_y)
        
        # 创建宠物标签
        self.pet_label = QLabel(self)
        self.pet_label.setGeometry(0, 0, self.pet_width, self.pet_height)
        self.pet_label.setFixedSize(self.pet_width, self.pet_height)
        self.pet_label.setAlignment(Qt.AlignCenter)
        self.pet_label.setScaledContents(True)
        
        # 设置鼠标跟踪
        self.setMouseTracking(True)
        self.pet_label.setMouseTracking(True)
        
        # 设置光标
        self.setCursor(QCursor(Qt.OpenHandCursor))
        
        # 气泡窗口（独立窗口，避免被裁剪）
        self.bubble_window = CloudBubbleWindow()
        self.bubble_window.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.bubble_window.setAttribute(Qt.WA_TranslucentBackground)
        self.bubble_window.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        self.bubble_label = QLabel(self.bubble_window)
        self.bubble_label.setAlignment(Qt.AlignCenter)
        self.bubble_label.setTextFormat(Qt.PlainText)
        self.bubble_label.setWordWrap(True)
        self.bubble_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._bubble_float_phase = 0.0
        self._update_bubble_position_timer = QTimer(self)
        self._update_bubble_position_timer.timeout.connect(
            self._update_bubble_position
        )
        self._update_bubble_position_timer.setInterval(50)
        
        self.bubble_window.hide()
        
        # 祁煜语录列表
        self._init_qi_yu_quotes()
        
        # 先加载动画，再设置状态
        self.current_state = PET_STATE_IDLE
        self.current_sub_index = 0
        self.idle_switch_count = 0
        self.last_idle_switch_time = datetime.now()
        self.idle_movies = []
        
        # 移动相关
        self.target_x = 0
        self.target_y = 0
        self.walk_direction = 1
        self.move_speed = 3
        
        # 加载动画
        self._load_pet_frames()
        
        # 加载完成后设置初始状态
        self._set_state(PET_STATE_IDLE)
        
        # 开始宠物行为
        self._schedule_next_action()
        
        # 开始气泡说话
        self._schedule_say_quote()
        
        # 启动时打招呼
        QTimer.singleShot(1500, self._greet_on_start)

    def _load_pet_frames(self):
        """加载宠物动画帧 - 支持翻转"""
        from PIL import Image
        
        # 需要翻转的状态
        flip_states = {PET_STATE_WALKING_LEFT, PET_STATE_JUMPING_RIGHT}
        
        # 存储所有帧
        self.all_frames = {}
        
        # 加载 idle GIF
        self.movie = QMovie()
        self.pet_label.setMovie(self.movie)
        
        idle_gif = os.path.join(GIF_DIR_FULL, 'idle1.gif')
        if os.path.exists(idle_gif):
            self.movie.setFileName(idle_gif)
            self.movie.start()
        
        # 加载所有 idle GIF
        for gif_name in GIF_FILES[PET_STATE_IDLE]:
            gif_path = os.path.join(GIF_DIR_FULL, gif_name)
            if os.path.exists(gif_path):
                try:
                    image = Image.open(gif_path)
                    frames = []
                    try:
                        while True:
                            frame = image.copy().convert('RGBA').resize(
                                (self.pet_physical_width, self.pet_physical_height),
                                Image.Resampling.LANCZOS,
                            )
                            data = frame.tobytes('raw', 'RGBA')
                            qimg = QImage(
                                data, frame.width, frame.height,
                                QImage.Format_RGBA8888,
                            )
                            frames.append(QPixmap.fromImage(qimg))
                            image.seek(image.tell() + 1)
                    except EOFError:
                        pass
                    if frames:
                        self.idle_movies.append((gif_name, frames))
                except Exception as error:
                    print(f"[LOAD] idle failed: {gif_name}: {error}")
        
        print(f"[LOAD] 加载了 {len(self.idle_movies)} 个 idle 动画")
        
        # 特殊处理：running-right.gif 前4帧用于移动，后面的帧用于 idle4
        running_right_path = os.path.join(GIF_DIR_FULL, 'running-right.gif')
        if os.path.exists(running_right_path):
            try:
                img = Image.open(running_right_path)
                all_pil_frames = []
                try:
                    while True:
                        frame = img.copy()
                        all_pil_frames.append(frame)
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
                
                # 前4帧用于移动
                walking_pil_frames = all_pil_frames[:4]
                # 后面的帧用于 idle4
                idle4_pil_frames = all_pil_frames[4:] if len(all_pil_frames) > 4 else []
                
                # 加载移动帧（向右走不翻转）
                walking_frames_right = []
                for pil_frame in walking_pil_frames:
                    frame = pil_frame.resize(
                        (self.pet_physical_width, self.pet_physical_height),
                        Image.Resampling.LANCZOS,
                    )
                    frame = frame.convert('RGBA')
                    data = frame.tobytes('raw', 'RGBA')
                    qimg = QImage(data, frame.width, frame.height, QImage.Format_RGBA8888)
                    walking_frames_right.append(QPixmap.fromImage(qimg))
                
                self.all_frames[PET_STATE_WALKING_RIGHT] = walking_frames_right
                print(f"[LOAD] {PET_STATE_WALKING_RIGHT}: 前4帧 ({len(walking_frames_right)} 帧)")
                
                # 加载移动帧（向左走翻转）
                walking_frames_left = []
                for pil_frame in walking_pil_frames:
                    frame = pil_frame.transpose(Image.FLIP_LEFT_RIGHT)
                    frame = frame.resize(
                        (self.pet_physical_width, self.pet_physical_height),
                        Image.Resampling.LANCZOS,
                    )
                    frame = frame.convert('RGBA')
                    data = frame.tobytes('raw', 'RGBA')
                    qimg = QImage(data, frame.width, frame.height, QImage.Format_RGBA8888)
                    walking_frames_left.append(QPixmap.fromImage(qimg))
                
                self.all_frames[PET_STATE_WALKING_LEFT] = walking_frames_left
                print(f"[LOAD] {PET_STATE_WALKING_LEFT}: 前4帧翻转 ({len(walking_frames_left)} 帧)")
                
                # 加载 idle4 帧
                if idle4_pil_frames:
                    idle4_frames = []
                    for pil_frame in idle4_pil_frames:
                        frame = pil_frame.resize(
                            (self.pet_physical_width, self.pet_physical_height),
                            Image.Resampling.LANCZOS,
                        )
                        frame = frame.convert('RGBA')
                        data = frame.tobytes('raw', 'RGBA')
                        qimg = QImage(data, frame.width, frame.height, QImage.Format_RGBA8888)
                        idle4_frames.append(QPixmap.fromImage(qimg))
                    
                    self.all_frames['idle4'] = idle4_frames
                    # 添加到 idle_movies 用于随机切换
                    self.idle_movies.append(('idle4.gif', idle4_frames))
                    print(f"[LOAD] idle4: running-right.gif后{len(idle4_frames)}帧用于idle4")
            except Exception as e:
                print(f"[LOAD] 处理 running-right.gif 失败: {e}")
        
        # 加载其他状态的帧（支持翻转）
        for state, gif_name in GIF_FILES.items():
            if state == PET_STATE_IDLE:
                continue
            # 跳过已经处理的 walking 状态
            if state in [PET_STATE_WALKING_LEFT, PET_STATE_WALKING_RIGHT]:
                continue
            
            if isinstance(gif_name, list):
                gif_name = gif_name[0] if gif_name else None
            
            if gif_name:
                gif_path = os.path.join(GIF_DIR_FULL, gif_name)
                if os.path.exists(gif_path):
                    try:
                        # 使用 PIL 加载 GIF
                        img = Image.open(gif_path)
                        frames = []
                        
                        try:
                            while True:
                                frame = img.copy()
                                
                                # 如果需要翻转
                                if state in flip_states:
                                    frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
                                
                                # 调整大小
                                frame = frame.resize(
                                    (self.pet_physical_width, self.pet_physical_height),
                                    Image.Resampling.LANCZOS,
                                )
                                
                                # 转换为 QPixmap
                                if frame.mode == 'RGBA':
                                    data = frame.tobytes('raw', 'RGBA')
                                    qimg = QImage(data, frame.width, frame.height, QImage.Format_RGBA8888)
                                else:
                                    frame = frame.convert('RGBA')
                                    data = frame.tobytes('raw', 'RGBA')
                                    qimg = QImage(data, frame.width, frame.height, QImage.Format_RGBA8888)
                                
                                pixmap = QPixmap.fromImage(qimg)
                                frames.append(pixmap)
                                
                                img.seek(img.tell() + 1)
                        except EOFError:
                            pass
                        
                        self.all_frames[state] = frames
                        print(f"[LOAD] {state}: {gif_name} ({len(frames)} 帧, 翻转={state in flip_states})")
                    except Exception as e:
                        print(f"[LOAD] 加载失败: {gif_name}, 错误: {e}")
        
        # 创建帧动画定时器
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._update_frame)
        self.current_frame_index = 0
    
    def _update_frame(self):
        """更新动画帧"""
        # 检查是否是 idle4
        if self.current_state == PET_STATE_IDLE and self.current_sub_index < len(self.idle_movies):
            name, movie = self.idle_movies[self.current_sub_index]
            if isinstance(movie, list):
                self.current_frame_index = (self.current_frame_index + 1) % len(movie)
                self._display_pixmap(movie[self.current_frame_index])
                return
        
        # 其他状态使用 all_frames
        if self.current_state in self.all_frames:
            frames = self.all_frames[self.current_state]
            if frames:
                self.current_frame_index = (self.current_frame_index + 1) % len(frames)
                self._display_pixmap(frames[self.current_frame_index])

    def _display_pixmap(self, pixmap):
        """Display the single-sampled physical frame without DPR remapping."""
        self.pet_label.setPixmap(pixmap)
    
    def _setup_timers(self):
        """设置定时器"""
        # 移动定时器
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._on_move_timer)
        self.move_timer.setInterval(50)
        
        # idle 切换定时器
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._check_idle_switch)
        self.idle_timer.setInterval(200)
        self.idle_timer.start()
        
        # 等待动画定时器
        self.waiting_timer = QTimer(self)
        self.waiting_timer.timeout.connect(self._check_waiting)
        self.waiting_timer.setInterval(10000)  # 每 10 秒检查一次
        self.waiting_timer.start()
        
        # 抛物线动画定时器
        self.parabola_timer = QTimer(self)
        self.parabola_timer.timeout.connect(self._animate_parabola)
    
    def _set_state(self, state):
        motion_mode = getattr(self, '_motion_mode', None)
        motion_states = {
            'walk': {PET_STATE_WALKING_LEFT, PET_STATE_WALKING_RIGHT},
            'jump': {PET_STATE_JUMPING_LEFT, PET_STATE_JUMPING_RIGHT},
            'parabola': {PET_STATE_JUMPING_LEFT, PET_STATE_JUMPING_RIGHT},
        }
        if motion_mode and state not in motion_states.get(motion_mode, set()):
            return
        """设置宠物状态"""
        if state == self.current_state and state != PET_STATE_IDLE:
            return
        
        self.current_state = state
        
        # 切换到 idle 状态时停止移动
        self._switch_animation(state)
        
        # idle 状态重置切换计时器
        if state == PET_STATE_IDLE:
            self.last_idle_switch_time = datetime.now()
            self.idle_switch_count = 0
    
    def _switch_animation(self, state):
        """切换动画"""
        if state == PET_STATE_IDLE and self.idle_movies:
            # idle 状态使用 QMovie 或帧动画
            if self.current_sub_index < len(self.idle_movies):
                name, movie = self.idle_movies[self.current_sub_index]
                
                # 检查是否是 idle4（帧动画而不是 QMovie）
                if isinstance(movie, list):
                    # idle4 使用帧动画
                    self.movie.stop()
                    self.frame_timer.start(100)
                    self.current_frame_index = 0
                    self._display_pixmap(movie[0])
                    print(f"[ANIM] 切换到 idle4 (帧动画)")
                else:
                    # 其他 idle 使用 QMovie
                    self.movie.stop()
                    self.movie.setFileName(movie.fileName())
                    self.movie.start()
                    self.pet_label.setMovie(self.movie)
                    self.frame_timer.stop()
                    print(f"[ANIM] 切换到 idle: {name}")
        elif state in self.all_frames:
            # 其他状态使用帧动画
            self.movie.stop()
            self.frame_timer.start(100)  # 100ms 切换帧
            self.current_frame_index = 0
            frames = self.all_frames[state]
            if frames:
                self._display_pixmap(frames[0])
                print(f"[ANIM] 切换到 {state}")
        else:
            # 没有帧，使用默认 idle
            gif_name = GIF_FILES.get(state)
            if isinstance(gif_name, list):
                gif_name = gif_name[0] if gif_name else None
            
            if gif_name:
                gif_path = os.path.join(GIF_DIR_FULL, gif_name)
                if os.path.exists(gif_path):
                    self.frame_timer.stop()
                    self.movie.stop()
                    self.movie.setFileName(gif_path)
                    self.movie.start()
                    self.pet_label.setMovie(self.movie)
                    print(f"[ANIM] 切换到 {state}: {gif_name}")
    
    def _check_idle_switch(self):
        """检查是否切换 idle 动画"""
        if self.current_state != PET_STATE_IDLE or not self.idle_movies:
            return
        
        # 检查时间间隔
        now = datetime.now()
        elapsed = (now - self.last_idle_switch_time).total_seconds() * 1000
        
        if elapsed < 7000:  # 7 秒间隔
            return
        
        # 30% 概率切换
        if random.random() < 0.3:
            # 随机选择另一个 idle
            new_index = random.randint(0, len(self.idle_movies) - 1)
            if new_index != self.current_sub_index:
                self.current_sub_index = new_index
                self.last_idle_switch_time = now
                
                name, movie = self.idle_movies[self.current_sub_index]
                
                # 检查是否是 idle4（帧动画而不是 QMovie）
                if isinstance(movie, list):
                    # idle4 使用帧动画
                    self.movie.stop()
                    self.frame_timer.start(100)
                    self.current_frame_index = 0
                    self._display_pixmap(movie[0])
                    print(f"[ANIM] 切换到 idle4 (帧动画)")
                else:
                    # 其他 idle 使用 QMovie
                    self.frame_timer.stop()
                    self.movie.stop()
                    self.movie.setFileName(movie.fileName())
                    self.movie.start()
                    self.pet_label.setMovie(self.movie)
                    print(f"[ANIM] 切换到 idle: {name}")
    
    def _check_waiting(self):
        """检查是否显示等待动画"""
        if self._diagnostic_busy():
            return
        if self.current_state != PET_STATE_IDLE:
            return
        
        # 检查无互动时间
        now = datetime.now()
        idle_time = (now - self.last_interaction_time).total_seconds()
        
        if idle_time >= 60 and random.random() < 0.4:
            # 显示等待动画 5-7 秒
            self._set_state(PET_STATE_WAITING)
            
            # 显示抱怨语句
            if self.qi_yu_quotes.get('complaint'):
                quote = random.choice(self.qi_yu_quotes['complaint'])
                print(f"[WAITING] {quote}")
                self._update_bubble(quote, PET_STATE_WAITING)
            
            waiting_duration = random.randint(5000, 7000)
            QTimer.singleShot(waiting_duration, lambda: self._set_state(PET_STATE_IDLE))
    
    def _schedule_next_action(self):
        """调度下一个动作"""
        delay = random.randint(5000, 15000)  # 5-15秒后执行
        QTimer.singleShot(delay, self._random_action)
    
    def _random_action(self):
        """随机动作"""
        if self._diagnostic_busy():
            self._schedule_next_action()
            return
        # 如果正在移动或拖拽，不执行任何动作
        if self.is_moving or self.is_dragging:
            self._schedule_next_action()
            return
        
        action = random.choice(['move', 'idle', 'jump'])
        
        if action == 'move':
            self._start_random_walk()
        elif action == 'jump':
            self._jump()
        elif action == 'idle':
            self._set_state(PET_STATE_IDLE)
        
        self._schedule_next_action()
    
    @staticmethod
    def _screen_rect(screen):
        geometry = screen.availableGeometry()
        return DesktopRect(
            geometry.left(), geometry.top(), geometry.right(), geometry.bottom()
        )

    def _desktop_rects(self):
        return [self._screen_rect(screen) for screen in QApplication.screens()]

    def _physical_px(self, value, screen=None):
        return max(1, round(value))

    def _screen_for_position(self, x=None, y=None, width=None, height=None):
        x = int(self.pet_x if x is None else x)
        y = int(self.pet_y if y is None else y)
        width = self.pet_width if width is None else width
        height = self.pet_height if height is None else height
        point = QPoint(x + width // 2, y + height // 2)
        screen = QApplication.screenAt(point)
        if screen:
            return screen
        closest = nearest_rect(self._desktop_rects(), point.x(), point.y())
        if closest:
            for candidate in QApplication.screens():
                if self._screen_rect(candidate) == closest:
                    return candidate
        return QApplication.primaryScreen()

    def _clamp_to_virtual_desktop(self, x, y):
        bounds = union_rects(self._desktop_rects())
        if not bounds:
            return int(x), int(y)
        return clamp_window(x, y, self.pet_width, self.pet_height, bounds)

    def _begin_motion(self, mode):
        self._motion_token += 1
        self._motion_mode = mode
        self.is_moving = True
        return self._motion_token

    def _finish_motion(self, token):
        if token != self._motion_token:
            return False
        self._motion_mode = None
        self.is_moving = False
        return True

    def _cancel_motion(self):
        self._motion_token += 1
        self._motion_mode = None
        self.is_moving = False
        if hasattr(self, 'parabola_timer'):
            self.parabola_timer.stop()

    def _start_random_walk(self):
        """开始随机走动"""
        screens = QApplication.screens()
        if not screens:
            return

        # Pick from every monitor so autonomous activity can visit extensions.
        screen_geo = random.choice(screens).availableGeometry()
        
        # 随机选择目标位置
        margin = 50
        self.target_x = random.randint(
            screen_geo.left() + margin,
            max(screen_geo.left() + margin,
                screen_geo.right() - self.pet_width - margin + 1),
        )
        self.target_y = random.randint(
            screen_geo.top() + margin,
            max(screen_geo.top() + margin,
                screen_geo.bottom() - self.pet_height - margin + 1),
        )
        
        # 设置方向并更新动画状态
        if self.target_x > self.pet_x:
            self.walk_direction = 1
            self._set_state(PET_STATE_WALKING_RIGHT)
        else:
            self.walk_direction = -1
            self._set_state(PET_STATE_WALKING_LEFT)
        
        # 开始移动
        token = self._begin_motion('walk')
        self._move_step(token)
    
    def _move_step(self, token):
        """移动一步"""
        if token != self._motion_token or self._motion_mode != 'walk':
            return
        
        dx = self.target_x - self.pet_x
        dy = self.target_y - self.pet_y
        
        distance = (dx**2 + dy**2) ** 0.5
        
        if distance < 5:
            # 到达目标
            if not self._finish_motion(token):
                return
            self.pet_x = int(self.target_x)
            self.pet_y = int(self.target_y)
            self._clamp_position()
            self.move(self.pet_x, self.pet_y)
            self._set_state(PET_STATE_IDLE)
            if self.diagnostic_behavior.state == BehaviorState.NAVIGATE:
                self._on_navigation_arrived()
            return
        
        # 移动
        step = min(self.move_speed, distance)
        ratio = step / distance
        self.pet_x += dx * ratio
        self.pet_y += dy * ratio
        
        # 限制在屏幕内
        self._clamp_position()
        
        self.move(int(self.pet_x), int(self.pet_y))
        
        # 更新方向并切换动画
        if dx > 0 and self.walk_direction != 1:
            self.walk_direction = 1
            self._set_state(PET_STATE_WALKING_RIGHT)
        elif dx < 0 and self.walk_direction != -1:
            self.walk_direction = -1
            self._set_state(PET_STATE_WALKING_LEFT)
        
        # 继续移动
        QTimer.singleShot(30, lambda current=token: self._move_step(current))
    
    def _clamp_position(self):
        """限制宠物位置在屏幕内"""
        self.pet_x, self.pet_y = self._clamp_to_virtual_desktop(
            self.pet_x, self.pet_y
        )

    def _move_to_target(self, x, y):
        """Move toward an externally supplied screen target."""
        self.target_x = int(x)
        self.target_y = int(y)
        self._clamp_target()
        self.walk_direction = 1 if self.target_x > self.pet_x else -1
        self._set_state(
            PET_STATE_WALKING_RIGHT
            if self.walk_direction > 0
            else PET_STATE_WALKING_LEFT
        )
        token = self._begin_motion('walk')
        self._move_step(token)

    def _clamp_target(self):
        screen = self._screen_for_position(self.target_x, self.target_y)
        if screen:
            geometry = screen.availableGeometry()
            self.target_x, self.target_y = clamp_window(
                self.target_x,
                self.target_y,
                self.pet_width,
                self.pet_height,
                self._screen_rect(screen),
            )

    def _on_diagnostic_event(self, payload):
        print(
            f"[IPC] received uri={payload.get('uri')} line={payload.get('line')} "
            f"removed={payload.get('removed')} active={payload.get('active')} "
            f"visible={payload.get('visible')} locate={payload.get('locate')}",
            flush=True,
        )
        try:
            event = DiagnosticEvent(
                uri=str(payload["uri"]),
                version=int(payload["version"]),
                severity=Severity(int(payload["severity"])),
                message=str(payload["message"]),
                line=int(payload["line"]),
                character=int(payload["character"]),
                end_line=int(payload["end_line"]),
                end_character=int(payload["end_character"]),
                removed=bool(payload.get("removed", False)),
            )
        except (KeyError, TypeError, ValueError):
            print("[IPC] invalid diagnostic payload")
            return

        identity = event.identity
        active = bool(payload.get("active", False))
        visible = bool(payload.get("visible", False))
        locate_requested = bool(payload.get("locate", False))

        if not active:
            if self.diagnostic_behavior.task and self.diagnostic_behavior.task.identity == identity:
                self._cancel_navigation("editor-switched")
            return
        current_task = self.diagnostic_behavior.task
        if (
            not event.removed
            and current_task
            and current_task.identity == identity
            and current_task.state not in {
                BehaviorState.CANCELLED,
                BehaviorState.CELEBRATE,
            }
        ):
            return
        if not event.removed and (not visible or not locate_requested):
            print(f"[NAV] passive diagnostic: visible={visible} locate={locate_requested}")
            return
        if not self.diagnostic_gate.accept(event):
            return

        self.last_interaction_time = datetime.now()
        if event.removed:
            self._schedule_resolution_confirmation(event)
            return

        self._cancel_resolution_confirmation(event.uri)

        self._cancel_navigation("superseded")
        self.diagnostic_behavior.detect(identity)
        self.diagnostic_behavior.locating()
        self.current_diagnostic = (event, dict(payload))
        self.locator_worker = ApiRequestWorker(
            lambda: self._locate_diagnostic_target(payload), self
        )
        self.locator_worker.succeeded.connect(
            lambda result, expected=identity: self._on_target_located(expected, result)
        )
        self.locator_worker.failed.connect(
            lambda error: print(f"[NAV] locate failed: {error}")
        )
        self.locator_worker.finished.connect(self._finish_locator_worker)
        self.locator_worker.start()

    def _locate_diagnostic_target(self, payload):
        document_name = str(payload.get("document_name", ""))
        window = find_vscode_window(document_name)
        if window:
            if not is_foreground_window(window):
                return {
                    "target": None,
                    "precise": False,
                    "reason": "target VSCode window is not foreground",
                }
            marker = locate_vscode_decoration(window)
            if marker:
                # Place the pet beside, never over, the diagnostic marker.
                if marker.x - window.left > self.pet_width + 40:
                    target_x = marker.x - self.pet_width - 24
                else:
                    target_x = marker.x + 40
                target_y = marker.y - self.pet_height // 2
                return {
                    "target": (target_x, target_y),
                    "precise": True,
                    "marker": (marker.x, marker.y),
                    "confidence": marker.confidence,
                }
        fallback = find_vscode_anchor(document_name)
        return {
            "target": fallback,
            "precise": False,
            "reason": "decoration marker not found",
        }

    def _on_target_located(self, expected_identity, result):
        task = self.diagnostic_behavior.task
        if not task or task.identity != expected_identity or task.state != BehaviorState.LOCATE:
            return
        target = result.get("target")
        if not target:
            self._cancel_navigation("no-window-target")
            return
        self.diagnostic_behavior.navigate(tuple(target), precise=bool(result.get("precise")))
        print(
            f"[NAV] target={target} precise={result.get('precise')} "
            f"reason={result.get('reason', '')}"
        )
        self._move_to_target(*target)

    def _finish_locator_worker(self):
        if self.locator_worker:
            self.locator_worker.deleteLater()
            self.locator_worker = None

    def _on_navigation_arrived(self):
        task = self.diagnostic_behavior.task
        if not task or not self.current_diagnostic:
            return
        event, _payload = self.current_diagnostic
        self.diagnostic_behavior.arrived()
        self.diagnostic_behavior.report()
        severity_name = "错误" if event.severity == Severity.ERROR else "警告"
        location = f"第 {event.line + 1} 行，第 {event.character + 1} 列"
        prefix = "我找到这里了" if task.precise else "没识别到精确字段，先到编辑器旁边提醒你"
        self._set_state(
            PET_STATE_SAD if event.severity == Severity.ERROR else PET_STATE_THINKING
        )
        self._update_bubble(
            f"{prefix}：{location}的{severity_name}——{event.message}",
            PET_STATE_SAD if event.severity == Severity.ERROR else PET_STATE_THINKING,
        )
        self.diagnostic_behavior.wait()

    def _cancel_navigation(self, reason):
        if self.diagnostic_behavior.cancel(reason):
            self._cancel_motion()
            print(f"[NAV] cancelled: {reason}")

    def _schedule_resolution_confirmation(self, event):
        task = self.diagnostic_behavior.task
        if not task or task.identity != event.identity:
            return
        self._cancel_resolution_confirmation(event.uri)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda identity=event.identity, uri=event.uri: self._confirm_resolution(
                identity, uri
            )
        )
        self.resolution_timers[event.uri] = timer
        timer.start(500)

    def _cancel_resolution_confirmation(self, uri):
        timer = self.resolution_timers.pop(uri, None)
        if timer:
            timer.stop()
            timer.deleteLater()

    def _confirm_resolution(self, identity, uri):
        timer = self.resolution_timers.pop(uri, None)
        if timer:
            timer.deleteLater()
        if self.diagnostic_behavior.celebrate(identity):
            self._cancel_motion()
            self._set_state(PET_STATE_HAPPY)
            self._update_bubble("修好了！这次值得庆祝一下。", PET_STATE_HAPPY)
            QTimer.singleShot(4500, lambda: self._set_state(PET_STATE_IDLE))

    def _diagnostic_busy(self):
        return self.diagnostic_behavior.state in {
            BehaviorState.DETECT,
            BehaviorState.LOCATE,
            BehaviorState.NAVIGATE,
            BehaviorState.ARRIVE,
            BehaviorState.REPORT,
            BehaviorState.WAIT,
        }
    
    def _init_qi_yu_quotes(self):
        """初始化祁煜语录列表"""
        self.qi_yu_quotes = {
            'morning': [
                '早啊，某位喜欢赖床的保镖小姐。',
                '今天的阳光不错，适合画一幅关于你的画。',
                '早饭吃了吗？没吃的话——我可不会给你做。',
                '新的一天开始了，要不要一起去海边看日出？',
                '昨晚睡得好吗？我可是画了一整夜的画。'
            ],
            'noon': [
                '午饭时间到了，你打算吃什么？',
                '要不要一起去吃烧烤？我知道一家不错的店。',
                '午休时间，借你靠一会儿——就一小会儿。',
                '今天中午的阳光太刺眼了，还是待在画室里比较舒服。',
                '有人的肚子叫了哦，要不要我去给你买点吃的？'
            ],
            'afternoon': [
                '下午好，我的灵感源泉。',
                '要不要来画室看看我新画的作品？',
                '今天下午的海风很舒服，想不想出去走走？',
                '灵感突然来了，你能陪我一会儿吗？',
                '下午茶时间，要不要来根奶酪棒？'
            ],
            'evening': [
                '晚上好，宝宝。今天过得怎么样？',
                '今晚的星星还没你上次打翻我颜料罐时瞪我的眼睛亮。',
                '要不要一起去吃晚饭？我请客。',
                '夜幕降临后，你似乎比白天时要坦率得多。',
                '今天辛苦了，要不要靠在我肩上休息一会儿？',
                '下班后打算去哪？你的专属司机随时待命。'
            ],
            'night': [
                '这么早就说晚安可不是你的性格。',
                '明天不是还要早起？别等到起晚了的时候再跟我抱怨。',
                '夜晚的风有点冷……但也不如现在的气氛这么冷。',
                '睡吧，我会守在你身边的。',
                '晚安，我的宝贝。做个好梦。'
            ],
            'complaint': [
                '等你等了八百年，水母都会走路了，海龟都会爬树了，连鲨鱼都改吃素了，你呢？',
                '怎么才想起来找我，是什么把你的注意力吸引走了？',
                '某人今天很忙嘛，消息都沉底了。',
                '我等你等了好久，你终于想起我了？',
                '今天画廊会有一幅名叫《消失的宝宝》的新展品，嫌疑人的特征与某人的日程高度吻合。',
                '又不理我？看来我得画一幅《被遗忘的海神》了。',
                '你再不来陪我，我就要把自己关在画室里三天三夜！',
                '明明可以清楚地看看我，为什么还要效仿盲人摸象？',
                '我挠挠挠......挠挠挠......',
                '要人亲亲才能起来！',
                '走了好久了，还不回来吗？'
            ],
            'casual': [
                '最近天气凉了不少，是该多加些衣服了。',
                '想吃冰淇淋吗？我去买。',
                '折一个纸蜻蜓就能让你高兴这么久，你还真是好哄。',
                '我的脸都被你戳红了，应该拿你怎么办呢？',
                '要不要跟我去个地方？',
                '你看起来不是很精神……是我的错觉，还是你没休息好？',
                '除了触摸要不要换种感受方式？',
                '好看吗，需不需要我再靠近一点？',
                '这个世界上，没有比"独一无二"更珍贵的东西。',
                '愿深海的祝福，与你同在。',
                '喵喵喵~',
                '嘿嘿，快来抱我。'
            ]
        }
    
    def _get_time_period(self):
        """获取当前时间段"""
        hour = datetime.now().hour
        if 5 <= hour < 9:
            return 'morning'
        elif 9 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 14:
            return 'noon'
        elif 14 <= hour < 19:
            return 'afternoon'
        elif 19 <= hour < 22:
            return 'evening'
        else:
            return 'night'
    
    def _say_random_quote(self):
        """随机说出一句祁煜语录"""
        if self._diagnostic_busy():
            self._schedule_say_quote()
            return
        # 检查无互动时间
        now = datetime.now()
        idle_time = (now - self.last_interaction_time).total_seconds()
        
        # 选择语录类型
        if idle_time >= 120:
            quotes = self.qi_yu_quotes['complaint']
            print(f"[QUOTE] 抱怨模式 (无互动 {idle_time:.1f}秒)")
        else:
            time_period = self._get_time_period()
            quotes = self.qi_yu_quotes[time_period] + self.qi_yu_quotes['casual']
            print(f"[QUOTE] 正常模式 ({time_period})")
        
        # 随机选择一句
        quote = random.choice(quotes)
        
        # 显示气泡
        print(f"[QUOTE] 祁煜: {quote}")
        self._update_bubble(quote, PET_STATE_IDLE)
        
        # 设置气泡显示时间（5-7秒），然后继续调度下次说话
        display_time = random.randint(5000, 7000)
        
        def hide_and_schedule():
            self.bubble_window.hide()
            if hasattr(self, '_update_bubble_position_timer'):
                self._update_bubble_position_timer.stop()
            self._schedule_say_quote()
        
        QTimer.singleShot(display_time, hide_and_schedule)
    
    def _schedule_say_quote(self):
        """调度下次说话"""
        delay = random.randint(8000, 30000)  # 8-30秒
        QTimer.singleShot(delay, self._say_random_quote)
    
    def _greet_on_start(self):
        """启动时打招呼"""
        if self._diagnostic_busy():
            return
        time_period = self._get_time_period()
        greetings = {
            'morning': ['早啊，某位喜欢赖床的保镖小姐。', '早安，我的宝贝。'],
            'noon': ['午安，要一起吃饭吗？', '中午好，记得休息一下。'],
            'afternoon': ['下午好，今天工作顺利吗？', '下午好，宝宝小姐。'],
            'evening': ['晚上好，宝宝。今天过得怎么样？', '晚上好，想我了吗？'],
            'night': ['晚安，我的缪斯小姐。', '这么早就说晚安可不是你的性格。']
        }
        quote = random.choice(greetings.get(time_period, ['你好，保镖小姐。']))
        print(f"[GREET] {quote}")
        self._update_bubble(quote, PET_STATE_IDLE)
        
        def hide_greet():
            self.bubble_window.hide()
            if hasattr(self, '_update_bubble_position_timer'):
                self._update_bubble_position_timer.stop()
        
        QTimer.singleShot(5000, hide_greet)
    
    def _jump(self):
        """跳跃动画 - 落到屏幕底部"""
        # 如果正在移动或拖拽，不执行跳跃
        if self.is_moving or self.is_dragging:
            return
        
        screen = self._screen_for_position()
        if not screen:
            return
        
        screen_geo = screen.availableGeometry()
        
        print(f"[JUMP] 开始跳跃 from ({self.pet_x}, {self.pet_y}), direction={self.walk_direction}")
        
        # 跳跃参数
        jump_distance = random.randint(100, 300)
        jump_steps = random.randint(20, 40)
        self._jump_step = 0
        self._jump_start_x = self.pet_x
        self._jump_start_y = self.pet_y
        # 跳跃终点落到屏幕底部
        self._jump_end_y = screen_geo.bottom() - self.pet_height + 1
        token = self._begin_motion('jump')
        
        # 根据方向设置目标
        if self.walk_direction > 0:
            self._jump_target_x = self.pet_x + jump_distance
            self._set_state(PET_STATE_JUMPING_RIGHT)
        else:
            self._jump_target_x = self.pet_x - jump_distance
            self._set_state(PET_STATE_JUMPING_LEFT)
        
        # 执行跳跃动画
        self._do_jump_step(jump_steps, token)
    
    def _do_jump_step(self, total_steps, token):
        """执行跳跃的一步 - 落到屏幕底部"""
        if token != self._motion_token or self._motion_mode != 'jump':
            return
        if self._jump_step >= total_steps:
            # 跳跃结束，确保落到屏幕底部
            self.pet_y = self._jump_end_y
            self._clamp_position()
            self.move(self.pet_x, self.pet_y)
            self._finish_motion(token)
            self._set_state(PET_STATE_IDLE)
            return
        
        t = self._jump_step / total_steps
        
        # 计算 x 位置（线性移动）
        x = self._jump_start_x + (self._jump_target_x - self._jump_start_x) * t
        
        # 计算 y 位置（抛物线落到屏幕底部）
        # 抛物线方程：y = start_y + (end_y - start_y) * t^2
        # 加上一个向上的抛物线：-jump_height * 4 * t * (1 - t)
        jump_height = max(100, self._jump_start_y - self._jump_end_y) // 2
        y = self._jump_start_y + (self._jump_end_y - self._jump_start_y) * (t * t) - jump_height * 4 * t * (1 - t)
        
        # 边界检查
        self.pet_x = int(x)
        self.pet_y = int(y)
        self._clamp_position()
        self.move(self.pet_x, self.pet_y)
        
        self._jump_step += 1
        QTimer.singleShot(
            30, lambda current=token: self._do_jump_step(total_steps, current)
        )
    
    def _on_move_timer(self):
        """移动定时器回调"""
        if self.is_dragging or self.is_moving:
            # 拖拽或移动中，不自动漂移
            pass
    
    def _animate_parabola(self):
        """抛物线动画"""
        if not hasattr(self, 'parabola_data'):
            self.parabola_timer.stop()
            return
        
        data = self.parabola_data
        token = data['motion_token']
        if token != self._motion_token or self._motion_mode != 'parabola':
            self.parabola_timer.stop()
            return
        data['current_step'] += 1
        
        if data['current_step'] >= data['steps']:
            # 动画结束
            self.pet_x = int(data['end_x'])
            self.pet_y = int(data['end_y'])
            self.move(self.pet_x, self.pet_y)
            self._set_state(PET_STATE_IDLE)
            self.parabola_timer.stop()
            self._finish_motion(token)
            return
        
        t = data['current_step'] / data['steps']
        
        # 计算位置
        x = data['start_x'] + (data['end_x'] - data['start_x']) * t
        y = data['start_y'] + (data['end_y'] - data['start_y']) * t + (1 - abs(2*t - 1)) * data['height_offset']
        
        # 边界检查
        x, y = self._clamp_to_virtual_desktop(x, y)
        
        self.pet_x = int(x)
        self.pet_y = int(y)
        self.move(self.pet_x, self.pet_y)
        
        # 更新动画状态（与原文件一致）
        state = (
            PET_STATE_JUMPING_RIGHT
            if data['vx'] >= 0
            else PET_STATE_JUMPING_LEFT
        )
        self._set_state(state)
    
    def _update_bubble(self, message, state=None):
        """更新气泡消息"""
        if state:
            self._set_state(state)
        
        # 使用传入的 state 或当前状态
        state_key = state if state else self.current_state
        color = STATE_COLORS.get(state_key, "#F2F2F2")
        background = STATE_BUBBLE_BACKGROUNDS.get(state_key, "#FCE8F3")
        self._bubble_state_key = state_key
        screen = self._screen_for_position()
        font_size = self._physical_px(24, screen)
        text_font = QFont('Microsoft YaHei UI')
        text_font.setPixelSize(font_size)
        text_font.setBold(True)
        
        print(f"[BUBBLE] 消息: {message[:20]}... | 状态: {state_key} | 颜色: {color}")
        
        self.bubble_window.set_colors(background, color)
        max_text_width = self._physical_px(420, screen)
        self.bubble_label.setFont(text_font)
        self.bubble_label.setAlignment(Qt.AlignCenter)
        self.bubble_label.setStyleSheet(f"""
            background-color: transparent;
            border: none;
            color: #4A148C;
            font-family: 'Microsoft YaHei UI', 'SimHei';
        """)
        self.bubble_label.setText(message)
        metrics = QFontMetrics(text_font)
        text_rect = metrics.boundingRect(
            QRect(0, 0, max_text_width, 10000),
            Qt.TextWordWrap | Qt.AlignCenter,
            message,
        )
        
        # 获取气泡尺寸
        label_width = max(self._physical_px(80, screen), text_rect.width() + 8)
        label_height = max(metrics.lineSpacing(), text_rect.height() + 8)
        self.bubble_label.setFixedSize(label_width, label_height)
        cloud_pad_x = self._physical_px(50, screen)
        cloud_pad_y = self._physical_px(28, screen)
        bubble_width = label_width + cloud_pad_x * 2
        bubble_height = label_height + cloud_pad_y * 2
        
        # 设置气泡窗口位置（宠物上方居中）
        pet_x, pet_y = self.x(), self.y()
        bubble_x = pet_x + (self.pet_width - bubble_width) // 2
        bubble_y = pet_y - bubble_height - self._physical_px(20, screen)
        
        # 边界检查
        screen = self._screen_for_position(
            bubble_x, bubble_y, bubble_width, bubble_height
        )
        if screen:
            bubble_x, bubble_y = clamp_window(
                bubble_x, bubble_y, bubble_width, bubble_height,
                self._screen_rect(screen),
            )
        
        self.bubble_window.setGeometry(
            bubble_x, bubble_y, bubble_width, bubble_height
        )
        self.bubble_label.setGeometry(
            cloud_pad_x, cloud_pad_y, label_width, label_height
        )
        
        self.bubble_window.show()
        
        # 移动时更新气泡位置
        self._bubble_float_phase = 0.0
        self._update_bubble_position_timer.start()
    
    def _update_bubble_position(self):
        """更新气泡位置（跟随宠物）"""
        if self.bubble_window.isVisible():
            bubble_width = self.bubble_window.width()
            bubble_height = self.bubble_window.height()
            
            pet_x, pet_y = self.x(), self.y()
            bubble_x = pet_x + (self.pet_width - bubble_width) // 2
            screen = self._screen_for_position()
            self._bubble_float_phase = (
                self._bubble_float_phase + 0.12
            ) % (math.pi * 2)
            float_offset = round(math.sin(self._bubble_float_phase) * 3)
            bubble_y = (
                pet_y - bubble_height
                - self._physical_px(20, screen) + float_offset
            )
            
            screen = self._screen_for_position(
                bubble_x, bubble_y, bubble_width, bubble_height
            )
            if screen:
                bubble_x, bubble_y = clamp_window(
                    bubble_x, bubble_y, bubble_width, bubble_height,
                    self._screen_rect(screen),
                )
            
            self.bubble_window.move(bubble_x, bubble_y)
    
    # ============== 鼠标事件 ==============
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self._cancel_navigation("pet-dragged")
            self._cancel_motion()
            self.is_dragging = True
            self.drag_start_x = event.globalX()
            self.drag_start_y = event.globalY()
            self.drag_last_x = event.globalX()
            self.drag_last_y = event.globalY()
            self.drag_last_time = datetime.now()
            self.drag_velocity_x = 0
            self.drag_velocity_y = 0
            self.last_interaction_time = datetime.now()
            
            # 停止移动
            self.is_moving = False
            
            # 停止悬停定时器
            if hasattr(self, 'hover_timer') and self.hover_timer.isActive():
                self.hover_timer.stop()
            
            # 点击时切换到 happy 状态
            self._set_state(PET_STATE_HAPPY)
            
            # 取消抛物线动画
            if self.parabola_timer.isActive():
                self.parabola_timer.stop()
            
            # 设置抓取光标
            self.setCursor(QCursor(Qt.ClosedHandCursor))
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self.setCursor(QCursor(Qt.OpenHandCursor))
        
        # 启动悬停定时器，3秒后弹出对话
        self.hover_timer = QTimer(self)
        self.hover_timer.timeout.connect(self._on_hover_timeout)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.start(3000)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.setCursor(QCursor(Qt.ArrowCursor))
        
        # 停止悬停定时器
        if hasattr(self, 'hover_timer') and self.hover_timer.isActive():
            self.hover_timer.stop()
    
    def _on_hover_timeout(self):
        """悬停超时处理 - 弹出对话对话框"""
        # 只有当鼠标仍在窗口内且没有拖拽时才弹出
        if not self.is_dragging:
            self._chat_with_pet()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_dragging:
            # 计算速度
            now = datetime.now()
            dt = (now - self.drag_last_time).total_seconds()
            if dt > 0:
                self.drag_velocity_x = (event.globalX() - self.drag_last_x) / dt
                self.drag_velocity_y = (event.globalY() - self.drag_last_y) / dt
            
            self.drag_last_x = event.globalX()
            self.drag_last_y = event.globalY()
            self.drag_last_time = now
            
            # 移动窗口（使用起始位置计算）
            self.pet_x = self.pet_x + (event.globalX() - self.drag_start_x)
            self.pet_y = self.pet_y + (event.globalY() - self.drag_start_y)
            
            # 边界检查
            self.pet_x, self.pet_y = self._clamp_to_virtual_desktop(
                self.pet_x, self.pet_y
            )
            
            self.move(int(self.pet_x), int(self.pet_y))
            
            # 更新起始位置
            self.drag_start_x = event.globalX()
            self.drag_start_y = event.globalY()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.setCursor(QCursor(Qt.OpenHandCursor))
            
            # 检查速度，决定是否执行抛物线
            speed = (self.drag_velocity_x ** 2 + self.drag_velocity_y ** 2) ** 0.5
            if speed > 50:
                self._start_parabola()
            else:
                self._set_state(PET_STATE_IDLE)
    
    def _start_parabola(self):
        """开始抛物线动画"""
        screen = self._screen_for_position()
        if not screen:
            return
        token = self._begin_motion('parabola')
        
        screen_geo = screen.availableGeometry()
        
        # 计算目标位置
        vx = self.drag_velocity_x * 0.3
        
        target_x = self.pet_x + vx
        target_y = screen_geo.bottom() - self.pet_height - 19
        
        # 边界检查
        target_x, target_y = clamp_window(
            target_x, target_y, self.pet_width, self.pet_height,
            self._screen_rect(screen),
        )
        
        # 抛物线参数 - 限制高度偏移，确保不会超出屏幕顶部
        top_clearance = max(0, self.pet_y - screen_geo.top() - 50)
        max_height = min(abs(vx) * 0.3, top_clearance)
        height_offset = -max_height if abs(vx) > 50 else -min(50, top_clearance)
        
        self.parabola_data = {
            'start_x': self.pet_x,
            'start_y': self.pet_y,
            'end_x': target_x,
            'end_y': target_y,
            'vx': vx,
            'height_offset': height_offset,
            'current_step': 0,
            'steps': 30,
            'motion_token': token,
        }
        
        self.parabola_timer.start(30)
    
    def mouseDoubleClickEvent(self, event):
        """双击事件 - 显示代码检查器"""
        if event.button() == Qt.LeftButton:
            self._show_code_checker()
    
    def contextMenuEvent(self, event):
        """右键菜单 - 美化样式"""
        menu = QMenu(self)
        
        # 设置菜单样式 - 圆角、半透明
        # 关键：设置透明背景属性
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        
        screen = self._screen_for_position()
        border = self._physical_px(2, screen)
        radius = self._physical_px(12, screen)
        menu_pad_y = self._physical_px(8, screen)
        menu_pad_x = self._physical_px(5, screen)
        item_pad_y = self._physical_px(8, screen)
        item_pad_right = self._physical_px(25, screen)
        item_pad_left = self._physical_px(15, screen)
        item_radius = self._physical_px(8, screen)
        margin_y = self._physical_px(2, screen)
        margin_x = self._physical_px(5, screen)
        font_size = self._physical_px(22, screen)
        separator_margin_y = self._physical_px(5, screen)
        separator_margin_x = self._physical_px(15, screen)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: rgba(252, 232, 243, 235);
                border: {border}px solid #F48FB1;
                border-radius: {radius}px;
                padding: {menu_pad_y}px {menu_pad_x}px;
            }}
            QMenu::item {{
                background-color: transparent;
                padding: {item_pad_y}px {item_pad_right}px {item_pad_y}px {item_pad_left}px;
                border-radius: {item_radius}px;
                margin: {margin_y}px {margin_x}px;
                font-size: {font_size}px;
                color: #4A148C;
            }}
            QMenu::item:selected {{
                background-color: rgba(244, 143, 177, 220);
                color: #FFFFFF;
            }}
            QMenu::item:disabled {{
                color: #9E9E9E;
                font-weight: bold;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: rgba(206, 147, 216, 150);
                margin: {separator_margin_y}px {separator_margin_x}px;
            }}
        """)
        
        # 菜单项
        menu.addAction(f"🐛 {APP_NAME} v{VERSION}").setEnabled(False)
        menu.addSeparator()
        menu.addAction("💬 和我对话", self._chat_with_pet)
        menu.addAction("🔍 检查代码", self._show_code_checker)
        menu.addAction("📁 打开文件", self._open_file)
        menu.addSeparator()
        menu.addAction("⚙ 设置", self._show_settings)
        menu.addAction("💡 关于", self._show_about)
        menu.addSeparator()
        menu.addAction("❌ 退出", self._quit_app)
        
        menu.exec_(event.globalPos())
    
    # ============== 功能方法 ==============
    def _show_code_checker(self, code_content=None):
        """显示代码检查器"""
        self._update_bubble("正在分析代码...", PET_STATE_THINKING)
        
        dialog = CodeCheckerDialog(self, code_content)
        dialog.exec_()
    
    def _open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开代码文件",
            "",
            "Python Files (*.py);;JavaScript Files (*.js);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._update_bubble(f"📂 已加载: {os.path.basename(file_path)}", PET_STATE_HAPPY)
                # 打开代码检查器并填入代码
                self._show_code_checker(content)
            except Exception as e:
                self._update_bubble(f"❌ 无法打开文件", PET_STATE_SAD)
    
    def _show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec_()
        self._set_state(PET_STATE_HAPPY)
    
    def _chat_with_pet(self):
        """与宠物对话"""
        dialog = ChatDialog(self)
        dialog.exec_()
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            f"关于 {APP_NAME}",
            f"<h3>🐛 {APP_NAME}</h3>"
            f"<p>版本: {VERSION}</p>"
            f"<p>一个可爱的编程助手，能检测代码错误并给出修复建议</p>"
            f"<p>使用 PyQt5 开发，解决透明背景问题</p>"
        )
    
    def _quit_app(self):
        """退出应用"""
        self.ipc_server.stop()
        QApplication.quit()

    def closeEvent(self, event):
        self.ipc_server.stop()
        super().closeEvent(event)


# ============== 代码检查器对话框 ==============
class CodeCheckerDialog(QDialog):
    """代码检查器对话框 - 粉紫蓝主题"""
    
    def __init__(self, parent=None, code_content=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("🐛 Debug Pet - 代码检查器")
        self.setGeometry(200, 200, 750, 700)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        
        # 粉紫蓝主题：半透明效果
        self.setWindowOpacity(0.93)
        
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(252, 232, 243, 230);
                border: 2px solid #F8BBD0;
                border-radius: 15px;
            }
        """)
        
        # 加载设置
        self._load_settings()
        self.request_worker = None
        
        self._init_ui()
        
        # 如果有代码内容，填入
        if code_content:
            self.code_text.setPlainText(code_content)
    
    def _load_settings(self):
        """加载设置"""
        self.config_service = ConfigService()
        self.model_config = self.config_service.load()
        self.api_key = self.config_service.get_api_key(self.model_config.provider)
        self.api_url = self.model_config.api_url
        self.ai_service = self.model_config.provider
        self.model_name = self.model_config.model
        self.use_ai = self.model_config.ai_enabled
    
    def _init_ui(self):
        """初始化 UI - 粉紫蓝主题"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 标题区域
        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: transparent;")
        title_layout = QHBoxLayout(title_frame)
        
        title = QLabel("🐛 Debug Pet")
        title.setStyleSheet("""
            font-size: 26px;
            font-weight: bold;
            color: #AD1457;
            background-color: transparent;
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        layout.addWidget(title_frame)
        
        # 代码输入区域
        code_label = QLabel("📋 代码输入")
        code_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #6A1B9A;
            background-color: transparent;
        """)
        layout.addWidget(code_label)
        
        self.code_text = QTextEdit()
        self.code_text.setPlaceholderText("在此粘贴或输入代码...")
        self.code_text.setMinimumHeight(200)
        self.code_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 243, 250, 255);
                border: 2px solid #CE93D8;
                border-radius: 12px;
                padding: 12px;
                font-family: 'Consolas', 'Microsoft YaHei UI';
                font-size: 18px;
                color: #4A148C;
            }
            QTextEdit:focus {
                border: 2px solid #AB47BC;
            }
        """)
        layout.addWidget(self.code_text, 2)
        
        # 按钮区域 - 粉紫蓝主题配色圆角按钮
        btn_frame = QFrame()
        btn_frame.setStyleSheet("background-color: transparent;")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setSpacing(10)
        
        # 检查代码按钮 - 粉色
        self.check_btn = QPushButton("🔍 检查代码")
        self.check_btn.setMinimumSize(120, 45)
        self.check_btn.setStyleSheet("""
            QPushButton {
                background-color: #F48FB1;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #EC407A;
            }
            QPushButton:pressed {
                background-color: #C2185B;
            }
        """)
        self.check_btn.clicked.connect(self._check_code)
        btn_layout.addWidget(self.check_btn)
        
        # 打开文件按钮 - 蓝色
        open_btn = QPushButton("📁 打开文件")
        open_btn.setMinimumSize(120, 45)
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #90CAF9;
                color: #0D47A1;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #64B5F6;
            }
            QPushButton:pressed {
                background-color: #42A5F5;
            }
        """)
        open_btn.clicked.connect(self._open_file_in_dialog)
        btn_layout.addWidget(open_btn)
        
        # 清空按钮 - 紫色
        clear_btn = QPushButton("🗑 清空")
        clear_btn.setMinimumSize(130, 45)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #CE93D8;
                color: #4A148C;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #AB47BC;
                color: white;
            }
            QPushButton:pressed {
                background-color: #8E24AA;
                color: white;
            }
        """)
        clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        
        layout.addWidget(btn_frame)
        
        # 错误输出区域
        error_label = QLabel("💡 分析结果")
        error_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #C2185B;
            background-color: transparent;
        """)
        layout.addWidget(error_label)
        
        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setMinimumHeight(150)
        self.error_text.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 243, 250, 255);
                border: 2px solid #F48FB1;
                border-radius: 12px;
                padding: 12px;
                font-family: 'Consolas', 'Microsoft YaHei UI';
                font-size: 18px;
                color: #4A148C;
            }
        """)
        layout.addWidget(self.error_text, 1)
        
        self.setLayout(layout)
    
    def _open_file_in_dialog(self):
        """在对话框中打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开代码文件",
            "",
            "Python Files (*.py);;JavaScript Files (*.js);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.code_text.setPlainText(content)
            except Exception as e:
                self.error_text.setText(f"❌ 无法打开文件: {e}")
    
    def _clear_all(self):
        """清空所有内容"""
        self.code_text.clear()
        self.error_text.clear()
    
    def _check_code(self):
        """检查代码"""
        code = self.code_text.toPlainText()
        if not code.strip():
            self.error_text.setText("⚠️ 请输入代码！")
            return
        
        # 上传代码必须由用户在设置中单独、明确授权。
        if self.use_ai and not self.model_config.allow_code_upload:
            self.error_text.setText(
                "🔒 AI 分析已启用，但代码上传未授权。已改用本地检查。\n"
                "如需 AI 分析，请在设置中开启“允许将代码发送给模型”。"
            )
            errors = self._check_python(code)
            if errors:
                self.error_text.append("\n🐛 本地检查发现问题：")
                for err in errors:
                    self.error_text.append(f"第 {err['line']} 行: {err['message']}")
            return

        if self.use_ai and self.model_config.allow_code_upload and self.api_key:
            self.error_text.setText("🤖 正在使用 AI 分析代码...")
            self._check_with_ai(code)
        else:
            # 使用简单的语法检查
            errors = self._check_python(code)
            
            if errors:
                error_output = "🐛 发现以下错误:\n\n"
                for i, err in enumerate(errors, 1):
                    error_output += f"{i}. 第 {err['line']} 行: {err['message']}\n"
                self.error_text.setText(error_output)
                # 报错时显示 failed 动作，停止移动
                if self.parent_window:
                    self.parent_window._cancel_motion()
                    self.parent_window._update_bubble("发现错误！", PET_STATE_SAD)
            else:
                self.error_text.setText("✅ 代码检查通过！没有发现语法错误。")
                # 通过时显示 idle4 动作，停止移动
                if self.parent_window:
                    self.parent_window._cancel_motion()
                    self.parent_window._set_state('idle4')
    
    def _check_with_ai(self, code):
        """在工作线程中执行明确授权的 AI 代码分析。"""
        prompt = f"""请分析以下代码，找出其中的错误、bug 或潜在问题。请用中文回答。

代码：
```python
{code}
```

请按照以下格式回答：
如果代码有问题，列出具体的问题和建议。
如果代码没有问题，请明确说明"代码没有问题"。
"""
        client = ModelApiClient(self.model_config, self.api_key)
        self.check_btn.setEnabled(False)
        self.request_worker = ApiRequestWorker(
            lambda: client.chat(
                "你是一个专业的代码审查专家，擅长发现代码中的错误和潜在问题。",
                [{"role": "user", "content": prompt}],
            ),
            self,
        )
        self.request_worker.succeeded.connect(self._on_ai_check_success)
        self.request_worker.failed.connect(self._on_ai_check_error)
        self.request_worker.finished.connect(self._finish_ai_check)
        self.request_worker.start()

    def _on_ai_check_success(self, result):
        ai_message = result.reply
        passed = any(
            marker in ai_message
            for marker in ("没有问题", "代码正确", "代码没有错误")
        )
        if passed:
            self.error_text.setText("✅ AI 检测通过！\n\n" + ai_message)
            if self.parent_window:
                self.parent_window._cancel_motion()
                self.parent_window._set_state('idle4')
        else:
            self.error_text.setText("🐛 AI 发现问题：\n\n" + ai_message)
            if self.parent_window:
                self.parent_window._cancel_motion()
                self.parent_window._update_bubble("发现错误！", PET_STATE_SAD)

    def _on_ai_check_error(self, error_message):
        self.error_text.setText(f"⚠️ AI 检测失败: {error_message}")

    def _finish_ai_check(self):
        self.check_btn.setEnabled(True)
        if self.request_worker:
            self.request_worker.deleteLater()
            self.request_worker = None
    
    def _check_python(self, code):
        """使用 py_compile 检查 Python 代码"""
        errors = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', temp_file],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            if result.returncode != 0:
                for line in result.stderr.split('\n'):
                    match = re.search(r'line (\d+)', line)
                    if match:
                        errors.append({
                            'line': int(match.group(1)),
                            'message': line.strip()
                        })
        except FileNotFoundError:
            errors.append({
                'line': 1,
                'message': 'Python 编译器未找到，请安装 Python3'
            })
        finally:
            os.unlink(temp_file)
        
        return errors


# ============== 设置对话框 ==============
class SettingsDialog(QDialog):
    """设置对话框 - 粉紫蓝主题"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙ 设置")
        self.setGeometry(300, 200, 540, 650)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        self.setWindowOpacity(0.93)

        self.setStyleSheet("""
            QDialog {
                background-color: rgba(252, 232, 243, 230);
                border: 2px solid #F8BBD0;
                border-radius: 15px;
            }
        """)

        # 加载现有设置
        self._load_settings()

        self._init_ui()

    def _load_settings(self):
        """加载设置"""
        self.config_service = ConfigService()
        self.model_config = self.config_service.load()
        self.api_key = self.config_service.get_api_key(self.model_config.provider)
        self.api_url = self.model_config.api_url
        self.ai_service = self.model_config.provider
        self.model_name = self.model_config.model
        self.use_ai = self.model_config.ai_enabled

    def _init_ui(self):
        """初始化 UI - 粉紫蓝主题"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # 标题
        title = QLabel("⚙ 设置")
        title.setStyleSheet("""
            font-size: 26px;
            font-weight: bold;
            color: #AD1457;
            background-color: transparent;
            padding: 5px 0;
        """)
        layout.addWidget(title)

        # API 设置标题
        api_label = QLabel("🔧 API 设置")
        api_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #6A1B9A;
            background-color: transparent;
            padding: 5px 0;
        """)
        layout.addWidget(api_label)

        # AI 服务选择
        service_layout = QHBoxLayout()
        service_label = QLabel("AI 服务:")
        service_label.setStyleSheet("color: #4A148C; font-size: 20px; background-color: transparent;")
        service_layout.addWidget(service_label)

        self.service_combo = QComboBox()
        self.service_combo.addItems(["DeepSeek", "GLM-4.7-Flash"])
        self.service_combo.setCurrentText("DeepSeek" if self.ai_service == "deepseek" else "GLM-4.7-Flash")
        self.service_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 243, 250, 255);
                border: 2px solid #CE93D8;
                border-radius: 10px;
                padding: 8px 12px;
                color: #4A148C;
                font-size: 20px;
                min-width: 200px;
            }
            QComboBox:hover {
                border: 2px solid #AB47BC;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(255, 243, 250, 255);
                border: 2px solid #CE93D8;
                border-radius: 10px;
                color: #4A148C;
                font-size: 20px;
                padding: 5px;
                selection-background-color: #F8BBD0;
                selection-color: #AD1457;
            }
        """)
        self.service_combo.currentTextChanged.connect(self._on_service_changed)
        service_layout.addWidget(self.service_combo)
        service_layout.addStretch()
        layout.addLayout(service_layout)

        # API Key
        api_key_label = QLabel("API Key:")
        api_key_label.setStyleSheet("color: #4A148C; font-size: 20px; background-color: transparent; padding-top: 5px;")
        layout.addWidget(api_key_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("输入 API Key (GLM 无需 Key)")
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 243, 250, 255);
                border: 2px solid #CE93D8;
                border-radius: 10px;
                padding: 10px 15px;
                color: #4A148C;
                font-size: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #AB47BC;
                background-color: rgba(255, 255, 255, 255);
            }
        """)
        self.api_key_input.setText(self.api_key)
        layout.addWidget(self.api_key_input)

        # API URL
        api_url_label = QLabel("API URL:")
        api_url_label.setStyleSheet("color: #4A148C; font-size: 20px; background-color: transparent; padding-top: 5px;")
        layout.addWidget(api_url_label)

        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("API 端点 URL")
        self.api_url_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 243, 250, 255);
                border: 2px solid #90CAF9;
                border-radius: 10px;
                padding: 10px 15px;
                color: #1565C0;
                font-size: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #42A5F5;
                background-color: rgba(255, 255, 255, 255);
            }
        """)
        self.api_url_input.setText(self.api_url)
        layout.addWidget(self.api_url_input)

        model_label = QLabel("模型名称:")
        model_label.setStyleSheet("color: #4A148C; font-size: 20px; background-color: transparent; padding-top: 5px;")
        layout.addWidget(model_label)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("例如 deepseek-chat 或本地模型名称")
        self.model_input.setText(self.model_name)
        self.model_input.setStyleSheet(self.api_url_input.styleSheet())
        layout.addWidget(self.model_input)

        # 使用 AI 开关
        self.use_ai_checkbox = QPushButton("🤖 启用 AI 分析")
        self.use_ai_checkbox.setCheckable(True)
        self.use_ai_checkbox.setChecked(self.use_ai)
        self.use_ai_checkbox.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 243, 250, 255);
                border: 2px solid #CE93D8;
                border-radius: 10px;
                padding: 10px 15px;
                color: #4A148C;
                font-size: 20px;
                text-align: left;
                margin-top: 10px;
            }
            QPushButton:hover {
                border: 2px solid #AB47BC;
                background-color: rgba(255, 228, 243, 255);
            }
            QPushButton:checked {
                background-color: #F8BBD0;
                color: #AD1457;
                border: 2px solid #EC407A;
            }
        """)
        layout.addWidget(self.use_ai_checkbox)

        self.allow_code_upload_checkbox = QPushButton("🔒 允许将代码发送给模型")
        self.allow_code_upload_checkbox.setCheckable(True)
        self.allow_code_upload_checkbox.setChecked(self.model_config.allow_code_upload)
        self.allow_code_upload_checkbox.setStyleSheet(self.use_ai_checkbox.styleSheet())
        layout.addWidget(self.allow_code_upload_checkbox)

        layout.addStretch()

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumSize(120, 45)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #BBDEFB;
                color: #1565C0;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #90CAF9;
            }
            QPushButton:pressed {
                background-color: #64B5F6;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setMinimumSize(120, 45)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #F48FB1;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #EC407A;
            }
            QPushButton:pressed {
                background-color: #C2185B;
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _on_service_changed(self, service_name):
        """当 AI 服务改变时，自动更新 API URL"""
        if service_name == "DeepSeek":
            self.api_url_input.setText("https://api.deepseek.com/chat/completions")
            self.model_input.setText("deepseek-chat")
        elif service_name == "GLM-4.7-Flash":
            self.api_url_input.setText("https://open.bigmodel.cn/api/paas/v4/chat/completions")
            self.model_input.setText("glm-4-flash")
    
    def _save_settings(self):
        """保存设置"""
        provider = "deepseek" if self.service_combo.currentText() == "DeepSeek" else "glm"
        config = ModelConfig(
            provider=provider,
            api_url=self.api_url_input.text().strip(),
            model=self.model_input.text().strip(),
            ai_enabled=self.use_ai_checkbox.isChecked(),
            allow_code_upload=self.allow_code_upload_checkbox.isChecked(),
            character_id=self.model_config.character_id,
            context_budget_tokens=self.model_config.context_budget_tokens,
        )
        self.config_service.save(config)
        self.config_service.set_api_key(provider, self.api_key_input.text().strip())
        
        self.accept()


# ============== 记忆管理对话框 ==============
class MemoryDialog(QDialog):
    """Manage one character's persisted memories without blocking the UI."""

    def __init__(self, memory_service, character_id, parent=None):
        super().__init__(parent)
        self.memory_service = memory_service
        self.character_id = character_id
        self.workers = []
        self.setWindowTitle("🧠 记忆管理")
        self.resize(820, 520)
        self._init_ui()
        self._reload()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.status_label = QLabel("正在读取记忆……")
        layout.addWidget(self.status_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "类型", "时间", "内容"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 180)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        for label, callback in (
            ("新增偏好", lambda: self._add_memory("preference")),
            ("新增情景", lambda: self._add_memory("episodic")),
            ("保存编辑", self._save_selected),
            ("删除选中", self._delete_selected),
            ("清空本角色", self._clear_all),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        self.enabled_button = QPushButton("记忆已启用")
        self.enabled_button.setCheckable(True)
        self.enabled_button.clicked.connect(self._toggle_enabled)
        buttons.addWidget(self.enabled_button)
        layout.addLayout(buttons)

    def _run_async(self, operation, on_success=None):
        worker = ApiRequestWorker(operation, self)
        self.workers.append(worker)
        if on_success:
            worker.succeeded.connect(on_success)
        worker.failed.connect(lambda error: self.status_label.setText(f"操作失败：{error}"))

        def cleanup():
            if worker in self.workers:
                self.workers.remove(worker)
            worker.deleteLater()

        worker.finished.connect(cleanup)
        worker.start()

    def _load_data(self):
        return (
            self.memory_service.list_entries(self.character_id, limit=300),
            self.memory_service.is_enabled(self.character_id),
        )

    def _reload(self):
        self._run_async(self._load_data, self._show_entries)

    def _show_entries(self, result):
        entries, enabled = result
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [str(entry.id), entry.kind, entry.created_at, entry.content]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column != 3:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, column, item)
        self.enabled_button.setChecked(enabled)
        self.enabled_button.setText("记忆已启用" if enabled else "记忆已关闭")
        self.status_label.setText(f"共 {len(entries)} 条；不同角色的数据彼此隔离。")

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            self.status_label.setText("请先选择一条记忆。")
            return None
        return int(self.table.item(row, 0).text()), self.table.item(row, 3).text()

    def _add_memory(self, kind):
        label = "用户偏好" if kind == "preference" else "情景记忆"
        content, accepted = QInputDialog.getMultiLineText(self, f"新增{label}", "内容：")
        if accepted and content.strip():
            self._run_async(
                lambda: self.memory_service.add_user_memory(
                    self.character_id, content.strip(), kind
                ),
                lambda _result: self._reload(),
            )

    def _save_selected(self):
        selected = self._selected()
        if selected:
            entry_id, content = selected
            self._run_async(
                lambda: self.memory_service.update_entry(
                    entry_id, self.character_id, content
                ),
                lambda _result: self._reload(),
            )

    def _delete_selected(self):
        selected = self._selected()
        if selected and QMessageBox.question(
            self, "删除记忆", "删除后不会再注入后续模型请求。确认删除？"
        ) == QMessageBox.Yes:
            entry_id, _content = selected
            self._run_async(
                lambda: self.memory_service.delete_entry(entry_id, self.character_id),
                lambda _result: self._reload(),
            )

    def _clear_all(self):
        if QMessageBox.question(
            self, "清空记忆", "确认清空当前角色的全部记忆？"
        ) == QMessageBox.Yes:
            self._run_async(
                lambda: self.memory_service.clear(self.character_id),
                lambda _result: self._reload(),
            )

    def _toggle_enabled(self, checked):
        self.enabled_button.setText("记忆已启用" if checked else "记忆已关闭")
        self._run_async(
            lambda: self.memory_service.set_enabled(self.character_id, checked),
            lambda _result: self._reload(),
        )


# ============== 对话对话框 ==============
class ChatDialog(QDialog):
    """与宠物对话的对话框 - 使用 GLM 以祁煜语气回复"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # 加载设置
        self._load_settings()

        # 对话历史（用于上下文记忆）
        self.message_history = []
        self.request_worker = None
        self.memory_worker = None
        self.memory_service = None
        self.session_id = str(uuid.uuid4())

        self.setWindowTitle("💬 和我对话")
        self.setGeometry(300, 300, 580, 500)
        self.setWindowOpacity(0.93)

        # 粉紫蓝主题背景
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(252, 232, 243, 230);
                border: 2px solid #F8BBD0;
                border-radius: 15px;
            }
        """)

        self._init_ui()
        self._restore_memory_async()
    
    def _load_settings(self):
        """加载设置"""
        self.config_service = ConfigService()
        self.model_config = self.config_service.load()
        self.api_key = self.config_service.get_api_key(self.model_config.provider)
        self.api_url = self.model_config.api_url
        self.ai_service = self.model_config.provider
    
    def _init_ui(self):
        """初始化 UI - 粉紫蓝主题"""
        layout = QVBoxLayout()

        # 标题与记忆入口
        title_layout = QHBoxLayout()
        title = QLabel("💬 想对我说...")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #AD1457;
            background-color: transparent;
            padding: 5px 5px;
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        self.memory_button = QPushButton("🧠 记忆")
        self.memory_button.setEnabled(False)
        self.memory_button.clicked.connect(self._show_memory_manager)
        title_layout.addWidget(self.memory_button)
        layout.addLayout(title_layout)

        # 对话历史区域
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMinimumHeight(250)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: rgba(252, 228, 236, 220);
                border: 2px solid #F8BBD0;
                border-radius: 15px;
                padding: 12px;
                font-family: 'Microsoft YaHei UI', 'SimHei';
                font-size: 20px;
                color: #333333;
            }
        """)
        # 欢迎消息 - 祁煜气泡
        welcome_html = '''
        <div style="margin: 6px 0;">
          <div style="display: flex; align-items: flex-start;">
            <span style="font-size: 20px;">💕</span>
            <div style="margin-left: 8px; background-color: rgba(240, 204, 228, 230);
                        border: 2px solid #F48FB1; border-radius: 15px;
                        padding: 10px 14px; color: #5D4037; font-size: 20px;
                        max-width: 80%;">
              你来了，我一直在等你……
            </div>
          </div>
        </div>
        '''
        self.chat_history.append(welcome_html.strip())
        layout.addWidget(self.chat_history, 2)

        # 输入区域
        input_layout = QHBoxLayout()

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("输入你想说的话...")
        self.input_text.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 230);
                border: 2px solid #CE93D8;
                border-radius: 12px;
                padding: 10px 15px;
                font-family: 'Microsoft YaHei UI', 'SimHei';
                font-size: 20px;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #AB47BC;
                background-color: rgba(255, 243, 250, 255);
            }
        """)
        self.input_text.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_text)

        send_btn = QPushButton("发送")
        send_btn.setMinimumSize(100, 45)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #F48FB1;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #EC407A;
            }
            QPushButton:pressed {
                background-color: #C2185B;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #9E9E9E;
            }
        """)
        send_btn.clicked.connect(self._send_message)
        self.send_btn = send_btn
        self.send_btn.setEnabled(False)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)

        self.setLayout(layout)

    def _load_memory(self):
        service = SQLiteMemoryService()
        return service, service.recent_messages(self.model_config.character_id, limit=20)

    def _restore_memory_async(self):
        self.memory_worker = ApiRequestWorker(self._load_memory, self)
        self.memory_worker.succeeded.connect(self._on_memory_restored)
        self.memory_worker.failed.connect(self._on_memory_restore_failed)
        self.memory_worker.finished.connect(self._finish_memory_restore)
        self.memory_worker.start()

    def _on_memory_restored(self, result):
        self.memory_service, entries = result
        self.message_history = [
            {"role": entry.role, "content": entry.content} for entry in entries
        ]
        for entry in entries:
            bubble = (
                self._make_user_bubble(entry.content)
                if entry.role == "user"
                else self._make_ai_bubble(entry.content)
            )
            self.chat_history.append(bubble)
        if entries:
            self.chat_history.append(
                self._make_ai_bubble("之前聊过的内容，我还记得。")
            )
        self.send_btn.setEnabled(True)
        self.memory_button.setEnabled(True)

    def _on_memory_restore_failed(self, error_message):
        self.memory_service = NullMemoryService()
        self.chat_history.append(
            self._make_error_bubble(f"记忆库暂时不可用：{error_message}")
        )
        self.send_btn.setEnabled(True)

    def _finish_memory_restore(self):
        if self.memory_worker:
            self.memory_worker.deleteLater()
            self.memory_worker = None

    def _show_memory_manager(self):
        if self.memory_service:
            MemoryDialog(
                self.memory_service,
                self.model_config.character_id,
                self,
            ).exec_()

    def _make_user_bubble(self, text):
        """生成用户消息气泡（右侧，蓝色系）"""
        return '''
        <div style="margin: 6px 0;">
          <div style="display: flex; align-items: flex-start; flex-direction: row-reverse;">
            <span style="font-size: 20px;">🌸</span>
            <div style="margin-right: 8px; background-color: rgba(179, 229, 252, 235);
                        border: 2px solid #64B5F6; border-radius: 15px;
                        padding: 10px 14px; color: #0D47A1; font-size: 20px;
                        max-width: 80%;">
              {text}
            </div>
          </div>
        </div>
        '''.format(text=html.escape(text))

    def _make_ai_bubble(self, text):
        """生成祁煜消息气泡（左侧，粉紫色系）"""
        return '''
        <div style="margin: 6px 0;">
          <div style="display: flex; align-items: flex-start;">
            <span style="font-size: 20px;">💕</span>
            <div style="margin-left: 8px; background-color: rgba(240, 204, 228, 230);
                        border: 2px solid #F48FB1; border-radius: 15px;
                        padding: 10px 14px; color: #5D4037; font-size: 20px;
                        max-width: 80%;">
              {text}
            </div>
          </div>
        </div>
        '''.format(text=html.escape(text))

    def _make_error_bubble(self, text):
        """生成错误消息气泡（左侧，红色系）"""
        return '''
        <div style="margin: 6px 0;">
          <div style="display: flex; align-items: flex-start;">
            <span style="font-size: 20px;">💢</span>
            <div style="margin-left: 8px; background-color: rgba(255, 205, 210, 235);
                        border: 2px solid #EF5350; border-radius: 15px;
                        padding: 10px 14px; color: #B71C1C; font-size: 20px;
                        max-width: 80%;">
              {text}
            </div>
          </div>
        </div>
        '''.format(text=html.escape(text))

    def _send_message(self):
        """发送消息"""
        message = self.input_text.text().strip()
        if not message or not self.memory_service:
            return

        # 添加用户消息气泡到历史
        self.chat_history.append(self._make_user_bubble(message))
        self.input_text.clear()
        self.send_btn.setEnabled(False)

        # UI history mirrors persisted history; request context is built in
        # the worker from SQLite so closing the dialog cannot erase it.
        self.message_history.append({"role": "user", "content": message})

        # 使用 AI 以祁煜语气回复（带上下文）
        self._get_qi_yu_response(message)
    
    def _load_qi_yu_prompt(self):
        """从 yu.md 文件加载祁煜 prompt"""
        prompt_path = get_resource_path("yu.md")
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read() + "\n\n请遵守核心任务与对话规范，符合祁煜人物设定，参考对话风格与语气，参考祁煜语录汇总。用祁煜的口吻回复以下对话："
            except Exception:
                pass
        return None
    
    def _get_qi_yu_response(self, message):
        """Start a model request without blocking Qt's UI thread."""
        qi_yu_prompt = self._load_qi_yu_prompt()
        if not qi_yu_prompt:
            self.chat_history.append(self._make_error_bubble("我的剧本好像丢了……"))
            self.send_btn.setEnabled(True)
            return

        client = ModelApiClient(self.model_config, self.api_key)

        def request_with_memory():
            self.memory_service.add_message(
                self.model_config.character_id,
                self.session_id,
                "user",
                message,
            )
            context = self.memory_service.build_context(
                self.model_config.character_id,
                message,
                qi_yu_prompt,
                budget_tokens=self.model_config.context_budget_tokens,
            )
            result = client.chat(context.system_prompt, context.messages)
            self.memory_service.add_message(
                self.model_config.character_id,
                self.session_id,
                "assistant",
                result.reply,
            )
            return result, context

        self.request_worker = ApiRequestWorker(
            request_with_memory,
            self,
        )
        self.request_worker.succeeded.connect(self._on_chat_success)
        self.request_worker.failed.connect(self._on_chat_error)
        self.request_worker.finished.connect(self._finish_chat_request)
        self.request_worker.start()

    def _on_chat_success(self, result):
        chat_result, context = result
        reply = chat_result.reply
        self.chat_history.append(self._make_ai_bubble(reply))
        self.message_history.append({"role": "assistant", "content": reply})
        print(
            f"[MEMORY] injected={list(context.injected_memory_ids)} "
            f"estimated_tokens={context.estimated_tokens}"
        )
        if self.parent_window:
            self.parent_window._set_state(PET_STATE_HAPPY)

    def _on_chat_error(self, error_message):
        self.chat_history.append(
            self._make_error_bubble(f"抱歉，我现在无法回应：{error_message}")
        )

    def _finish_chat_request(self):
        self.send_btn.setEnabled(True)
        if self.request_worker:
            self.request_worker.deleteLater()
            self.request_worker = None


# ============== 主程序 ==============
def main():
    enable_per_monitor_dpi_awareness()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建宠物窗口
    pet = PetWindow()
    pet.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
