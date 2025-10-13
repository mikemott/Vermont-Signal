#!/bin/bash
# Clean API keys from shell history
# Run this after rotating keys

echo "🧹 Cleaning API keys from shell history..."

# Backup history first
cp ~/.bash_history ~/.bash_history.backup
cp ~/.zsh_history ~/.zsh_history.backup 2>/dev/null

# Remove lines containing old keys
sed -i.bak '/sk-ant-api03-Xi9NXgulzf3tUm/d' ~/.bash_history 2>/dev/null
sed -i.bak '/AIzaSyAqWQOvj5u-_4GJyqpu1DVfBdfnPvfXqm4/d' ~/.bash_history 2>/dev/null
sed -i.bak '/sk-proj-GZU1G4HzUn85gBQD/d' ~/.bash_history 2>/dev/null

sed -i.bak '/sk-ant-api03-Xi9NXgulzf3tUm/d' ~/.zsh_history 2>/dev/null
sed -i.bak '/AIzaSyAqWQOvj5u-_4GJyqpu1DVfBdfnPvfXqm4/d' ~/.zsh_history 2>/dev/null
sed -i.bak '/sk-proj-GZU1G4HzUn85gBQD/d' ~/.zsh_history 2>/dev/null

# Clear in-memory history
history -c 2>/dev/null

echo "✅ Shell history cleaned"
echo "📦 Backup saved to ~/.bash_history.backup"
echo ""
echo "⚠️  IMPORTANT: The old keys are now removed from history,"
echo "   but they may still exist in:"
echo "   - Deployment platform logs (Fly.io, Railway, Render)"
echo "   - Any terminal session recordings"
echo "   - Cloud provider audit logs"
echo ""
echo "   That's why we ROTATED the keys - the old ones are now invalid."
