import os
import time
import logging
import threading
from PIL import ImageGrab
import numpy as np
import win32gui
import win32con

# Import our DirectInput module
import direct_input

# Try to import cv2, we will handle ImportError gracefully if it's not installed yet
try:
    import cv2
except ImportError:
    cv2 = None

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class ForzaBot:
    def __init__(self, templates_dir="templates"):
        self.templates_dir = templates_dir
        self.race_duration = 62.0  # seconds
        self.threshold = 0.8       # similarity threshold
        self.check_interval = 1.0  # check screen every X seconds
        self.game_window_title = "Forza Horizon" # Substring to find window
        self.selected_hwnd = None                # Explicit HWND from GUI
        
        self.state = "IDLE"
        self.mode = "RACE_FARM"  # RACE_FARM, CAR_BUY, CAR_MASTERY
        self.is_running = False
        self.thread = None
        self.log_callback = print # Can be replaced by GUI log function
        self.state_callback = None # Can be replaced by GUI state update function
        
        self.mastery_grid_topleft = None
        self.mastery_grid_bottomright = None
        self.mastery_car_index = 0
        
        # Ensure templates directory exists
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            
        self.load_config()

    def load_config(self):
        import json
        config_path = os.path.join(self.templates_dir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.race_duration = data.get("race_duration", self.race_duration)
                    self.threshold = data.get("threshold", self.threshold)
                    self.game_window_title = data.get("game_window_title", self.game_window_title)
                    self.mastery_grid_topleft = data.get("mastery_grid_topleft", self.mastery_grid_topleft)
                    if self.mastery_grid_topleft:
                        self.mastery_grid_topleft = tuple(self.mastery_grid_topleft)
                    self.mastery_grid_bottomright = data.get("mastery_grid_bottomright", self.mastery_grid_bottomright)
                    if self.mastery_grid_bottomright:
                        self.mastery_grid_bottomright = tuple(self.mastery_grid_bottomright)
                    self.mastery_car_index = data.get("mastery_car_index", self.mastery_car_index)
            except Exception as e:
                self.log(f"讀取設定檔 config.json 發生錯誤: {e}")

    def save_config(self):
        import json
        config_path = os.path.join(self.templates_dir, "config.json")
        try:
            data = {
                "race_duration": self.race_duration,
                "threshold": self.threshold,
                "game_window_title": self.game_window_title,
                "mastery_grid_topleft": self.mastery_grid_topleft,
                "mastery_grid_bottomright": self.mastery_grid_bottomright,
                "mastery_car_index": self.mastery_car_index
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.log(f"儲存設定檔 config.json 發生錯誤: {e}")

    def log(self, message):
        logging.info(message)
        if self.log_callback:
            self.log_callback(message)

    def update_state(self, new_state):
        self.state = new_state
        self.log(f"狀態轉移至: {new_state}")
        if self.state_callback:
            self.state_callback(new_state)

    def find_game_window(self):
        """Finds the window handle and rect for the game."""
        # If we have an explicit hwnd selected and it is valid, use it directly
        if self.selected_hwnd and win32gui.IsWindow(self.selected_hwnd):
            if not win32gui.IsIconic(self.selected_hwnd):
                return self.selected_hwnd, win32gui.GetWindowRect(self.selected_hwnd)

        hwnd_list = []
        def win_enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.game_window_title.lower() in title.lower():
                    hwnd_list.append((hwnd, title))
        win32gui.EnumWindows(win_enum_handler, None)
        
        if not hwnd_list:
            return None, None
            
        # Prioritize windows that are not minimized and have actual size
        for hwnd, title in hwnd_list:
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            if width > 100 and height > 100:
                # Check if minimized
                if not win32gui.IsIconic(hwnd):
                    return hwnd, rect
        
        # Fallback to the first found
        hwnd, title = hwnd_list[0]
        return hwnd, win32gui.GetWindowRect(hwnd)

    def capture_game_screen(self):
        """Captures the game screen, or full screen if game window not found."""
        hwnd, rect = self.find_game_window()
        if hwnd and rect:
            # rect is (left, top, right, bottom)
            # Ensure coordinates are within valid range
            left, top, right, bottom = rect
            if left < 0: left = 0
            if top < 0: top = 0
            
            # Avoid capturing minimized or zero-size window
            if right > left and bottom > top:
                screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
                return screenshot, (left, top)
                
        # Fallback to full screen
        screenshot = ImageGrab.grab()
        return screenshot, (0, 0)

    def find_template_on_screen(self, template_filename, threshold=None, region=None):
        """Searches for a template image on the game screen, optionally within a relative region and threshold."""
        if cv2 is None:
            self.log("錯誤: OpenCV (cv2) 尚未載入，請確認安裝完成。")
            return None
            
        template_path = os.path.join(self.templates_dir, template_filename)
        if not os.path.exists(template_path):
            self.log(f"警告: 找不到模板檔案 {template_path}，請先截圖設定。")
            return None
            
        screenshot, offset = self.capture_game_screen()
        img_rgb = np.array(screenshot)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            self.log(f"錯誤: 無法讀取模板檔案 {template_path}")
            return None
            
        w, h = template.shape[1], template.shape[0]
        
        # Determine threshold
        search_threshold = threshold if threshold is not None else self.threshold
        
        # Apply region crop if provided (ymin, ymax, xmin, xmax as fractions of screen size)
        crop_offset_x = 0
        crop_offset_y = 0
        if region is not None:
            sh, sw = img_gray.shape[0], img_gray.shape[1]
            ymin, ymax, xmin, xmax = region
            py_min = int(ymin * sh)
            py_max = int(ymax * sh)
            px_min = int(xmin * sw)
            px_max = int(xmax * sw)
            # Ensure crop bounds are valid
            py_min = max(0, min(py_min, sh - 1))
            py_max = max(0, min(py_max, sh))
            px_min = max(0, min(px_min, sw - 1))
            px_max = max(0, min(px_max, sw))
            
            if py_max > py_min and px_max > px_min:
                img_gray = img_gray[py_min:py_max, px_min:px_max]
                crop_offset_x = px_min
                crop_offset_y = py_min
        
        # Ensure template is smaller than screen
        if w > img_gray.shape[1] or h > img_gray.shape[0]:
            return None
            
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val >= search_threshold:
            # relative center of match in the (cropped) image
            rel_x = max_loc[0] + w // 2
            rel_y = max_loc[1] + h // 2
            # absolute center of match on screen
            abs_x = offset[0] + crop_offset_x + rel_x
            abs_y = offset[1] + crop_offset_y + rel_y
            return abs_x, abs_y, max_val
            
        return None

    def find_all_templates_on_screen(self, template_filename, min_distance=30):
        """Searches for all occurrences of a template image on the game screen.
        Returns a list of (abs_x, abs_y, confidence) sorted from left to right.
        """
        if cv2 is None:
            self.log("錯誤: OpenCV (cv2) 尚未載入，請確認安裝完成。")
            return []
            
        template_path = os.path.join(self.templates_dir, template_filename)
        if not os.path.exists(template_path):
            self.log(f"警告: 找不到模板檔案 {template_path}，請先截圖設定。")
            return []
            
        screenshot, offset = self.capture_game_screen()
        img_rgb = np.array(screenshot)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            self.log(f"錯誤: 無法讀取模板檔案 {template_path}")
            return []
            
        w, h = template.shape[1], template.shape[0]
        
        # Ensure template is smaller than screen
        if w > img_gray.shape[1] or h > img_gray.shape[0]:
            self.log(f"錯誤: 模板尺寸 {w}x{h} 大於畫面尺寸 {img_gray.shape[1]}x{img_gray.shape[0]}")
            return []
            
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        
        # Find all locations with confidence >= threshold
        loc = np.where(res >= self.threshold)
        
        matches = []
        for pt in zip(*loc[::-1]):  # Switch x and y
            confidence = res[pt[1], pt[0]]
            matches.append((pt[0] + w // 2, pt[1] + h // 2, confidence))
            
        # Group close matches to avoid multiple detections of the same card (basic NMS)
        matches.sort(key=lambda item: item[0])
        
        filtered_matches = []
        for pt in matches:
            is_duplicate = False
            for f_pt in filtered_matches:
                dist = np.sqrt((pt[0] - f_pt[0])**2 + (pt[1] - f_pt[1])**2)
                if dist < min_distance:
                    if pt[2] > f_pt[2]:
                        filtered_matches.remove(f_pt)
                        filtered_matches.append(pt)
                    is_duplicate = True
                    break
            if not is_duplicate:
                filtered_matches.append(pt)
                
        # Convert to absolute screen coordinates
        final_matches = []
        for rel_x, rel_y, conf in filtered_matches:
            abs_x = offset[0] + rel_x
            abs_y = offset[1] + rel_y
            final_matches.append((abs_x, abs_y, conf))
            
        # Sort by x coordinate left-to-right
        final_matches.sort(key=lambda item: item[0])
        return final_matches

    def start(self):
        """Starts the bot loop in a background thread."""
        if self.is_running:
            return
        
        if cv2 is None:
            self.log("無法啟動：OpenCV 模組未安裝或載入失敗。")
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.log("腳本已在背景啟動...")

    def stop(self):
        """Stops the bot loop."""
        if not self.is_running:
            return
        self.is_running = False
        # Safety release of keys
        try:
            direct_input.release_key(direct_input.KEY_W)
        except Exception:
            pass
        # Cleanup wait state tracking variables
        for attr in ["buy_wait_stable_count", "buy_wait_last_x", "buy_wait_last_y"]:
            if hasattr(self, attr):
                delattr(self, attr)
        self.update_state("IDLE")
        self.log("腳本已停止運作。")

    def _run_loop(self):
        """Main execution loop."""
        # Wait for CV2 to load if needed
        while cv2 is None and self.is_running:
            time.sleep(1.0)
            
        if not self.is_running:
            return

        if self.mode == "CAR_BUY":
            self.log("正在啟動自動購車模式 (Lamborghini Revuelto)...")
            self.buy_car_count = 0
            detected_state = "BUY_START"
            try:
                if self.find_template_on_screen("autoshow.png"):
                    detected_state = "BUY_START"
                    self.log("自動判定成功：目前處於【車庫首頁 - 汽車展售中心】")
            except Exception:
                pass
            
            self.update_state(detected_state)
            
            while self.is_running:
                try:
                    if cv2 is None:
                        time.sleep(2.0)
                        continue
                        
                    if self.state == "BUY_START":
                        match = self.find_template_on_screen("autoshow.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【汽車展售中心】按鈕 (置信度: {conf:.2f})")
                            self.log("模擬滑鼠點擊進入展售中心...")
                            direct_input.mouse_click(x, y, click_duration=0.15, settle_delay=0.15)
                            self.update_state("BUY_IN_SHOP")
                            time.sleep(1.0)
                        else:
                            # 備用狀態修正
                            if self.find_template_on_screen("lambo_brand.png"):
                                self.log("💡 [自動狀態修正]：已在車廠選單中，修正狀態至【選擇車廠】")
                                self.update_state("BUY_SELECT_MANUFACTURER")
                            elif self.find_template_on_screen("revuelto.png"):
                                self.log("💡 [自動狀態修正]：已在車輛選單中，修正狀態至【選擇車輛】")
                                self.update_state("BUY_SELECT_CAR")
                            else:
                                time.sleep(self.check_interval)
                                
                    elif self.state == "BUY_IN_SHOP":
                        self.log("已進入商城，發送鍵盤 'Backspace' 開啟車廠選單...")
                        direct_input.press_and_release(direct_input.KEY_BACKSPACE, duration=0.5)
                        self.update_state("BUY_SELECT_MANUFACTURER")
                        time.sleep(1.5)
                        
                    elif self.state == "BUY_SELECT_MANUFACTURER":
                        match = self.find_template_on_screen("lambo_brand.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【LAMBORGHINI】車廠標誌 (置信度: {conf:.2f})")
                            self.log("模擬滑鼠點擊進入車廠選單...")
                            direct_input.mouse_click(x, y, click_duration=0.15, settle_delay=0.15)
                            self.update_state("BUY_SELECT_CAR")
                            time.sleep(1.5)
                        else:
                            if self.find_template_on_screen("revuelto.png"):
                                self.log("💡 [自動狀態修正]：已在車輛選單中，修正狀態至【選擇車輛】")
                                self.update_state("BUY_SELECT_CAR")
                            else:
                                time.sleep(self.check_interval)
                                
                    elif self.state == "BUY_SELECT_CAR":
                        match = self.find_template_on_screen("revuelto.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【REVUELTO】車輛卡片 (置信度: {conf:.2f})")
                            self.log("滑鼠先移至車輛位置，等待 0.5 秒以觸發懸停狀態...")
                            direct_input.set_cursor_pos(x, y)
                            time.sleep(0.5)
                            self.log("模擬滑鼠點擊選中車輛...")
                            direct_input.mouse_click(x, y, click_duration=0.15, settle_delay=0.05)
                            self.update_state("BUY_LIVERY")
                            time.sleep(1.0)
                        else:
                            time.sleep(self.check_interval)
                            
                    elif self.state == "BUY_LIVERY":
                        match = self.find_template_on_screen("factory_colors.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【車廠色彩】字樣 (置信度: {conf:.2f})，確定塗裝頁面已載入。")
                            self.log("發送鍵盤 'Enter' 選擇塗裝...")
                            direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                            time.sleep(1.0)
                            self.log("發送鍵盤 'Enter' 確認塗裝顏色...")
                            direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                            self.update_state("BUY_CONFIRM")
                            time.sleep(1.0)
                        else:
                            time.sleep(self.check_interval)
                        
                    elif self.state == "BUY_CONFIRM":
                        self.log("進入是否確認購買頁面，發送鍵盤 'Enter'...")
                        direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                        time.sleep(1.0)
                        self.log("發送鍵盤 'Enter' 確認購買...")
                        direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                        self.update_state("BUY_WAIT_ANIMATION")
                        
                    elif self.state == "BUY_WAIT_ANIMATION":
                        if not hasattr(self, "buy_wait_stable_count"):
                            self.buy_wait_stable_count = 0
                            self.buy_wait_last_x, self.buy_wait_last_y = -1, -1
                            
                        # Region: bottom 20% of the screen, i.e., y-axis between 0.8 and 1.0. Higher threshold of 0.75
                        match = self.find_template_on_screen("drive.png", threshold=0.75, region=(0.8, 1.0, 0.0, 1.0))
                        if match:
                            x, y, conf = match
                            if self.buy_wait_last_x != -1 and abs(x - self.buy_wait_last_x) <= 5 and abs(y - self.buy_wait_last_y) <= 5:
                                self.buy_wait_stable_count += 1
                                self.log(f"偵測到穩定的【駕駛】字樣 (置信度: {conf:.2f})，連續第 {self.buy_wait_stable_count} 次確認位置無偏移。")
                            else:
                                self.buy_wait_stable_count = 1
                                self.log(f"偵測到【駕駛】字樣 (座標: {x}, {y}, 置信度: {conf:.2f})，開始穩定度追蹤...")
                            self.buy_wait_last_x, self.buy_wait_last_y = x, y
                        else:
                            if self.buy_wait_stable_count > 0:
                                self.log("【駕駛】字樣消失或位置偏移，重置穩定度追蹤。")
                            self.buy_wait_stable_count = 0
                            self.buy_wait_last_x, self.buy_wait_last_y = -1, -1
                            
                        if self.buy_wait_stable_count >= 3:
                            # Reset tracking variables for next time
                            if hasattr(self, "buy_wait_stable_count"):
                                delattr(self, "buy_wait_stable_count")
                            if hasattr(self, "buy_wait_last_x"):
                                delattr(self, "buy_wait_last_x")
                            if hasattr(self, "buy_wait_last_y"):
                                delattr(self, "buy_wait_last_y")
                            
                            self.log("【駕駛】按鍵已完全穩定出現，過場動畫結束。")
                            self.buy_car_count += 1
                            self.log(f"進度：第 {self.buy_car_count} / 12 輛車購買完成。")
                            
                            # Additional sleep to ensure transition completes fully
                            self.log("等待底端按鍵選單完全啟用 (1.0 秒)...")
                            time.sleep(1.0)
                            
                            if self.buy_car_count >= 12:
                                self.log("已成功購買 12 輛車，達到設定上限，腳本自動停止。")
                                self.stop()
                                break
                            self.log("發送鍵盤 'Esc' 返回汽車展售中心...")
                            direct_input.press_and_release(direct_input.KEY_ESC, duration=0.5)
                            self.update_state("BUY_START")
                            time.sleep(2.0)
                        else:
                            # Check again after a short delay
                            time.sleep(0.5)
                        
                except Exception as e:
                    self.log(f"自動購車循環中發生異常錯誤: {e}")
                    time.sleep(2.0)
                    
            self.update_state("IDLE")
            return

        if self.mode == "CAR_MASTERY":
            self.log("正在啟動自動解鎖車輛熟練度模式...")
            self.update_state("MASTERY_START")
            
            while self.is_running:
                try:
                    if cv2 is None:
                        time.sleep(2.0)
                        continue
                        
                    if self.state == "MASTERY_START":
                        match = self.find_template_on_screen("my_cars_tile.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【我的車輛】按鈕 (置信度: {conf:.2f})")
                            self.log("模擬滑鼠點擊「我的車輛」...")
                            direct_input.mouse_click(x, y, click_duration=0.15, settle_delay=0.15)
                            self.update_state("MASTERY_OPEN_MANUFACTURER")
                            time.sleep(2.5)
                        else:
                            if self.find_template_on_screen("lambo_brand.png"):
                                self.log("💡 [自動狀態修正]：已在車廠選單中，修正狀態至【選擇車廠】")
                                self.update_state("MASTERY_SELECT_MANUFACTURER")
                            elif self.find_template_on_screen("revuelto.png"):
                                self.log("💡 [自動狀態修正]：已在車輛選單中，修正狀態至【選擇車輛】")
                                self.update_state("MASTERY_SELECT_CAR")
                            else:
                                time.sleep(self.check_interval)
                                
                    elif self.state == "MASTERY_OPEN_MANUFACTURER":
                        self.log("已進入車庫，發送鍵盤 'Backspace' 開啟車廠選單...")
                        direct_input.press_and_release(direct_input.KEY_BACKSPACE, duration=0.5)
                        self.update_state("MASTERY_SELECT_MANUFACTURER")
                        time.sleep(1.5)
                        
                    elif self.state == "MASTERY_SELECT_MANUFACTURER":
                        match = self.find_template_on_screen("lambo_brand.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【LAMBORGHINI】車廠標誌 (置信度: {conf:.2f})")
                            self.log("模擬滑鼠點擊進入車廠選單...")
                            direct_input.mouse_click(x, y, click_duration=0.15, settle_delay=0.15)
                            self.update_state("MASTERY_SELECT_CAR")
                            time.sleep(2.0)
                        else:
                            if self.find_template_on_screen("revuelto.png"):
                                self.log("💡 [自動狀態修正]：已在車輛選單中，修正狀態至【選擇車輛】")
                                self.update_state("MASTERY_SELECT_CAR")
                            else:
                                time.sleep(self.check_interval)
                                
                    elif self.state == "MASTERY_SELECT_CAR":
                        matches = self.find_all_templates_on_screen("revuelto.png")
                        if matches:
                            self.log(f"畫面中偵測到 {len(matches)} 輛 REVUELTO 車輛卡片")
                            if self.mastery_car_index < len(matches):
                                x, y, conf = matches[self.mastery_car_index]
                                self.log(f"滑鼠先移至第 {self.mastery_car_index + 1} 輛未使用過之車輛位置 (座標: {x}, {y})，等待 0.5 秒以觸發懸停狀態...")
                                direct_input.set_cursor_pos(x, y)
                                time.sleep(0.5)
                                self.log(f"模擬滑鼠點擊選中車輛 (置信度: {conf:.2f})...")
                                direct_input.mouse_click(x, y, click_duration=0.15, settle_delay=0.05)
                                # 等待選單位移與動畫完成，發送 Enter 開啟選單
                                time.sleep(1.0)
                                self.log("發送鍵盤 'Enter' 鍵以叫出乘駕選單...")
                                direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                                self.update_state("MASTERY_DRIVE_PROMPT")
                                time.sleep(1.5)
                            else:
                                self.log(f"所有畫面上偵測到的 {len(matches)} 輛車均已點過熟練度，腳本停止。")
                                self.stop()
                                break
                        else:
                            time.sleep(self.check_interval)
                            
                    elif self.state == "MASTERY_DRIVE_PROMPT":
                        match = self.find_template_on_screen("drive_car.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【乘駕車輛】按鈕 (置信度: {conf:.2f})，按下 Enter 選擇...")
                            direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                            self.update_state("MASTERY_ENTER_UPGRADES")
                            self.log("正在進入車庫並更換乘駕車輛，等待 6 秒過場...")
                            time.sleep(6.0)
                        else:
                            if self.find_template_on_screen("upgrades_tuning.png"):
                                self.log("💡 [自動狀態修正]：已越過乘駕車輛，直接進入升級選單")
                                self.update_state("MASTERY_ENTER_UPGRADES")
                            else:
                                time.sleep(self.check_interval)
                                
                    elif self.state == "MASTERY_ENTER_UPGRADES":
                        match = self.find_template_on_screen("upgrades_tuning.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【升級套件與調校】入口 (置信度: {conf:.2f})")
                            self.log("模擬滑鼠點擊「升級套件與調校」...")
                            direct_input.mouse_click(x, y, click_duration=0.15, settle_delay=0.15)
                            self.update_state("MASTERY_ENTER_MASTERY")
                            time.sleep(2.0)
                        else:
                            if self.find_template_on_screen("car_mastery_button.png"):
                                self.log("💡 [自動狀態修正]：已越過升級套件，直接進入熟練度選單")
                                self.update_state("MASTERY_ENTER_MASTERY")
                            else:
                                time.sleep(self.check_interval)
                                
                    elif self.state == "MASTERY_ENTER_MASTERY":
                        match = self.find_template_on_screen("car_mastery_button.png")
                        if match:
                            x, y, conf = match
                            self.log(f"偵測到【車輛熟練度】入口 (置信度: {conf:.2f})")
                            self.log("模擬滑鼠點擊「車輛熟練度」...")
                            direct_input.mouse_click(x, y, click_duration=0.15, settle_delay=0.15)
                            self.update_state("MASTERY_UNLOCK_SKILLS")
                            time.sleep(2.5)
                        else:
                            time.sleep(self.check_interval)
                            
                    elif self.state == "MASTERY_UNLOCK_SKILLS":
                        if not self.mastery_grid_topleft or not self.mastery_grid_bottomright:
                            self.log("錯誤：缺少技能樹校準座標，無法點選技能！")
                            self.stop()
                            break
                            
                        # User path: (3, 0) -> (2, 0) -> (1, 0) -> (0, 0) -> (0, 1) -> (0, 2)
                        path = [(3, 0), (2, 0), (1, 0), (0, 0), (0, 1), (0, 2)]
                        
                        hwnd, rect = self.find_game_window()
                        if not rect:
                            self.log("錯誤：找不到遊戲視窗，無法定位技能點。")
                            self.stop()
                            break
                            
                        offset_x, offset_y = rect[0], rect[1]
                        x_tl, y_tl = self.mastery_grid_topleft
                        x_br, y_br = self.mastery_grid_bottomright
                        
                        step_x = (x_br - x_tl) / 3.0
                        step_y = (y_br - y_tl) / 3.0
                        
                        self.log("開始依序解鎖車輛熟練度技能點...")
                        for step_idx, (row, col) in enumerate(path):
                            if not self.is_running:
                                break
                            
                            rel_x = x_tl + col * step_x
                            rel_y = y_tl + row * step_y
                            abs_x = int(offset_x + rel_x)
                            abs_y = int(offset_y + rel_y)
                            
                            self.log(f"點選技能點 [{step_idx + 1}/6]：格點 (row={row}, col={col}) -> 螢幕座標 ({abs_x}, {abs_y})")
                            direct_input.mouse_click(abs_x, abs_y, click_duration=0.15, settle_delay=0.1)
                            time.sleep(0.5)
                            
                            direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.4)
                            time.sleep(0.8)
                            
                        if not self.is_running:
                            break
                            
                        self.log("技能點擊完成！發送 'Esc' 返回升級調校畫面...")
                        direct_input.press_and_release(direct_input.KEY_ESC, duration=0.5)
                        time.sleep(1.5)
                        
                        self.log("發送 'Esc' 返回車庫大廳頁面...")
                        direct_input.press_and_release(direct_input.KEY_ESC, duration=0.5)
                        time.sleep(2.0)
                        
                        self.mastery_car_index += 1
                        self.save_config()
                        self.log(f"該車解鎖完成。切換至下一輛，目前索引：{self.mastery_car_index}")
                        self.update_state("MASTERY_START")
                        time.sleep(1.0)
                        
                except Exception as e:
                    self.log(f"自動點選熟練度循環中發生異常錯誤: {e}")
                    time.sleep(2.0)
                    
            self.update_state("IDLE")
            return

        self.log("正在分析當前遊戲畫面，嘗試自動判定所處階段...")
        
        detected_state = "WAIT_FOR_SETTLEMENT"
        immediate_action = None
        try:
            # We check yes.png first as a confirmation prompt is distinct in the center
            yes_match = self.find_template_on_screen("yes.png")
            if yes_match:
                detected_state = "WAIT_FOR_CONFIRM"
                self.log("自動判定成功：目前處於【確認重新開始彈窗】")
                immediate_action = "YES"
            else:
                restart_match = self.find_template_on_screen("restart.png")
                if restart_match:
                    detected_state = "WAIT_FOR_SETTLEMENT"
                    self.log("自動判定成功：目前處於【結算畫面】")
                    immediate_action = "RESTART"
                else:
                    start_match = self.find_template_on_screen("start.png")
                    if start_match:
                        detected_state = "WAIT_FOR_START_EVENT"
                        self.log("自動判定成功：目前處於【賽事準備起跑畫面】")
                        immediate_action = "START"
                    else:
                        self.log("未偵測到已知特徵，預設進入【等待結算畫面】偵測狀態。")
        except Exception as e:
            self.log(f"自動判定階段發生異常: {e}，預設進入【等待結算畫面】")
            
        self.update_state(detected_state)
        
        # Execute immediate action if detected to make startup instant
        if self.is_running and immediate_action:
            if immediate_action == "YES":
                self.log("啟動瞬時響應：發送鍵盤 'Enter' 按鍵確認重新開始...")
                direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                self.update_state("WAIT_FOR_START_EVENT")
                time.sleep(3.0)
            elif immediate_action == "RESTART":
                self.log("啟動瞬時響應：發送鍵盤 'X' 按鍵進行重新開始...")
                direct_input.press_and_release(direct_input.KEY_X, duration=0.5)
                self.update_state("WAIT_FOR_CONFIRM")
                time.sleep(1.0)
            elif immediate_action == "START":
                self.log("啟動瞬時響應：發送鍵盤 'Enter' 按鍵開始賽事...")
                direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                self.update_state("RACING")
                
        while self.is_running:
            try:
                # 確保 OpenCV 已經載入
                if cv2 is None:
                    time.sleep(2.0)
                    continue

                if self.state == "WAIT_FOR_SETTLEMENT":
                    # 辨識畫面是否有「重新開始」按鈕 (restart.png)
                    match = self.find_template_on_screen("restart.png")
                    if match:
                        x, y, conf = match
                        self.log(f"偵測到【重新開始】按鈕 (置信度: {conf:.2f})")
                        self.log("發送鍵盤 'X' 按鍵進行重新開始...")
                        direct_input.press_and_release(direct_input.KEY_X, duration=0.5)
                        self.update_state("WAIT_FOR_CONFIRM")
                        time.sleep(1.0)
                    else:
                        # 備用語音/畫面狀態自適應修正：如果已經跳過此階段
                        if self.find_template_on_screen("yes.png"):
                            self.log("💡 [自動狀態修正]：等待結算時偵測到【是】確認按鈕，修正狀態至【確認選單】")
                            self.update_state("WAIT_FOR_CONFIRM")
                        elif self.find_template_on_screen("start.png"):
                            self.log("💡 [自動狀態修正]：等待結算時偵測到【開始賽事】按鈕，修正狀態至【起跑畫面】")
                            self.update_state("WAIT_FOR_START_EVENT")
                        else:
                            time.sleep(self.check_interval)

                elif self.state == "WAIT_FOR_CONFIRM":
                    # 辨識畫面中央是否有「是」按鈕 (yes.png)
                    match = self.find_template_on_screen("yes.png")
                    if match:
                        x, y, conf = match
                        self.log(f"偵測到【是】確認按鈕 (置信度: {conf:.2f})")
                        self.log("發送鍵盤 'Enter' 按鍵確認重新開始...")
                        direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                        self.update_state("WAIT_FOR_START_EVENT")
                        time.sleep(3.0)
                    else:
                        # 備用語音/畫面狀態自適應修正
                        if self.find_template_on_screen("start.png"):
                            self.log("💡 [自動狀態修正]：等待確認時偵測到【開始賽事】按鈕，修正狀態至【起跑畫面】")
                            self.update_state("WAIT_FOR_START_EVENT")
                        elif self.find_template_on_screen("restart.png"):
                            self.log("💡 [自動狀態修正]：等待確認時偵測到【重新開始】按鈕，修正狀態至【結算畫面】")
                            self.update_state("WAIT_FOR_SETTLEMENT")
                        else:
                            time.sleep(self.check_interval)

                elif self.state == "WAIT_FOR_START_EVENT":
                    # 辨識畫面是否有「開始賽事」按鈕 (start.png)
                    match = self.find_template_on_screen("start.png")
                    if match:
                        x, y, conf = match
                        self.log(f"偵測到【開始賽事】按鈕 (置信度: {conf:.2f})")
                        self.log("發送鍵盤 'Enter' 按鍵開始賽事...")
                        direct_input.press_and_release(direct_input.KEY_ENTER, duration=0.5)
                        self.update_state("RACING")
                    else:
                        # 備用語音/畫面狀態自適應修正
                        if self.find_template_on_screen("restart.png"):
                            self.log("💡 [自動狀態修正]：等待起跑時偵測到【重新開始】按鈕，修正狀態至【結算畫面】")
                            self.update_state("WAIT_FOR_SETTLEMENT")
                        elif self.find_template_on_screen("yes.png"):
                            self.log("💡 [自動狀態修正]：等待起跑時偵測到【是】確認按鈕，修正狀態至【確認選單】")
                            self.update_state("WAIT_FOR_CONFIRM")
                        else:
                            time.sleep(self.check_interval)

                elif self.state == "RACING":
                    self.log("賽事已開始，自動按下 'W' 鍵加速前進...")
                    direct_input.press_key(direct_input.KEY_W)
                    
                    early_exit = False
                    next_state = "WAIT_FOR_SETTLEMENT"
                    try:
                        self.log(f"開始賽事計時等待，共 {self.race_duration} 秒... (前 5 秒為啟動與載入保護期)")
                        start_time = time.time()
                        last_detect_time = time.time()
                        last_w_press_time = time.time()
                        
                        while time.time() - start_time < self.race_duration:
                            if not self.is_running:
                                break
                            
                            current_time = time.time()
                            
                            # 每 2.0 秒重送一次 W 鍵，確保遊戲在控制權移交或載入完成後能確實接收並維持 W 鍵訊號
                            if current_time - last_w_press_time >= 2.0:
                                last_w_press_time = current_time
                                direct_input.press_key(direct_input.KEY_W)
                            
                            # 避開前 5.0 秒的遊戲載入/淡出期，避免誤判尚未完全消失的「開始賽事」按鈕
                            if current_time - start_time > 5.0:
                                if current_time - last_detect_time >= 1.5:
                                    last_detect_time = current_time
                                    # 檢測是否提前進入了結算或確認畫面
                                    if self.find_template_on_screen("restart.png"):
                                        self.log("🔍 [賽事狀態偵測]：在賽事過程中偵測到【重新開始】按鈕，賽事已提前結束！")
                                        early_exit = True
                                        next_state = "WAIT_FOR_SETTLEMENT"
                                        break
                                    elif self.find_template_on_screen("yes.png"):
                                        self.log("🔍 [賽事狀態偵測]：在賽事過程中偵測到【是】確認按鈕，賽事已提前結束！")
                                        early_exit = True
                                        next_state = "WAIT_FOR_CONFIRM"
                                        break
                                    elif self.find_template_on_screen("start.png"):
                                        self.log("🔍 [賽事狀態偵測]：在賽事過程中偵測到【開始賽事】按鈕，賽事可能未開始或已重置！")
                                        early_exit = True
                                        next_state = "WAIT_FOR_START_EVENT"
                                        break
                            
                            time.sleep(0.1)
                    finally:
                        self.log("釋放 'W' 鍵...")
                        direct_input.release_key(direct_input.KEY_W)
                        
                    if not self.is_running:
                        return
                        
                    if early_exit:
                        self.log(f"賽事提前終止，跳轉至狀態: {next_state}")
                        self.update_state(next_state)
                    else:
                        self.log("預定賽事等待時間已到，進入結算畫面偵測狀態。")
                        self.update_state("WAIT_FOR_SETTLEMENT")

            except Exception as e:
                self.log(f"執行循環中發生異常錯誤: {e}")
                time.sleep(2.0)
                
        self.update_state("IDLE")

# Test routine
if __name__ == "__main__":
    bot = ForzaBot()
    # Simple check of screen grab
    screenshot, offset = bot.capture_game_screen()
    print(f"Captured screen size: {screenshot.size}, Top-left offset: {offset}")
