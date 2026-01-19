#!/bin/bash
# Script to add Python pip to PATH

# Add Python user bin directory to PATH in .zshrc
if ! grep -q "Library/Python/3.9/bin" ~/.zshrc 2>/dev/null; then
    echo "" >> ~/.zshrc
    echo "# Add Python user bin directory to PATH" >> ~/.zshrc
    echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
    echo "✓ Added Python bin directory to ~/.zshrc"
else
    echo "✓ Python bin directory already in ~/.zshrc"
fi

# Reload shell configuration
echo "✓ Please run: source ~/.zshrc"
echo "✓ Or open a new terminal window"
