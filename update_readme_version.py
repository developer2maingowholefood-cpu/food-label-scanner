import re

with open('VERSION') as vf:
    version = vf.read().strip()

for readme in ['README.md', 'README.PROCESS.md']:
    try:
        with open(readme, 'r') as f:
            content = f.read()
        # Replace version in the first heading (e.g., v1.6.0 or v1.7.0)
        new_content = re.sub(r'(Food Label Scanner v)(\d+\.\d+\.\d+)', rf'\g<1>{version}', content)
        with open(readme, 'w') as f:
            f.write(new_content)
        print(f"Updated {readme} to version {version}")
    except FileNotFoundError:
        print(f"{readme} not found, skipping.") 