import os
import random
import traceback
import time
from PyQt5.QtWidgets import QLabel, QMainWindow, QApplication, QSystemTrayIcon, QMenu, QAction, qApp
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QTransform, QIcon
from conf import *


class FoxPet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.image_label = QLabel(self)

        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.screen_width = screen_geo.width()
        self.screen_height = screen_geo.height()

        self.current_state = None
        self.tick_count = 0
        self.state_timer = 0
        self.frame_index = 0
        self.current_frames = []
        self.current_is_loop = True
        self.current_speed = 10
        self.current_duration = 0  # 记录当前状态存活的总tick数
        self.current_wall_offset = None  # 角色挂在墙上减去的宽度
        self.hunt_jumped = None  # HUNT起跳插栓

        self.dx = 0
        self.dy = 0
        self.is_dragged = False
        self.is_facing_right = False
        self.is_upside_down = False

        self.drag_pos = None
        self.mouse_history = []
        self.current_size = None
        self.floor_y = None

        # 剥离大量数据，直接引用配置中枢
        self.states = STATES
        self.transitions = TRANSITIONS

        self.set_scale(1.0)
        self._init_tray()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(REFRESH_RATE)

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))
        tray_menu = QMenu(self)

        summon_action = QAction("🦊 召唤狐狐", self)
        summon_action.triggered.connect(self.summon_fox)
        tray_menu.addAction(summon_action)

        scale_menu = QMenu("🔍 狐狐体型", self)
        for label, scale in [("大 (150%)", 1.5), ("中 (100% 默认)", 1.0), ("小 (75%)", 0.75)]:
            action = QAction(label, self)
            action.triggered.connect(lambda checked, s=scale: self.set_scale(s))
            scale_menu.addAction(action)
        tray_menu.addMenu(scale_menu)

        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(qApp.quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def set_scale(self, scale_factor):
        self.current_size = int(PET_SIZE * scale_factor)
        # 比如原版是 48/128，我们按照这个原始比例，乘上当前的尺寸，得到新的精确贴墙像素
        self.current_wall_offset = int(self.current_size * (WALL_OFFSET / PET_SIZE))
        self.setFixedSize(self.current_size, self.current_size)
        self.floor_y = self.screen_height - self.current_size
        self.summon_fox()

    def summon_fox(self):
        spawn_x = int(self.screen_width * 0.5 - self.current_size / 2)
        spawn_y = int(-self.screen_height * 0.1)
        self.move(spawn_x, spawn_y)
        self.dx, self.dy = 0, 0
        self.show()
        self.change_state('FALL')

    # ==========================================
    # 【引擎主循环：逻辑被彻底拆分，清清爽爽】
    # ==========================================
    def update_loop(self):
        try:
            # 1. 大脑：状态机切换逻辑
            self.check_state_transitions()

            # 2. 肌肉：物理运算与防穿模拦截
            if not self.is_dragged:
                if (self.y() > self.screen_height * 1.2 or self.y() < -self.screen_height * 0.2 or
                        self.x() < -self.screen_width * 0.2 or self.x() > self.screen_width * 1.2):
                    self.summon_fox()
                    return

                # 重力系统
                special_states = ['CLIMB_UP', 'CLIMB_DOWN', 'WALL_IDLE', 'CEILING_ENTER', 'CEILING_EXIT', 'CEILING_WALK',
                                  'CEILING_IDLE']
                if self.current_state not in special_states:
                    self.dy += GRAVITY

                # 【帧级动作精准位移控制 (根运动)】
                # ==========================================
                if self.current_state == 'HUNT':
                    # 动画第 3~5 帧 (索引 2, 3, 4) 是扑击阶段
                    if 4 <= self.frame_index <= 5:
                        # 1. 垂直方向：拔地而起 (且只允许爆发一次力！)
                        if not getattr(self, 'hunt_jumped', False):
                            self.dy = -SPEED_HUNT_Y  # 给一个向上的负数动能
                            self.hunt_jumped = True  # 拔掉保险销，这轮动作不再给向上的力了！
                        # 2. 水平方向：短促有力的前冲
                        self.dx = SPEED_HUNT_X if self.is_facing_right else -SPEED_HUNT_X
                    else:
                        # 预备阶段(帧 0~1) 和 落地按住猎物阶段(帧 5及之后)，不给水平推力，直接刹车
                        self.dx = 0
                # ==========================================
                # 预判坐标并触发碰撞
                next_x, next_y = self.x() + self.dx, self.y() + self.dy
                next_x, next_y = self.handle_collisions(next_x, next_y)
                self.move(int(next_x), int(next_y))

            # 3. 灵魂：动画节拍器
            self.tick_count += 1
            if self.tick_count >= self.current_speed:
                self.animate()
                self.tick_count = 0

            self.state_timer += 1

        except Exception as e:
            print("Python 代码执行出错：")
            traceback.print_exc()

    def check_state_transitions(self):
        # 只要活够了时长，立刻查字典抽签进入下一个动作
        if self.state_timer >= self.current_duration:
            next_options = self.transitions.get(self.current_state)
            if next_options:
                choices, weights = list(next_options.keys()), list(next_options.values())
                next_state = random.choices(choices, weights=weights)[0]
                self.change_state(next_state)

    def handle_collisions(self, next_x, next_y):
        left_bound = -self.current_wall_offset
        right_bound = self.screen_width - self.current_size + self.current_wall_offset

        # A. 左右墙壁与 AI 寻路逻辑
        if self.current_state in ['WALK', 'WALK_FOUR_FOOT', 'FALL', 'GO_TO_WALL', 'JUMP_TO_WALL', 'POKED', 'HUNT']:
            if next_x < left_bound and self.y() > -self.screen_height * 0.2:
                next_x, self.dx, self.dy = left_bound, 0, 0
                self.is_facing_right = False
                self.change_state('CLIMB_UP' if self.current_state == 'GO_TO_WALL' else 'WALL_IDLE')

            elif next_x > right_bound and self.y() > -self.screen_height * 0.2:
                next_x, self.dx, self.dy = right_bound, 0, 0
                self.is_facing_right = True
                self.change_state('CLIMB_UP' if self.current_state == 'GO_TO_WALL' else 'WALL_IDLE')

            elif self.current_state in ['WALK', 'WALK_FOUR_FOOT'] and random.random() < PROB_TURN_AROUND:
                self.dx = -self.dx
                self.is_facing_right = (self.dx > 0)
                self.animate()

        if self.current_state == 'GO_TO_WALL':
            self.dx = -SPEED_RUN if self.x() < self.screen_width / 2 else SPEED_RUN
            self.is_facing_right = (self.dx > 0)

        elif self.current_state == 'CEILING_WALK':
            if next_x <= left_bound and self.dx < 0:     # 撞到左边天花板尽头
                next_x = left_bound                      # 对齐左墙贴图
                self.dx = 0
                self.is_facing_right = False             # 调整朝向
                self.change_state('CEILING_EXIT')          # 切入下墙状态！
            elif next_x >= right_bound and self.dx > 0:  # 撞到右边天花板尽头
                next_x = right_bound                     # 对齐右墙贴图
                self.dx = 0
                self.is_facing_right = True              # 调整朝向
                self.change_state('CEILING_EXIT')          # 切入下墙状态！
            elif random.random() < PROB_CEILING_DROP:
                self.change_state('CEILING_IDLE')

        # C. 上下极限撞击与着陆
        if next_y >= self.floor_y and self.dy >= 0:
            next_y, self.dy = self.floor_y, 0
            if self.current_state in ['FALL', 'CLIMB_DOWN', 'JUMP_TO_WALL', 'POKED']:
                if self.current_state == 'FALL': self.dx = 0
                self.change_state('LAND')

        elif next_y <= 0 and self.current_state == 'CLIMB_UP':
            next_y = 0
            self.change_state('CEILING_ENTER')

        return next_x, next_y

    def animate(self):
        frames, is_loop = self.current_frames, self.current_is_loop
        if not frames: return
        if self.frame_index >= len(frames): self.frame_index = 0

        img_path = os.path.join(ASSET_DIR, frames[self.frame_index])
        if not os.path.exists(img_path): return

        pixmap = QPixmap(img_path).scaled(self.current_size, self.current_size, Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation)
        if pixmap.isNull(): return

        transform = QTransform()
        if self.is_facing_right: transform.scale(-1, 1)
        if self.is_upside_down: transform.scale(1, -1)
        if not transform.isIdentity(): pixmap = pixmap.transformed(transform)

        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())
        self.resize(pixmap.size())

        if is_loop:
            self.frame_index = (self.frame_index + 1) % len(frames)
        elif self.frame_index < len(frames) - 1:
            self.frame_index += 1

    def change_state(self, new_state):
        if self.current_state == new_state: return

        print(f"【状态切换】{self.current_state} -> {new_state}")
        self.current_state = new_state
        self.state_timer = self.frame_index = self.tick_count = 0

        state_info = self.states.get(new_state, {})
        default_speed = state_info.get('speed', 15)
        default_loop = state_info.get('loop', True)
        default_duration = state_info.get('duration', None)  # 核心：默认允许不填 duration！

        if 'anim_pools' in state_info:
            chosen_pool = random.choice(state_info['anim_pools'])
            is_dict = isinstance(chosen_pool, dict)
            self.current_frames = chosen_pool.get('frames', []) if is_dict else chosen_pool
            self.current_is_loop = chosen_pool.get('loop', default_loop) if is_dict else default_loop
            self.current_speed = chosen_pool.get('speed', default_speed) if is_dict else default_speed
            current_duration_range = chosen_pool.get('duration', default_duration) if is_dict else default_duration
        else:
            self.current_frames = state_info.get('frames', [])
            self.current_is_loop = default_loop
            self.current_speed = default_speed
            current_duration_range = default_duration

        # ==========================================
        # 【核心黑科技：智能计算寿命】
        # 如果不填 duration，引擎将精确计算：帧数 × 播放速度 = 刚好播完需要的Tick数！
        # ==========================================
        if current_duration_range is None:
            if not self.current_is_loop:
                self.current_duration = len(self.current_frames) * self.current_speed
            else:
                self.current_duration = int((3.0 * 1000) / REFRESH_RATE)  # 循环动画不填时间的兜底
        else:
            target_seconds = random.uniform(current_duration_range[0], current_duration_range[1])
            self.current_duration = int((target_seconds * 1000) / REFRESH_RATE)

        # 调配物理状态
        self._apply_state_physics_presets(new_state)
        self.animate()

    def _apply_state_physics_presets(self, new_state):
        self.is_upside_down = False

        if new_state == 'CLIMB_UP':
            self.dx, self.dy = 0, -SPEED_CLIMB
        elif new_state == 'CLIMB_DOWN':
            self.dx, self.dy = 0, SPEED_CLIMB
        elif new_state == 'WALL_IDLE':
            self.dx, self.dy = 0, 0
        elif new_state in ['CEILING_ENTER', 'CEILING_WALK', 'CEILING_IDLE']:
            self.is_upside_down = True
            self.dy = 0
            if new_state == 'CEILING_WALK':
                self.dx = random.choice([-SPEED_CEILING, SPEED_CEILING])
                self.is_facing_right = (self.dx > 0)
            else:
                self.dx = 0
        elif new_state in ['IDLE', 'STAND_TWO_FOOT', 'STAND_FOUR_FOOT', 'LAND', 'POKED', 'HUNT']:
            self.dx = 0
            # 捕猎状态专属保险销：用来控制“只起跳一次”
            if new_state == 'HUNT':
                self.hunt_jumped = False
        elif new_state in ['WALK', 'WALK_FOUR_FOOT']:
            self.dx = random.choice([-SPEED_WALK, SPEED_WALK])
            self.is_facing_right = (self.dx > 0)
        elif new_state == 'JUMP_TO_WALL':
            self.dy = -SPEED_JUMP_Y
            self.dx = -SPEED_JUMP_X if self.x() < self.screen_width / 2 else SPEED_JUMP_X
            self.is_facing_right = (self.dx > 0)

    # 鼠标事件保持不变
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragged = True
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.change_state('DRAG')
            self.mouse_history = [(time.time(), event.globalPos())]
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragged:
            self.mouse_history.append((time.time(), event.globalPos()))
            if len(self.mouse_history) > 5:
                self.mouse_history.pop(0)
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragged = False
            if len(self.mouse_history) > 0:
                start_time, start_pos = self.mouse_history[0]
                release_time, release_pos = time.time(), event.globalPos()
                distance = ((release_pos.x() - start_pos.x()) ** 2 + (release_pos.y() - start_pos.y()) ** 2) ** 0.5
                duration = release_time - start_time

                if distance < 5 and duration < 0.3:
                    self.change_state('POKED')
                    self.dy = -15
                    self.dx = -5 if getattr(self, 'is_facing_right', True) else 5
                    self.mouse_history.clear()
                    super().mouseReleaseEvent(event)
                    return

            self.change_state('FALL')
            if len(self.mouse_history) >= 2:
                old_time, old_pos = self.mouse_history[0]
                new_time, new_pos = self.mouse_history[-1]
                dt = new_time - old_time

                if dt > 0 and (time.time() - new_time) < DRAG_PAUSE_THRESHOLD:
                    vx, vy = (new_pos.x() - old_pos.x()) / dt, (new_pos.y() - old_pos.y()) / dt
                    frame_seconds = REFRESH_RATE / 1000.0
                    self.dx = max(-100, min(100, vx * frame_seconds * THROW_BOOST_X))
                    self.dy = max(-200, min(100, vy * frame_seconds * THROW_BOOST_Y))
                else:
                    self.dx, self.dy = 0, 0
            else:
                self.dx, self.dy = 0, 0

            self.mouse_history.clear()
        super().mouseReleaseEvent(event)