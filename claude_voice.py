#!/usr/bin/env python3
"""
Claude Voice Command System - Always-on voice assistant for Claude Code

This daemon listens for "Hey Claude" wake word, captures voice commands,
transcribes them using local Whisper, and launches Claude Code to execute them.
"""

import os
import sys
import time
import wave
import tempfile
import subprocess
import logging
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional
import threading
import queue

import yaml
import numpy as np
import sounddevice as sd
import requests

# Defer pvporcupine import to handle missing access key gracefully
pvporcupine = None

# Project root directory
PROJECT_DIR = Path(__file__).parent.resolve()


def load_config() -> dict:
    """Load configuration from config.yaml, with environment variable overrides"""
    config_path = PROJECT_DIR / "config.yaml"

    # Try config.yaml first, fall back to config.yaml.example
    if not config_path.exists():
        config_path = PROJECT_DIR / "config.yaml.example"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Override with environment variables (for security)
    if os.environ.get("PICOVOICE_ACCESS_KEY"):
        config["picovoice"]["access_key"] = os.environ["PICOVOICE_ACCESS_KEY"]

    return config


def setup_logging(config: dict) -> logging.Logger:
    """Setup logging based on configuration"""
    log_file = PROJECT_DIR / config["logging"]["log_file"]
    log_file.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, config["logging"]["level"].upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Setup logger
    logger = logging.getLogger("claude_voice")
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


class AudioRecorder:
    """Handles audio recording with silence detection"""

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.sample_rate = config["audio"]["sample_rate"]
        self.channels = config["audio"]["channels"]
        self.silence_timeout = config["command"]["silence_timeout"]
        self.max_duration = config["command"]["max_duration"]
        self.end_keyword = config["command"]["end_keyword"].lower()
        self.input_device = config["audio"].get("input_device", "default")

        # Audio buffer
        self.audio_buffer = []
        self.is_recording = False

    def record_command(self) -> Optional[str]:
        """
        Record audio until silence is detected or max duration reached.
        Returns path to temporary WAV file. Uses specific input device to avoid
        Bluetooth audio quality degradation.
        """
        self.audio_buffer = []
        self.is_recording = True

        # Calculate frames
        chunk_duration = 0.1  # 100ms chunks
        chunk_samples = int(self.sample_rate * chunk_duration)

        # Silence detection parameters
        silence_threshold = 500  # RMS threshold for silence
        silence_chunks = 0
        silence_chunks_needed = int(self.silence_timeout / chunk_duration)

        start_time = time.time()

        self.logger.info("Recording command... (say 'over' or pause to finish)")

        # Play a short beep to indicate recording started
        self._play_start_sound()

        try:
            with sd.InputStream(
                device=self.input_device,  # Use specific device, not system default
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.int16,
                blocksize=chunk_samples
            ) as stream:
                while self.is_recording:
                    # Check max duration
                    elapsed = time.time() - start_time
                    if elapsed >= self.max_duration:
                        self.logger.info(f"Max duration ({self.max_duration}s) reached")
                        break

                    # Read audio chunk
                    chunk, _ = stream.read(chunk_samples)
                    self.audio_buffer.append(chunk.copy())

                    # Calculate RMS for silence detection
                    rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))

                    if rms < silence_threshold:
                        silence_chunks += 1
                        if silence_chunks >= silence_chunks_needed:
                            self.logger.info(f"Silence detected after {elapsed:.1f}s")
                            break
                    else:
                        silence_chunks = 0

        except sd.PortAudioError as e:
            self.logger.error(f"Audio device error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Recording error: {e}")
            return None

        self.is_recording = False

        if not self.audio_buffer:
            return None

        return self._save_to_wav()

    def _save_to_wav(self) -> str:
        """Save recorded audio buffer to a temporary WAV file"""
        # Concatenate all chunks
        audio_data = np.concatenate(self.audio_buffer)

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
            dir=PROJECT_DIR / "logs"
        )

        # Write WAV file
        with wave.open(temp_file.name, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        self.logger.debug(f"Saved audio to {temp_file.name}")
        return temp_file.name

    def _play_start_sound(self):
        """Play a short beep to indicate recording started"""
        try:
            # Generate a short 440Hz beep
            duration = 0.1  # seconds
            t = np.linspace(0, duration, int(44100 * duration), False)
            beep = (np.sin(2 * np.pi * 440 * t) * 0.3 * 32767).astype(np.int16)
            sd.play(beep, 44100)
            sd.wait()
        except Exception as e:
            self.logger.debug(f"Could not play start sound: {e}")


class WhisperTranscriber:
    """Handles speech-to-text using local Whisper or OpenAI API"""

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.whisper_url = config["stt"]["whisper_url"]
        self.use_openai_fallback = config["stt"]["use_openai_fallback"]

    def transcribe(self, audio_path: str) -> Optional[str]:
        """Transcribe audio file to text"""
        # Try local Whisper first
        text = self._transcribe_local(audio_path)

        if text is None and self.use_openai_fallback:
            self.logger.info("Local Whisper failed, trying OpenAI API...")
            text = self._transcribe_openai(audio_path)

        return text

    def _transcribe_local(self, audio_path: str) -> Optional[str]:
        """Transcribe using local whisper.cpp server"""
        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    self.whisper_url,
                    files={"file": ("audio.wav", f, "audio/wav")},
                    data={
                        "response_format": "json",
                        "language": "en"
                    },
                    timeout=30
                )

            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "").strip()
                self.logger.debug(f"Whisper transcription: {text}")
                return text
            else:
                self.logger.error(f"Whisper API error: {response.status_code}")
                return None

        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to local Whisper server. Is it running?")
            self.logger.error("Start it with: voicemode service start whisper")
            return None
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            return None

    def _transcribe_openai(self, audio_path: str) -> Optional[str]:
        """Transcribe using OpenAI Whisper API"""
        try:
            import openai

            client = openai.OpenAI()
            with open(audio_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text"
                )
            return transcript.strip()

        except Exception as e:
            self.logger.error(f"OpenAI transcription error: {e}")
            return None


class ClaudeLauncher:
    """Handles launching Claude Code with voice commands"""

    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.working_dir = os.path.expanduser(config["claude"]["working_directory"])
        self.binary_path = config["claude"]["binary_path"]
        self.end_keyword = config["command"]["end_keyword"].lower()
        self.terminal_app = config.get("terminal", {}).get("app", "iterm")

    def launch(self, command: str) -> bool:
        """Launch Claude Code in a new iTerm/Terminal window with voice mode"""
        # Remove end keyword from command if present
        command = self._clean_command(command)

        if not command:
            self.logger.warning("Empty command after cleaning, skipping")
            return False

        self.logger.info(f"Launching Claude with command: {command}")

        # Build the prompt that instructs Claude to respond via voice
        prompt = f'''You received this voice command. Execute it and respond via voice using the VoiceMode converse tool. Speak your response naturally to the user. After responding, you can continue the conversation normally.

Voice command: "{command}"'''

        # Write prompt to temp file to avoid escaping issues
        prompt_file = PROJECT_DIR / "logs" / ".current_prompt.txt"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text(prompt)

        # Build the shell command (no -p flag for interactive mode)
        shell_cmd = f'cd "{self.working_dir}" && {self.binary_path} "$(cat "{prompt_file}")"'

        try:
            if self.terminal_app == "iterm":
                return self._launch_iterm(shell_cmd)
            else:
                return self._launch_terminal(shell_cmd)
        except Exception as e:
            self.logger.error(f"Failed to launch Claude: {e}")
            return False

    def _launch_iterm(self, shell_cmd: str) -> bool:
        """Launch in iTerm2 - new tab if window exists, otherwise new window"""
        escaped_cmd = shell_cmd.replace('"', '\\"')
        applescript = f'''
        tell application "iTerm"
            activate
            if (count of windows) > 0 then
                tell current window
                    create tab with default profile
                    tell current session
                        write text "{escaped_cmd}"
                    end tell
                end tell
            else
                create window with default profile
                tell current session of current window
                    write text "{escaped_cmd}"
                end tell
            end if
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", applescript], check=True, capture_output=True)
            self.logger.info("Claude Code launched in iTerm")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"iTerm failed, trying Terminal: {e.stderr.decode()}")
            return self._launch_terminal(shell_cmd)

    def _launch_terminal(self, shell_cmd: str) -> bool:
        """Launch in Terminal.app"""
        escaped_cmd = shell_cmd.replace('"', '\\"')
        applescript = f'''
        tell application "Terminal"
            activate
            do script "{escaped_cmd}"
        end tell
        '''
        subprocess.run(["osascript", "-e", applescript], check=True, capture_output=True)
        self.logger.info("Claude Code launched in new Terminal window")
        return True

    def _clean_command(self, command: str) -> str:
        """Remove end keyword and clean up the command"""
        # Remove "over" from the end (case-insensitive)
        words = command.split()
        if words and words[-1].lower().rstrip(".,!?") == self.end_keyword:
            words = words[:-1]

        # Also check for "over" with punctuation anywhere at the end
        cleaned = " ".join(words).strip()

        # Remove trailing punctuation that might remain
        cleaned = cleaned.rstrip(".,!?")

        return cleaned


class VoiceCommandDaemon:
    """Main daemon that ties everything together"""

    def __init__(self):
        self.config = load_config()
        self.logger = setup_logging(self.config)

        # Validate access key before importing porcupine
        access_key = self.config["picovoice"]["access_key"]
        if access_key == "YOUR_PICOVOICE_ACCESS_KEY" or not access_key:
            self.logger.error("=" * 60)
            self.logger.error("PICOVOICE ACCESS KEY NOT SET!")
            self.logger.error("1. Go to https://console.picovoice.ai/")
            self.logger.error("2. Sign up/login and get your Access Key")
            self.logger.error("3. Set it via environment variable:")
            self.logger.error("   export PICOVOICE_ACCESS_KEY='your-key-here'")
            self.logger.error("   Or create config.yaml from config.yaml.example")
            self.logger.error("=" * 60)
            sys.exit(1)

        # Import porcupine now
        global pvporcupine
        import pvporcupine as pv
        pvporcupine = pv

        self.recorder = AudioRecorder(self.config, self.logger)
        self.transcriber = WhisperTranscriber(self.config, self.logger)
        self.launcher = ClaudeLauncher(self.config, self.logger)

        # Initialize Porcupine wake word detector
        self.porcupine = None
        self._init_porcupine()

        self.running = False

    def _init_porcupine(self):
        """Initialize Porcupine wake word detector"""
        access_key = self.config["picovoice"]["access_key"]
        model_path = PROJECT_DIR / self.config["picovoice"]["wake_word_model"]

        if not model_path.exists():
            self.logger.error(f"Wake word model not found: {model_path}")
            sys.exit(1)

        try:
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[str(model_path)]
            )
            self.logger.info("Porcupine wake word detector initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Porcupine: {e}")
            self.logger.error("Check your access key in config.yaml")
            sys.exit(1)

    def run(self):
        """Main loop - listen for wake word and process commands"""
        self.running = True
        self.logger.info("=" * 50)
        self.logger.info("Claude Voice Command System started")
        self.logger.info("Say 'Hey Claude' to activate, then speak your command")
        self.logger.info("Say 'over' or pause for 2 seconds to finish")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("=" * 50)

        try:
            while self.running:
                # Open mic only for short bursts to avoid audio quality degradation
                wake_detected = self._listen_for_wake_word()
                if wake_detected:
                    self.logger.info("Wake word detected: 'Hey Claude'")
                    self._handle_command()
                    # Give audio system time to reset before listening again
                    time.sleep(0.5)
                    self.logger.info("Ready for next command. Say 'Hey Claude' to activate.")

        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            self.cleanup()

    def _listen_for_wake_word(self) -> bool:
        """Listen for wake word using sounddevice with specific input device"""
        listen_duration = 1.0  # seconds
        frame_length = self.porcupine.frame_length
        sample_rate = self.porcupine.sample_rate
        frames_needed = int(listen_duration * sample_rate / frame_length)

        # Get configured input device (use built-in mic to avoid Bluetooth quality issues)
        input_device = self.config["audio"].get("input_device", "MacBook Pro Microphone")

        try:
            with sd.InputStream(
                device=input_device,  # Use specific device, not system default
                samplerate=sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=frame_length,
                latency='low'  # Use low latency for better responsiveness
            ) as stream:
                # Flush any stale audio by reading a few frames without processing
                for _ in range(3):
                    stream.read(frame_length)

                for _ in range(frames_needed):
                    if not self.running:
                        return False

                    frame, _ = stream.read(frame_length)
                    keyword_index = self.porcupine.process(frame.flatten())

                    if keyword_index >= 0:
                        return True

        except sd.PortAudioError as e:
            self.logger.error(f"Audio device error: {e}")
            self.logger.error(f"Device '{input_device}' not found. Available devices:")
            for d in sd.query_devices():
                if d['max_input_channels'] > 0:
                    self.logger.error(f"  - {d['name']}")
            time.sleep(1)
        except Exception as e:
            self.logger.debug(f"Audio error: {e}")
            time.sleep(0.1)

        return False

    def _handle_command(self):
        """Handle a voice command after wake word detection"""
        # Record the command
        audio_path = self.recorder.record_command()

        if not audio_path:
            self.logger.warning("No audio recorded")
            return

        try:
            # Transcribe the audio
            command = self.transcriber.transcribe(audio_path)

            if not command:
                self.logger.warning("Transcription failed or empty")
                return

            self.logger.info(f"Transcribed command: {command}")

            # Log the command
            self._log_command(command)

            # Launch Claude with the command
            self.launcher.launch(command)

        finally:
            # Clean up temporary audio file
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    def _log_command(self, command: str):
        """Log command to history file"""
        history_file = PROJECT_DIR / "logs" / "command_history.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(history_file, "a") as f:
            f.write(f"[{timestamp}] {command}\n")

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.porcupine:
            self.porcupine.delete()
            self.logger.info("Porcupine resources released")


def main():
    """Entry point"""
    daemon = VoiceCommandDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
