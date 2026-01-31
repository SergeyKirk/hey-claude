#!/bin/bash
# Claude Voice Command System - Management Script

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.user.claude-voice"
PLIST_PATH="$PROJECT_DIR/$PLIST_NAME.plist"
LAUNCHD_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
VENV_PATH="$PROJECT_DIR/.venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

case "$1" in
    install)
        echo -e "${YELLOW}Installing Claude Voice Command System...${NC}"

        # Create virtual environment if it doesn't exist
        if [ ! -d "$VENV_PATH" ]; then
            echo "Creating virtual environment..."
            python3 -m venv "$VENV_PATH"
        fi

        # Activate and install dependencies
        echo "Installing Python dependencies..."
        source "$VENV_PATH/bin/activate"
        pip install --upgrade pip
        pip install -r "$PROJECT_DIR/requirements.txt"

        # Generate plist with environment variable if set
        echo "Installing launchd service..."
        mkdir -p "$HOME/Library/LaunchAgents"

        if [ -n "$PICOVOICE_ACCESS_KEY" ]; then
            # Generate plist with embedded access key
            cat > "$LAUNCHD_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.claude-voice</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PATH/bin/python</string>
        <string>$PROJECT_DIR/claude_voice.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/daemon_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/daemon_stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>PICOVOICE_ACCESS_KEY</key>
        <string>$PICOVOICE_ACCESS_KEY</string>
    </dict>
</dict>
</plist>
EOF
            echo -e "${GREEN}Access key embedded in launchd service${NC}"
        else
            # Generate plist without access key (user must set via config.yaml)
            cat > "$LAUNCHD_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.claude-voice</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PATH/bin/python</string>
        <string>$PROJECT_DIR/claude_voice.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/daemon_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/daemon_stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF
            echo -e "${YELLOW}Note: Set PICOVOICE_ACCESS_KEY env var before install to embed in service${NC}"
            echo -e "${YELLOW}      Or create config.yaml with your access key${NC}"
        fi

        echo -e "${GREEN}Installation complete!${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Get your Picovoice access key from https://console.picovoice.ai/"
        echo "2. Set your access key (choose one):"
        echo "   Option A: export PICOVOICE_ACCESS_KEY='your-key' (add to ~/.zshrc)"
        echo "   Option B: cp config.yaml.example config.yaml && edit config.yaml"
        echo "3. Download your Hey-Claude wake word model from Picovoice Console"
        echo "4. Run: ./manage.sh start"
        ;;

    start)
        echo -e "${YELLOW}Starting Claude Voice Command System...${NC}"

        # Check if access key is configured (via env var or config file)
        if [ -z "$PICOVOICE_ACCESS_KEY" ]; then
            if [ -f "$PROJECT_DIR/config.yaml" ]; then
                if grep -q "YOUR_PICOVOICE_ACCESS_KEY" "$PROJECT_DIR/config.yaml"; then
                    echo -e "${RED}Error: Picovoice access key not configured!${NC}"
                    echo "Set PICOVOICE_ACCESS_KEY env var or edit config.yaml"
                    exit 1
                fi
            else
                echo -e "${RED}Error: PICOVOICE_ACCESS_KEY not set and no config.yaml found!${NC}"
                echo "Set: export PICOVOICE_ACCESS_KEY='your-key'"
                echo "Or:  cp config.yaml.example config.yaml && edit"
                exit 1
            fi
        fi

        # Check if whisper service is running
        if ! curl -s http://localhost:2022/health > /dev/null 2>&1; then
            echo -e "${YELLOW}Warning: Whisper service not detected on port 2022${NC}"
            echo "Starting whisper service..."
            voicemode service start whisper 2>/dev/null || echo "Could not auto-start whisper"
        fi

        # Load the launchd job
        if [ -f "$LAUNCHD_PATH" ]; then
            launchctl load "$LAUNCHD_PATH" 2>/dev/null
            launchctl start "$PLIST_NAME" 2>/dev/null
            echo -e "${GREEN}Service started!${NC}"
            echo "Say 'Hey Claude' to activate."
        else
            echo -e "${RED}Service not installed. Run: ./manage.sh install${NC}"
            exit 1
        fi
        ;;

    stop)
        echo -e "${YELLOW}Stopping Claude Voice Command System...${NC}"
        launchctl stop "$PLIST_NAME" 2>/dev/null
        launchctl unload "$LAUNCHD_PATH" 2>/dev/null
        echo -e "${GREEN}Service stopped.${NC}"
        ;;

    restart)
        $0 stop
        sleep 1
        $0 start
        ;;

    status)
        if launchctl list | grep -q "$PLIST_NAME"; then
            echo -e "${GREEN}Claude Voice System is running${NC}"
            launchctl list "$PLIST_NAME"
        else
            echo -e "${YELLOW}Claude Voice System is not running${NC}"
        fi
        ;;

    logs)
        echo "=== Recent Voice Commands ==="
        tail -20 "$PROJECT_DIR/logs/command_history.log" 2>/dev/null || echo "No commands logged yet"
        echo ""
        echo "=== Recent System Logs ==="
        tail -30 "$PROJECT_DIR/logs/voice_commands.log" 2>/dev/null || echo "No logs yet"
        ;;

    run)
        # Run in foreground (for testing)
        echo -e "${YELLOW}Running in foreground (Ctrl+C to stop)...${NC}"
        source "$VENV_PATH/bin/activate"
        python "$PROJECT_DIR/claude_voice.py"
        ;;

    uninstall)
        echo -e "${YELLOW}Uninstalling Claude Voice Command System...${NC}"
        $0 stop
        rm -f "$LAUNCHD_PATH"
        echo -e "${GREEN}Service uninstalled.${NC}"
        echo "Project files remain in: $PROJECT_DIR"
        ;;

    *)
        echo "Claude Voice Command System - Management Script"
        echo ""
        echo "Usage: $0 {install|start|stop|restart|status|logs|run|uninstall}"
        echo ""
        echo "Commands:"
        echo "  install   - Install dependencies and launchd service"
        echo "  start     - Start the voice command daemon"
        echo "  stop      - Stop the daemon"
        echo "  restart   - Restart the daemon"
        echo "  status    - Check if daemon is running"
        echo "  logs      - View recent logs and command history"
        echo "  run       - Run in foreground (for testing)"
        echo "  uninstall - Remove launchd service"
        ;;
esac
