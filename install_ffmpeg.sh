#!/bin/bash

# FFmpeg installation script for Hunyuan-GameCraft
# This script helps install FFmpeg on different platforms

echo "=== FFmpeg Installation Script for Hunyuan-GameCraft ==="
echo ""

# Detect operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        echo "Detected Ubuntu/Debian system"
        echo "Installing FFmpeg..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v yum &> /dev/null; then
        echo "Detected CentOS/RHEL system"
        echo "Installing FFmpeg..."
        sudo yum install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        echo "Detected Fedora system"
        echo "Installing FFmpeg..."
        sudo dnf install -y ffmpeg
    else
        echo "Unsupported Linux distribution. Please install FFmpeg manually:"
        echo "  Visit: https://ffmpeg.org/download.html"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected macOS system"
    if command -v brew &> /dev/null; then
        echo "Installing FFmpeg using Homebrew..."
        brew install ffmpeg
    else
        echo "Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo "Now installing FFmpeg..."
        brew install ffmpeg
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows (Git Bash, Cygwin)
    echo "Detected Windows system"
    echo "Please install FFmpeg manually:"
    echo "  1. Download from: https://ffmpeg.org/download.html"
    echo "  2. Extract to a folder (e.g., C:\\ffmpeg)"
    echo "  3. Add C:\\ffmpeg\\bin to your PATH environment variable"
    echo ""
    echo "Or use Chocolatey: choco install ffmpeg"
    echo "Or use Scoop: scoop install ffmpeg"
else
    echo "Unsupported operating system: $OSTYPE"
    echo "Please install FFmpeg manually from: https://ffmpeg.org/download.html"
fi

echo ""
echo "=== Installation Complete ==="
echo ""

# Verify installation
if command -v ffmpeg &> /dev/null; then
    echo "✓ FFmpeg is now available!"
    echo "Version: $(ffmpeg -version | head -n1)"
    echo ""
    echo "You can now run the icon generation script with better video compatibility."
else
    echo "✗ FFmpeg installation may have failed."
    echo "Please check the error messages above and try again."
fi
