name: Build sur AlmaLinux local

on:
  push:
    branches: [ "main" ]

jobs:
  build:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: |
          sudo dnf install -y python3-pip python3-tkinter
          pip3 install --user selenium pillow img2pdf pyinstaller
          python3 -m PyInstaller --onefile --noconsole main.py
      - name: Save
        uses: actions/upload-artifact@v4
        with:
          name: SushiScan_Alma_Fix
          path: dist/main
