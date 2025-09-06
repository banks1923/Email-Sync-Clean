import os
import re


def generate_command_reference():
    """
    Parses the Makefile to generate a markdown command reference.
    """
    # Correctly construct absolute paths from the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    makefile_path = os.path.join(script_dir, '..', 'Makefile')
    output_path = os.path.join(script_dir, '..', 'docs', 'COMMAND_REFERENCE.md')

    commands = []
    try:
        with open(makefile_path, 'r') as f:
            for line in f:
                # Regex to find targets with '##' comments
                match = re.match(r'^([a-zA-Z0-9_-]+):.*?## (.*)$', line)
                if match:
                    target = match.group(1).strip()
                    description = match.group(2).strip()
                    
                    # Format the command example
                    if 'QUERY' in description:
                        command = f'`make {target} QUERY="..."`'
                    elif 'FILE' in description:
                        command = f'`make {target} FILE="..."`'
                    else:
                        command = f'`make {target}`'
                    
                    commands.append((command, description))
    except FileNotFoundError:
        print(f"Error: Makefile not found at {makefile_path}")
        return

    try:
        with open(output_path, 'w') as f:
            f.write("# Command Reference\n\n")
            f.write("This reference is auto-generated from the `Makefile`. Do not edit it manually.\n\n")
            f.write("| Command | Description |\n")
            f.write("|---|---|")
            for command, description in commands:
                f.write(f"| {command} | {description} |\n")
    except IOError as e:
        print(f"Error writing to output file {output_path}: {e}")
        return

if __name__ == "__main__":
    generate_command_reference()
    print("Successfully generated docs/COMMAND_REFERENCE.md")