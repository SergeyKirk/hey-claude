# Hey Claude - Voice Command System

**Repository**: https://github.com/SergeyKirk/hey-claude
**Location**: `~/Documents/personal_projects/claude-voice-detection/`
**Status**: Working (v1.0)

---

## Project Overview

Always-on macOS voice assistant that listens for "Hey Claude" wake word and executes commands via Claude Code CLI.

### How It Works
1. Porcupine wake word detection listens for "Hey Claude"
2. Records voice command until user says "over" (or 2-second pause)
3. Whisper transcribes audio to text
4. Opens new iTerm tab and runs Claude Code with the command
5. Claude responds via VoiceMode TTS

---

## Current State

### Working Features
- Wake word detection ("Hey Claude") via Picovoice Porcupine
- Voice command recording with "over" end trigger
- Local Whisper transcription (port 2022)
- Claude Code execution in new iTerm tab
- Voice responses via Kokoro TTS (port 8880)
- Built-in mic support (avoids Bluetooth audio quality issues)
- **Background app via py2app** - runs silently with proper mic permissions

### Two Ways to Run

1. **Foreground (Terminal)**:
   ```bash
   ./manage.sh run
   ```

2. **Background App** (recommended):
   ```bash
   python3 setup.py py2app
   cp config.yaml "dist/Hey Claude.app/Contents/Resources/"
   cp -r Hey-Claude_en_mac_v4_0_0 "dist/Hey Claude.app/Contents/Resources/"
   mkdir -p "dist/Hey Claude.app/Contents/Resources/logs"
   open "dist/Hey Claude.app"
   ```

---

## Key Files

| File | Purpose |
|------|---------|
| `claude_voice.py` | Main daemon - wake word detection, recording, transcription, Claude launching |
| `manage.sh` | Service management (install, run, logs) |
| `setup.py` | py2app build configuration for standalone macOS app |
| `config.yaml` | User configuration (gitignored - contains API key) |
| `config.yaml.example` | Template configuration |
| `Hey-Claude_en_mac_v4_0_0/` | Picovoice wake word model (user must download) |

---

## Dependencies

- **Picovoice Porcupine** - Wake word detection (requires free API key)
- **VoiceMode MCP** - Whisper STT + Kokoro TTS (https://github.com/mbailey/voicemode)
- **Claude Code CLI** - Command execution
- **iTerm2** - Terminal for Claude sessions

---

## Configuration

Key settings in `config.yaml`:

```yaml
picovoice:
  access_key: "YOUR_KEY"  # From console.picovoice.ai
  wake_word_model: "Hey-Claude_en_mac_v4_0_0/Hey-Claude_en_mac_v4_0_0.ppn"

audio:
  input_device: "MacBook Pro Microphone"  # Avoids Bluetooth issues

command:
  end_keyword: "over"
  silence_timeout: 2.0
```

---

## Known Issues & Solutions

### Background Service (launchd) - NOT WORKING
- macOS TCC blocks microphone access for launchd services
- Solution: Use py2app to create proper .app bundle

### Bluetooth Audio Quality Degradation
- Cause: macOS switches to HFP mode when mic is accessed
- Solution: Set `input_device: "MacBook Pro Microphone"` in config

### VoiceMode Keeps Talking After Closing iTerm
- Expected behavior - TTS runs independently
- Fix: `pkill -f "kokoro\|tts"` or alias `shutup`

---

## Session Log

### 2025-02-01 (Initial Development)
- Created voice command system with Picovoice + Whisper + Claude Code
- Fixed f-string syntax errors, python3/pip3 compatibility
- Solved Bluetooth audio issue by using built-in mic
- Discovered launchd mic permission issue (TCC)
- **Solution**: py2app creates proper macOS app with mic permissions
- App runs as background process (LSUIElement=true, no Dock icon)
- Ready for auto-start via Login Items

---

## Future Improvements

- [ ] Research proper code signing for distribution
- [ ] Add notification when wake word detected
- [ ] Support multiple wake words
- [ ] Add voice feedback confirmation ("I heard you")
- [ ] Explore Automator/AppleScript wrapper as alternative

---

## Update Rules

**ALWAYS update this CLAUDE.md when:**
1. Adding new features or fixing bugs
2. Changing configuration options
3. Discovering new issues or solutions
4. Making architectural decisions
5. Updating dependencies or build process

Keep session log current with dated entries.
