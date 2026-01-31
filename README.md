# Hey Claude - Voice Command System

Always-on macOS voice assistant that listens for "Hey Claude" and executes commands via Claude Code.

## Features

- Always-on wake word detection ("Hey Claude") using Picovoice Porcupine
- Natural voice commands with "over" end trigger (or 2-second pause)
- Automatic Claude Code execution in new iTerm tab
- Voice responses via VoiceMode MCP (Whisper + Kokoro TTS)
- Secure access key handling (environment variables)
- macOS launchd service for auto-start on login
- Built-in mic support to avoid Bluetooth audio quality issues

## Prerequisites

- **macOS** with Apple Silicon (M1/M2/M3/M4)
- **Python 3.10+**
- **[Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)** installed and configured
- **[VoiceMode MCP](https://www.npmjs.com/package/@anthropic/voicemode-mcp)** with Whisper and Kokoro services running
- **[Picovoice](https://picovoice.ai/)** account (free tier available)
- **iTerm2** (recommended) or Terminal.app

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/hey-claude.git
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

# Re-run install to embed in launchd service
./manage.sh install
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

### 5. Start the Daemon

```bash
./manage.sh start
```

## Usage

1. Say **"Hey Claude"** to activate (you'll hear a beep)
2. Speak your command naturally
3. Say **"over"** to finish (or pause for 2 seconds)
4. Claude executes in a new iTerm tab and responds via voice

### Example Commands

- "Hey Claude, what time is it, over"
- "Hey Claude, create a Python function to sort a list, over"
- "Hey Claude, look up task 3700 in Jira, over"
- "Hey Claude, summarize this file, over"

## Management Commands

```bash
./manage.sh install   # Install dependencies & launchd service
./manage.sh start     # Start the voice daemon
./manage.sh stop      # Stop the daemon
./manage.sh restart   # Restart the daemon
./manage.sh status    # Check if running
./manage.sh logs      # View command history & logs
./manage.sh run       # Run in foreground (for testing/debugging)
./manage.sh uninstall # Remove launchd service
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

If you use Bluetooth headphones and experience degraded audio quality when the daemon is running, configure `input_device` to use your Mac's built-in microphone:

```yaml
audio:
  input_device: "MacBook Pro Microphone"  # or "Built-in Microphone"
```

This forces the daemon to use the built-in mic without changing your system default (so calls and other apps still use your headphones normally).

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
- Verify the `.ppn` model file path is correct in config
- Try running `./manage.sh run` to see debug output
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
- This uses the built-in mic without affecting your headphone audio output

### VoiceMode keeps talking after closing iTerm
- This is expected - the TTS process runs independently
- Add this alias to stop it: `alias shutup='pkill -f "kokoro\|tts"'`

## Security

- Access keys are never committed to git (`.gitignore`)
- Use environment variables for production
- The launchd service embeds the key securely when installed with env var set
- Config file with access key is gitignored

## License

MIT License - See [LICENSE](LICENSE) file

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

Built with [Picovoice Porcupine](https://picovoice.ai/platform/porcupine/), [Whisper.cpp](https://github.com/ggerganov/whisper.cpp), and [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
