# Forza Horizon 6 Skill Farming Bot (Skill Farming Bot)

Language / 語言: [繁體中文 (Traditional Chinese)](README.md) | [English](README_EN.md)

This is an automated skill farming assistant tool designed for the *Forza Horizon* series. The tool uses **OpenCV image recognition (template matching)** to detect game states and leverages Windows low-level **DirectInput keyboard and mouse emulation** to automatically restart races or execute operations, achieving fully unattended, automated skill farming.

This project features a modern dark-themed graphical user interface (GUI) and a built-in image cropping calibration tool, ensuring perfect compatibility with various screen resolutions and game languages.

---

## Features

- **DirectInput Emulation**: Uses the Windows `SendInput` API, 100% bypassing the game's blocking of standard keyboard inputs for a secure and stable connection.
- **Custom Template Calibration**: Built-in screenshot cropping tool allows you to select templates directly from your game screen by dragging and highlighting buttons, resolving resolution and localization compatibility issues.
- **Global Hotkeys**: Press `F10` at any time while playing to start automation, and press `F11` to immediately stop. Includes a safe key release mechanism for the `W` key.
- **Automatic Driving**: Automatically holds down the `W` key during races to keep the vehicle moving forward, releasing it immediately when the race duration ends.
- **Smart Startup Detection**: Upon launch, the assistant automatically identifies whether the game is currently on the "Results/Settlement" screen, "Restart Confirmation Dialog", or the "Starting Grid", seamlessly proceeding to the next step without requiring you to wait from the beginning.
- **Stay-on-Top Toggle**: Choose the running game window from a dropdown menu and toggle the "Always on Top" option to keep the game in focus, preventing other windows from blocking detection.
- **Background Idle Guide**: Click the "❓ Background Idle Guide" button in the Settings page to view detailed instructions on how to use the free utility DisplayFusion's "Prevent Window Deactivation" feature or a Windows Virtual Machine (VM) to idle the game in the background without freeze, with 100% account safety (no DLL injection).
- **Auto-Stop Timer**: Configure automatic script termination (e.g., `1 Hour`, `1.5 Hours`, `2 Hours`, etc.) with a live countdown timer displayed in the GUI. The script stops safely when the timer expires.
- **Auto-Purchase Mode**: Automatically clicks the Autoshow, filters by manufacturer, selects the Lamborghini Revuelto, paints it, confirms purchase, waits out the delivery cutscene, and loops.
- **Auto-Mastery (Skill Tree) Mode**: Automatically enters your garage, filters by manufacturer, selects unprocessed cars in order, drives them, enters the Upgrade & Tuning section, goes to the Car Mastery page, unlocks 6 critical skill nodes (3,0 -> 2,0 -> 1,0 -> 0,0 -> 0,1 -> 0,2) on the 4x4 grid, returns to the garage lobby, and repeats. Handles screen shifts dynamically and records progress indices.

---

## Installation & Setup

Before running this tool, please ensure you complete the following steps:

### 1. Install Python
- Download and install **Python 3.12** or higher from the [Official Python Website](https://www.python.org/).
- **[IMPORTANT]** Make sure to check the box **"Add Python.exe to PATH"** during installation.

### 2. Install Python Dependencies
- **One-click Auto-installation (Recommended)**: Double-click the **`install_requirements.bat`** file in the project folder. It will launch the command prompt and install all required Python packages (including OpenCV, Pillow, and pywin32) automatically.
- **Manual Installation**: Open Command Prompt (CMD) and run the following command:
  ```bash
  pip install opencv-python pillow pywin32
  ```

### 3. Game Graphics Settings
To ensure the screenshot matching works correctly, configure the graphics settings in *Forza Horizon*:
- Set the Display Mode to **"Windowed"** or **"Borderless Windowed"**.
- ⚠️ Do NOT use "Exclusive Fullscreen" mode, otherwise the script will capture black screenshots.

---

## User Manual

### 1. Run as Administrator
- Right-click **`run_bot.bat`** in the project folder.
- Choose **"Run as Administrator"** (Since the game runs with elevated privileges, the assistant requires the same privilege level to simulate key presses).

### 2. Calibrate Image Templates (Required for First-time Use)
- Open the assistant GUI and bring the game window to the screen.
- Go to the "Image Calibration" tab in the GUI, and click **"Capture"** for each template:
  - **Restart Button (`restart.png`)**: Capture this on the race settlement screen, drag and draw a red rectangle over the "Restart" text.
  - **Confirm "Yes" (`yes.png`)**: In the confirmation dialog that pops up after clicking restart, draw a box over the "Yes" button.
  - **Start Race (`start.png`)**: Capture this on the pre-race grid screen, drawing a box over the "Start Race" button.
- Once captured, a thumbnail preview will be shown, and the label will turn green, indicating successful calibration.

### 3. Configure Settings
- In the "Settings" tab, configure the race duration in seconds (e.g., `62` seconds).
- Click **"Save Settings"** to apply changes.

### 4. Start & Stop
- While in the game, press **`F10`** on your keyboard (or click "Start Script") to begin automation.
- Press **`F11`** (or click "Stop Script") to pause or end, releasing any pressed keys safely.

### 5. Auto Car Purchase Mode
- **Switch Mode**: Select **"Auto Car Purchase (Revuelto)"** under the mode selection on the Dashboard.
- **Calibrate Templates**: Go to the "Image Calibration" tab, click "Capture" and draw boxes in the game for the following:
  - **Autoshow Entrance (`autoshow.png`)**: Draw over the "Autoshow" tile on the garage home menu.
  - **Lamborghini Logo (`lambo_brand.png`)**: Draw over the "LAMBORGHINI" manufacturer icon.
  - **Revuelto Card (`revuelto.png`)**: Draw over the "REVUELTO" vehicle card in the store.
  - **Factory Colors (`factory_colors.png`)**: Draw over the "Factory Colors" title in the livery customization page.
  - **Drive (`drive.png`)**: Draw over the "Drive" prompt that appears after the delivery cutscene ends.
- **Run**: Navigate to the garage home menu, and press **`F10`**. The bot will automatically buy cars in batches and stop once it reaches the limit of 12.

### 6. Auto Car Mastery Mode
- **Switch Mode**: Select **"Auto Car Mastery"** on the Dashboard.
- **Calibrate Templates**: Go to the "Image Calibration" tab, click "Capture" and draw boxes in the game for the following:
  - **My Cars Tile (`my_cars_tile.png`)**: Draw over the "My Cars" button on the garage home menu.
  - **Drive Car Prompt (`drive_car.png`)**: Draw over the "Drive Car" button in the selection prompt.
  - **Upgrades & Tuning Tile (`upgrades_tuning.png`)**: Draw over the "Upgrades & Tuning" button on the garage lobby menu.
  - **Car Mastery Entry (`car_mastery_button.png`)**: Draw over the "Car Mastery" button in the upgrade list.
- **Calibrate Grid**: In the "4x4 Skill Tree Grid Calibration" section, click "Calibrate Top-Left" and "Calibrate Bottom-Right" and click the centers of the top-left and bottom-right nodes on the 4x4 skill tree.
- **Run**: Navigate to the garage home menu, and press **`F10`**. The bot will process cars one by one, unlocking 6 nodes on the skill tree per vehicle, and automatically increment the index.

---

## File Manifest
- `gui.py`: Tkinter graphical user interface application.
- `bot.py`: Automation machine and OpenCV detection engine.
- `direct_input.py`: Low-level keyboard/mouse driver simulation.
- `run_bot.bat`: One-click administrator start script.

---

## Background Idle & Anti-Freeze Guide

Since the *Forza Horizon* series uses DirectX 12 rendering and Raw Input, losing window focus (e.g., pressing Alt-Tab) causes the game to auto-pause, drop frame rates, and ignore simulated inputs.

### ⚠️ Security & Input Limitations Warnings
1. **Safety Design**: To bypass focus detection programmatically, a DLL must be injected into the game process. However, this is detected as a cheat by Easy Anti-Cheat and leads to **permanent account bans**. This assistant **never performs any dangerous DLL injections**.
2. **Input Leakage**: The assistant uses the Windows `SendInput` API for hardware-level keyboard simulation. `SendInput` keys **only go to the active window**. If you type in Chrome or Discord while the bot is active, simulated keys (W, X, Enter) will write into your applications, disrupting your work.

### 💡 Solutions & Best Practices

#### Method A: Using DisplayFusion (Best for Dual Monitors / Monitoring Only)
1. Set the game to **"Borderless Windowed"** mode.
2. Install [DisplayFusion](https://www.displayfusion.com/) (Free version is sufficient).
3. Under "Settings -> Functions", find **"Prevent Window Deactivation"** and assign a hotkey (e.g., `Ctrl + Alt + P`).
4. Click inside the game window, and press the assigned hotkey.
5. You can now move your mouse to the second screen to watch videos or browse with your mouse, and the game will not pause. *(Do not type on the keyboard, as keys will still leak to your active typing window).*

#### Method B: Using Windows VM (Recommended, Allow Working While Idle)
1. Install Hyper-V, VMware, or VirtualBox.
2. Ensure **GPU 3D Acceleration** (GPU Passthrough) is enabled to support DirectX 12 games.
3. Run the game and the assistant inside the Virtual Machine.
4. Once started, you can minimize the VM. Simulated keystrokes will be isolated inside the VM, allowing you to work, type, and play other games on your host PC seamlessly.

#### Method C: Auto-Stop Timer (For Offline Idle)
- Enable the "Auto-Stop Timer" in the Settings tab (e.g. 1 hour or 2 hours) and keep the game in the foreground. The bot will automatically close and lock keys when done, conserving PC power.
