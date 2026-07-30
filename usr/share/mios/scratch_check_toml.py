import tomllib

with open("c:/MiOS/usr/share/mios/mios.toml", "rb") as f:
    try:
        data = tomllib.load(f)
        print("TOML loaded successfully! Keys:", len(data))
    except Exception as e:
        print("TOML load error:", e)
