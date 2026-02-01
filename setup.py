"""
py2app build script for Hey Claude

Build with: python3 setup.py py2app
"""

from setuptools import setup

APP = ['claude_voice.py']
DATA_FILES = [
    ('', ['config.yaml.example']),
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'hey-claude.icns',
    'packages': ['pvporcupine', 'sounddevice', 'numpy', 'requests', 'yaml', '_sounddevice_data'],
    'includes': ['_cffi_backend'],
    'frameworks': ['/opt/homebrew/lib/libportaudio.dylib'],
    'strip': False,  # Don't strip binaries
    'semi_standalone': False,
    'site_packages': True,
    'plist': {
        'CFBundleIconFile': 'hey-claude',
        'CFBundleIdentifier': 'com.user.hey-claude',
        'CFBundleName': 'Hey Claude',
        'CFBundleDisplayName': 'Hey Claude',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # Run as background app (no dock icon)
        'NSMicrophoneUsageDescription': 'Hey Claude needs microphone access to listen for wake word and voice commands.',
        'NSHighResolutionCapable': True,
    },
}

setup(
    name='Hey Claude',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
