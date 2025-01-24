import toml


with open("settings/data.toml", 'r') as f:
    config = toml.load(f)

# Function to fetch a value from the configuration
def get(key: str, value: str):
    return config[key][value]

# Example usage
screen_size = (get("display", "screen_x"), get("display", "screen_y"))
max_fps = get("quality", "max_fps")
