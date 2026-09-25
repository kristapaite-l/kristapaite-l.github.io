import kagglehub
kagglehub.login()
# Define your target path
target_path = r"C:\Users\Laura\Github\kristapaite-l.github.io\kristapaite-l.github.io\data\machine_learning\titanic"

# Download files directly into the target directory
path = kagglehub.competition_download('titanic', output_dir=target_path)

print("Path to competition files:", path)