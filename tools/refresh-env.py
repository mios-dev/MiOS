import json
import os
from datetime import datetime

def refresh_env():
    env_file = ".ai-environment.json"
    vscode_file = ".vscode/settings.json"
    
    if not os.path.exists(env_file):
        print(f"❌ {env_file} not found.")
        return

    with open(env_file, 'r') as f:
        env_data = json.load(f)

    # 1. Update Aesthetic Preferences from VS Code
    if os.path.exists(vscode_file):
        with open(vscode_file, 'r') as f:
            # Handle JSON with comments (VSCodium settings often have them)
            content = f.read()
            # Simple comment stripping (won't handle nested/complex cases but works for standard VSCode)
            content = "\n".join([line for line in content.splitlines() if not line.strip().startswith("//") and not line.strip().startswith("_")])
            try:
                vscode_data = json.loads(content)
                
                # Extract font info
                font_family = vscode_data.get("editor.fontFamily", env_data["aesthetic_preferences"]["fonts"]["monospace"])
                font_size = vscode_data.get("editor.fontSize", env_data["aesthetic_preferences"]["fonts"]["size"])
                
                env_data["aesthetic_preferences"]["fonts"]["monospace"] = font_family
                env_data["aesthetic_preferences"]["fonts"]["size"] = font_size
                print(f"✅ Refreshed aesthetic preferences from {vscode_file}")
            except json.JSONDecodeError as e:
                print(f"⚠️ Warning: Could not parse {vscode_file}: {e}")

    # 2. Update Timestamp/Version
    env_data["last_refresh"] = datetime.now().isoformat()
    
    with open(env_file, 'w') as f:
        json.dump(env_data, f, indent=2)
    
    print(f"✅ {env_file} updated and cloned as latest.")

if __name__ == "__main__":
    refresh_env()
