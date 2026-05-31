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
        
        self.state = "IDLE"  # IDLE, WAIT_FOR_SETTLEMENT, WAIT_FOR_CONFIRM, WAIT_FOR_START_EVENT, RACING
        self.is_running = False
        self.thread = None
        self.log_callback = print # Can be replaced by GUI log function
        self.state_callback = None # Can be replaced by GUI state update function
        
        # Ensure templates directory exists
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)

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

    def find_template_on_screen(self, template_filename):
        """Searches for a template image on the game screen."""
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
        
        # Ensure template is smaller than screen
        if w > img_gray.shape[1] or h > img_gray.shape[0]:
            self.log(f"錯誤: 模板尺寸 {w}x{h} 大於畫面尺寸 {img_gray.shape[1]}x{img_gray.shape[0]}")
            return None
            
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val >= self.threshold:
            # relative center of match
            rel_x = max_loc[0] + w // 2
            rel_y = max_loc[1] + h // 2
            # absolute center of match on screen
            abs_x = offset[0] + rel_x
            abs_y = offset[1] + rel_y
            return abs_x, abs_y, max_val
            
        return None

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
        self.update_state("IDLE")
        self.log("腳本已停止運作。")

    def _run_loop(self):
        """Main execution loop."""
        # Wait for CV2 to load if needed
        while cv2 is None and self.is_running:
            time.sleep(1.0)
            
        if not self.is_running:
            return

        self.log("正在分析當前遊戲畫面，嘗試自動判定所處階段...")
        
        detected_state = "WAIT_FOR_SETTLEMENT"
        try:
            # We check yes.png first as a confirmation prompt is distinct in the center
            if self.find_template_on_screen("yes.png"):
                detected_state = "WAIT_FOR_CONFIRM"
                self.log("自動判定成功：目前處於【確認重新開始彈窗】")
            elif self.find_template_on_screen("restart.png"):
                detected_state = "WAIT_FOR_SETTLEMENT"
                self.log("自動判定成功：目前處於【結算畫面】")
            elif self.find_template_on_screen("start.png"):
                detected_state = "WAIT_FOR_START_EVENT"
                self.log("自動判定成功：目前處於【賽事準備起跑畫面】")
            else:
                self.log("未偵測到已知特徵，預設進入【等待結算畫面】偵測狀態。")
        except Exception as e:
            self.log(f"自動判定階段發生異常: {e}，預設進入【等待結算畫面】")
            
        self.update_state(detected_state)
        
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
                        # 稍微等待遊戲反應
                        time.sleep(1.0)
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
                        # 等待場景轉跳
                        time.sleep(3.0)
                    else:
                        # 預防錯過或按鍵沒點到，可重複嘗試，或等待
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
                        time.sleep(self.check_interval)

                elif self.state == "RACING":
                    self.log("賽事已開始，自動按下 'W' 鍵加速前進...")
                    direct_input.press_key(direct_input.KEY_W)
                    
                    try:
                        self.log(f"開始賽事計時等待，共 {self.race_duration} 秒...")
                        start_time = time.time()
                        while time.time() - start_time < self.race_duration:
                            if not self.is_running:
                                break
                            time.sleep(0.1)
                    finally:
                        self.log("賽事時間已到或腳本停止，釋放 'W' 鍵...")
                        direct_input.release_key(direct_input.KEY_W)
                        
                    if not self.is_running:
                        return
                        
                    self.log("等待時間已到，預期賽事已結束，進入結算畫面偵測狀態。")
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
