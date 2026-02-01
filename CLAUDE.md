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

## Quick Reference

```bash
./hey-claude.sh install     # First time setup
./hey-claude.sh run         # Test in foreground
./hey-claude.sh build-app   # Build background app
./hey-claude.sh start-app   # Run background app
./hey-claude.sh stop-app    # Stop app
./hey-claude.sh status      # Check if running
./hey-claude.sh logs        # View logs
```

---

## Key Files

| File | Purpose |
|------|---------|
| `claude_voice.py` | Main daemon - wake word, recording, transcription, Claude launching |
| `hey-claude.sh` | Management script (install, run, build-app, etc.) |
| `setup.py` | py2app build configuration |
| `config.yaml` | User config (gitignored) |
| `config.yaml.example` | Template config |
| `wake-word/hey-claude.ppn` | Picovoice wake word model (user downloads) |

---

## Installation Flow (New User)

1. Clone repo + `./hey-claude.sh install`
2. Get Picovoice account, download wake word model
3. Place model at `wake-word/hey-claude.ppn`
4. Copy and edit config.yaml with access key
5. Test with `./hey-claude.sh run`
6. Build app with `./hey-claude.sh build-app`
7. Start with `./hey-claude.sh start-app`
8. Add to Login Items for auto-start:
   - Via Settings: System Settings > General > Login Items > Add app
   - Via Terminal: `osascript -e 'tell application "System Events" to make login item at end with properties {path:"'$(pwd)'/dist/Hey Claude.app", hidden:false}'`

---

## Dependencies

- **Picovoice Porcupine** - Wake word detection (free API key required)
- **VoiceMode MCP** - Whisper STT + Kokoro TTS (https://github.com/mbailey/voicemode)
- **Claude Code CLI** - Command execution
- **iTerm2** - Terminal for Claude sessions
- **py2app** - Builds standalone macOS app

---

## Known Issues & Solutions

| Issue | Solution |
|-------|----------|
| Bluetooth audio quality degrades | Set `input_device: "MacBook Pro Microphone"` in config |
| launchd service can't access mic | Use py2app built app instead (has proper permissions) |
| VoiceMode keeps talking after close | Run `pkill -f "kokoro\|tts"` |
| App crashes on start | Check Console.app, verify config.yaml and wake-word exist |

---

## Session Log

### 2025-02-01 - Initial Development
- Created voice command system with Picovoice + Whisper + Claude Code
- Fixed f-string syntax errors, python3/pip3 compatibility
- Solved Bluetooth audio issue (use built-in mic)
- Discovered launchd mic permission issue (TCC blocks it)
- **Solution**: py2app creates proper macOS app with mic permissions
- Simplified script: renamed manage.sh to hey-claude.sh
- Simplified wake word path: `wake-word/hey-claude.ppn`
- Added `build-app` and `start-app` commands
- App runs as background process (LSUIElement=true)

### 2026-02-01 - UX Improvements
- Added configurable wake word sensitivity (default 0.8)
- Fixed audio stream conflict: close stream before recording, reopen after
- Added sound feedback (Pop.aiff) when wake word detected
- Added notification banner with custom icon using terminal-notifier
- Created custom app icon (coral microphone on dark background)
- Added icon to app bundle and notifications

---

## Future Improvements

- [ ] Research proper code signing for distribution
- [x] Add notification when wake word detected
- [x] Add voice feedback ("I heard you")
- [ ] Support multiple wake words
- [ ] Explore Homebrew formula for easier install

---

## Update Rules

**ALWAYS update this CLAUDE.md when:**
- Adding new features or fixing bugs
- Changing configuration options
- Discovering new issues or solutions
- Making architectural decisions
- Updating dependencies or build process

Keep session log current with dated entries.
