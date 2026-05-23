# Shared Hytale path configuration for all example projects (bash).
# Sourced by each example's deploy.sh. Mirrors hytale-paths.bat (Windows) and
# hytale-paths.gradle (build), including Linux Flatpak launcher support.

if [ -n "${APPDATA:-}" ]; then
    HYTALE_ROOT="$APPDATA/Hytale"                                          # Windows / explicit override
elif [ -d "$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale" ]; then
    HYTALE_ROOT="$HOME/.var/app/com.hypixel.HytaleLauncher/data/Hytale"    # Linux Flatpak launcher
else
    HYTALE_ROOT="$HOME/AppData/Roaming/Hytale"                             # original fallback
fi
HYTALE_MODS_DIR="$HYTALE_ROOT/UserData/Mods"
