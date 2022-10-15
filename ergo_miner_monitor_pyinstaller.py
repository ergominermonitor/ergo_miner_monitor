import PyInstaller.__main__

PyInstaller.__main__.run([
    'ergo_miner_monitor.py',
    '--onefile',
    '--nowindowed',
    '-y'
])
