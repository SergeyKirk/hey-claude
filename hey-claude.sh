#!/bin/bash
# Hey Claude - Voice Command System

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PATH="$PROJECT_DIR/.venv"
APP_NAME="Hey Claude"
APP_PATH="$PROJECT_DIR/dist/$APP_NAME.app"
RESOURCES_PATH="$APP_PATH/Contents/Resources"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

case "$1" in
    install)
        echo -e "${BLUE}=== Hey Claude - Installation ===${NC}"
        echo ""

        # Create virtual environment
        if [ ! -d "$VENV_PATH" ]; then
            echo -e "${YELLOW}Creating virtual environment...${NC}"
            python3 -m venv "$VENV_PATH"
        fi

        # Install dependencies
        echo -e "${YELLOW}Installing Python dependencies...${NC}"
        source "$VENV_PATH/bin/activate"
        pip3 install --upgrade pip -q
        pip3 install -r "$PROJECT_DIR/requirements.txt" -q
        pip3 install py2app -q

        # Create logs directory
        mkdir -p "$PROJECT_DIR/logs"

        echo ""
        echo -e "${GREEN}Installation complete!${NC}"
        echo ""
        echo -e "${BLUE}Next steps:${NC}"
        echo "1. Get Picovoice credentials:"
        echo "   - Go to https://console.picovoice.ai/"
        echo "   - Sign up (free) and copy your Access Key"
        echo "   - Go to Porcupine > Custom Wake Word"
        echo "   - Type 'Hey Claude', select macOS (arm64), download"
        echo ""
        echo "2. Set up wake word model:"
        echo "   mkdir -p wake-word"
        echo "   mv ~/Downloads/Hey-Claude_*.ppn wake-word/hey-claude.ppn"
        echo ""
        echo "3. Configure:"
        echo "   cp config.yaml.example config.yaml"
        echo "   # Edit config.yaml - add your Picovoice access key"
        echo ""
        echo "4. Test in foreground:"
        echo "   ./hey-claude.sh run"
        echo ""
        echo "5. Build background app:"
        echo "   ./hey-claude.sh build-app"
        ;;

    run)
        echo -e "${YELLOW}Running Hey Claude in foreground (Ctrl+C to stop)...${NC}"
        echo ""

        # Check config exists
        if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
            echo -e "${RED}Error: config.yaml not found${NC}"
            echo "Run: cp config.yaml.example config.yaml"
            exit 1
        fi

        # Check wake word model exists
        if [ ! -f "$PROJECT_DIR/wake-word/hey-claude.ppn" ]; then
            echo -e "${RED}Error: Wake word model not found at wake-word/hey-claude.ppn${NC}"
            echo "Download from Picovoice Console and place in wake-word/ folder"
            exit 1
        fi

        source "$VENV_PATH/bin/activate"
        python3 "$PROJECT_DIR/claude_voice.py"
        ;;

    build-app)
        echo -e "${BLUE}=== Building Hey Claude App ===${NC}"
        echo ""

        # Check prerequisites
        if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
            echo -e "${RED}Error: config.yaml not found${NC}"
            echo "Run: cp config.yaml.example config.yaml"
            exit 1
        fi

        if [ ! -f "$PROJECT_DIR/wake-word/hey-claude.ppn" ]; then
            echo -e "${RED}Error: Wake word model not found${NC}"
            echo "Place your .ppn file at: wake-word/hey-claude.ppn"
            exit 1
        fi

        # Clean previous builds
        echo -e "${YELLOW}Cleaning previous builds...${NC}"
        rm -rf "$PROJECT_DIR/build" "$PROJECT_DIR/dist"

        # Build app
        echo -e "${YELLOW}Building app with py2app...${NC}"
        source "$VENV_PATH/bin/activate"
        python3 "$PROJECT_DIR/setup.py" py2app --quiet 2>/dev/null

        if [ ! -d "$APP_PATH" ]; then
            echo -e "${RED}Build failed!${NC}"
            exit 1
        fi

        # Copy resources
        echo -e "${YELLOW}Copying configuration and wake word model...${NC}"
        cp "$PROJECT_DIR/config.yaml" "$RESOURCES_PATH/"
        cp -r "$PROJECT_DIR/wake-word" "$RESOURCES_PATH/"
        mkdir -p "$RESOURCES_PATH/logs"

        echo ""
        echo -e "${GREEN}Build complete!${NC}"
        echo ""
        echo -e "App location: ${BLUE}$APP_PATH${NC}"
        echo ""
        echo "To start the app:"
        echo "  ./hey-claude.sh start-app"
        echo ""
        echo "To auto-start at login:"
        echo "  1. Open System Settings > General > Login Items"
        echo "  2. Click + under 'Open at Login'"
        echo "  3. Select: dist/Hey Claude.app"
        ;;

    start-app)
        if [ ! -d "$APP_PATH" ]; then
            echo -e "${RED}App not built yet. Run: ./hey-claude.sh build-app${NC}"
            exit 1
        fi

        echo -e "${YELLOW}Starting Hey Claude app...${NC}"
        open "$APP_PATH"

        sleep 2
        if pgrep -f "Hey Claude" > /dev/null; then
            echo -e "${GREEN}Hey Claude is running!${NC}"
            echo "Say 'Hey Claude' to activate."
        else
            echo -e "${RED}App may have crashed. Check Console.app for details.${NC}"
        fi
        ;;

    stop-app)
        echo -e "${YELLOW}Stopping Hey Claude app...${NC}"
        pkill -f "Hey Claude" 2>/dev/null || true
        pkill -f "claude_voice" 2>/dev/null || true
        echo -e "${GREEN}Stopped.${NC}"
        ;;

    logs)
        echo "=== Recent Voice Commands ==="
        tail -20 "$PROJECT_DIR/logs/command_history.log" 2>/dev/null || echo "No commands logged yet"
        echo ""
        echo "=== Recent System Logs ==="
        tail -30 "$PROJECT_DIR/logs/voice_commands.log" 2>/dev/null || echo "No logs yet"
        ;;

    status)
        if pgrep -f "Hey Claude" > /dev/null || pgrep -f "claude_voice" > /dev/null; then
            echo -e "${GREEN}Hey Claude is running${NC}"
            ps aux | grep -E "(Hey Claude|claude_voice)" | grep -v grep
        else
            echo -e "${YELLOW}Hey Claude is not running${NC}"
        fi
        ;;

    *)
        echo -e "${BLUE}Hey Claude - Voice Command System${NC}"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  install     Install dependencies (run first)"
        echo "  run         Run in foreground (for testing)"
        echo "  build-app   Build standalone macOS app"
        echo "  start-app   Start the background app"
        echo "  stop-app    Stop the background app"
        echo "  status      Check if running"
        echo "  logs        View recent logs"
        echo ""
        echo "Quick start:"
        echo "  ./hey-claude.sh install"
        echo "  ./hey-claude.sh run        # Test first"
        echo "  ./hey-claude.sh build-app  # Build background app"
        echo "  ./hey-claude.sh start-app  # Run in background"
        ;;
esac
