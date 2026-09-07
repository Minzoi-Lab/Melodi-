# 🎵 Melodi Setup Guide

This guide will help you set up **Melodi** on Windows, macOS, and Linux.

## 📋 Requirements

Melodi requires:

* 🐍 Python 3
* 🖼️ Tkinter
* 🎵 Pygame

---

## 🪟 Windows

Tkinter comes pre-installed with standard Python installations on Windows.

### Install Pygame

Open **Command Prompt** or **PowerShell** and run:

```bash
pip install pygame
```

If `pip` is not recognised, try:

```bash
python -m pip install pygame
```

or:

```bash
pip3 install pygame
```

---

## 🍎 macOS

Tkinter is generally included with official Python distributions on macOS.

### Install Pygame

Open **Terminal** and run:

```bash
pip3 install pygame
```

Alternatively:

```bash
python3 -m pip install pygame
```

---

## 🐧 Linux

On Linux distributions such as **Ubuntu, Debian, and Linux Mint**, Tkinter usually needs to be installed separately.

### Install Tkinter

Open your Terminal and run:

```bash
sudo apt update
sudo apt install python3-tk
```

### Install Pygame

Try:

```bash
pip3 install pygame
```

If your Linux distribution blocks system-wide `pip` installations because of **PEP 668**, we recommend using a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pygame
```

> **Note:** A virtual environment is recommended instead of using `--break-system-packages`, as it avoids modifying your system Python installation.

---

## ✅ Verify the Installation

To verify that Tkinter and Pygame are installed correctly, open a Python shell.

### Windows

```bash
python
```

### macOS / Linux

```bash
python3
```

Then run:

```python
import tkinter
import pygame

print("Melodi dependencies are installed!")
```

If there are no errors, everything is installed correctly! 🎉

To exit the Python shell:

```python
exit()
```

---

## 🎧 Running Melodi

Once everything is installed, navigate to the Melodi project directory and run:

### Windows

```bash
python main.py
```

### macOS / Linux

```bash
python3 main.py
```

Enjoy **Melodi**! 🎶
