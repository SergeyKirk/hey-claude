# Hey Claude - Voice Command System

Always-on macOS voice assistant that listens for "Hey Claude" and executes commands via Claude Code.

## Features

- Wake word detection ("Hey Claude") using Picovoice Porcupine
- Natural voice commands with "over" end trigger (or 2-second pause)
- Automatic Claude Code execution in new iTerm tab
- Voice responses via VoiceMode MCP (Whisper + Kokoro TTS)
- Built-in mic support to avoid Bluetooth audio quality issues
- Secure access key handling via environment variables or config file

## Prerequisites

- **macOS** with Apple Silicon (M1/M2/M3/M4)
- **Python 3.10+**
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)** installed and configured
- **[VoiceMode MCP](https://github.com/mbailey/voicemode)** with Whisper and Kokoro services running
- **[Picovoice](https://picovoice.ai/)** account (free tier available)
- **iTerm2** (recommended) or Terminal.app

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/SergeyKirk/hey-claude.git
cd hey-claude
./manage.sh install
```

### 2. Get Picovoice Credentials

1. Go to [console.picovoice.ai](https://console.picovoice.ai/)
2. Sign up (free tier) and copy your **Access Key**
3. Navigate to **Porcupine > Custom Wake Word**
4. Type "Hey Claude", select **macOS (arm64)**, and download the `.ppn` file
5. Extract and place the wake word folder (e.g., `Hey-Claude_en_mac_v4_0_0/`) in the project directory

### 3. Configure Access Key

**Option A: Environment Variable (Recommended)**
```bash
# Add to ~/.zshrc or ~/.bashrc
export PICOVOICE_ACCESS_KEY='your-access-key-here'
source ~/.zshrc
```

**Option B: Config File**
```bash
cp config.yaml.example config.yaml
# Edit config.yaml and set picovoice.access_key
```

### 4. Start Voice Services

Ensure VoiceMode services are running:
```bash
voicemode service start whisper  # STT on port 2022
voicemode service start kokoro   # TTS on port 8880
```

### 5. Run Hey Claude

```bash
./manage.sh run
```

Keep this terminal window open - the voice assistant runs in the foreground.

## Usage

1. Say **"Hey Claude"** to activate
2. Speak your command naturally
3. Say **"over"** to finish (or pause for 2 seconds)
4. Claude executes in a new iTerm tab and responds via voice
5. After Claude finishes, say "Hey Claude" again for the next command

### Example Commands

- "Hey Claude, what time is it, over"
- "Hey Claude, create a Python function to sort a list, over"
- "Hey Claude, explain this error message, over"
- "Hey Claude, summarize this file, over"

## Management Commands

```bash
./manage.sh install   # Install dependencies
./manage.sh run       # Run the voice assistant (foreground)
./manage.sh logs      # View command history & logs
./manage.sh uninstall # Remove launchd service (if installed)
```

## Configuration

Edit `config.yaml` (copy from `config.yaml.example`):

```yaml
picovoice:
  access_key: "YOUR_KEY"  # Or use PICOVOICE_ACCESS_KEY env var
  wake_word_model: "Hey-Claude_en_mac_v4_0_0/Hey-Claude_en_mac_v4_0_0.ppn"

command:
  end_keyword: "over"      # Word to end commands
  silence_timeout: 2.0     # Seconds of silence to auto-end
  max_duration: 30.0       # Maximum command length

audio:
  input_device: "default"  # Or "MacBook Pro Microphone" to force built-in mic

claude:
  working_directory: "~/Documents"
  binary_path: "/opt/homebrew/bin/claude"

terminal:
  app: "iterm"  # or "terminal"
```

### Bluetooth Audio Quality Fix

If you use Bluetooth headphones and experience degraded audio quality, configure `input_device` to use your Mac's built-in microphone:

```yaml
audio:
  input_device: "MacBook Pro Microphone"  # or "Built-in Microphone"
```

This uses the built-in mic for wake word detection without affecting your headphone audio output. Your calls and other apps still use Bluetooth normally.

To list available input devices:
```bash
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  Porcupine Wake Word Detection              │
│  (always listening, <1% CPU)                │
└─────────────────┬───────────────────────────┘
                  │ "Hey Claude" detected
                  ▼
┌─────────────────────────────────────────────┐
│  Audio Recording (sounddevice)              │
│  (built-in mic to avoid BT quality issues)  │
└─────────────────┬───────────────────────────┘
                  │ "over" or 2s silence
                  ▼
┌─────────────────────────────────────────────┐
│  Whisper Transcription                      │
│  (local whisper.cpp on port 2022)           │
└─────────────────┬───────────────────────────┘
                  │ transcribed text
                  ▼
┌─────────────────────────────────────────────┐
│  Claude Code CLI (new iTerm tab)            │
│  (executes command, responds via voice)     │
└─────────────────────────────────────────────┘
```

## Troubleshooting

### Wake word not detected
- Check microphone permissions: System Settings > Privacy & Security > Microphone
- Ensure Terminal has microphone access
- Verify the `.ppn` model file path is correct in config
- Ensure your mic is not muted

### Whisper transcription fails
- Verify Whisper service: `curl http://localhost:2022/health`
- Start Whisper: `voicemode service start whisper`

### Claude doesn't respond via voice
- Ensure Kokoro TTS is running: `voicemode service start kokoro`
- Check VoiceMode MCP is configured in Claude Code settings

### Audio quality degraded (Bluetooth headphones)
- This happens when macOS switches your headphones to HFP mode
- Solution: Set `input_device: "MacBook Pro Microphone"` in config.yaml

### VoiceMode keeps talking after closing iTerm
- The TTS process runs independently
- Stop it with: `pkill -f "kokoro\|tts"` (or add as alias: `alias shutup='pkill -f "kokoro\|tts"'`)

## Known Limitations

- **Requires terminal window**: Currently runs in foreground via `./manage.sh run`. Background service (`./manage.sh start`) exists but has macOS microphone permission issues with launchd.
- **macOS only**: Uses Picovoice wake word models compiled for macOS arm64.

## Security

- Access keys are never committed to git (`.gitignore`)
- Use environment variables or gitignored config.yaml
- Never share your Picovoice access key

## License

MIT License - See [LICENSE](LICENSE) file

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

Built with [Picovoice Porcupine](https://picovoice.ai/platform/porcupine/), [Whisper.cpp](https://github.com/ggerganov/whisper.cpp), and [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
