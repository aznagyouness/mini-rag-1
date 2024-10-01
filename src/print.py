import os

def print_directory_structure(root_dir, indent=""):
    for item in os.listdir(root_dir):
        path = os.path.join(root_dir, item)
        if os.path.isdir(path):
            print(f"{indent}📂 {item}/")
            print_directory_structure(path, indent + "   ")
        else:
            print(f"{indent}📄 {item}")

# Run this script in your project directory
project_root = "."
print("Project Structure:\n")
print_directory_structure(project_root)
