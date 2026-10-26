#!/usr/bin/env python3
"""
Compiles protocol buffer definitions (.proto) into Python gRPC code.
Also handles fixing relative imports for modular package usage.
"""
import os
import sys
import re
from grpc_tools import protoc

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO_DIR = os.path.join(PROJECT_ROOT, "proto")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "backend", "grpc_server", "generated")

def generate():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Ensure __init__.py exists in output dir
    init_file = os.path.join(OUTPUT_DIR, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Generated gRPC package\n")

    proto_files = [f for f in os.listdir(PROTO_DIR) if f.endswith(".proto")]
    if not proto_files:
        print("No .proto files found in", PROTO_DIR)
        return

    for proto_file in proto_files:
        proto_path = os.path.join(PROTO_DIR, proto_file)
        print(f"Compiling {proto_file}...")
        
        cmd = [
            "grpc_tools.protoc",
            f"-I{PROTO_DIR}",
            f"--python_out={OUTPUT_DIR}",
            f"--grpc_python_out={OUTPUT_DIR}",
            proto_path,
        ]
        
        ret = protoc.main(cmd)
        if ret != 0:
            print(f"Error compiling {proto_file}, return code: {ret}")
            sys.exit(ret)

    # Post-process generated *_grpc.py files to support relative imports inside packages
    for fname in os.listdir(OUTPUT_DIR):
        if fname.endswith("_grpc.py"):
            fpath = os.path.join(OUTPUT_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Replace 'import xxx_pb2 as' with 'from . import xxx_pb2 as' or try-except
            pattern = re.compile(r"^import (\w+_pb2) as (\w+)", re.MULTILINE)
            replacement = (
                r"try:\n"
                r"    from . import \1 as \2\n"
                r"except (ImportError, ValueError):\n"
                r"    import \1 as \2"
            )
            new_content = pattern.sub(replacement, content)
            
            if new_content != content:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Patched imports in {fname} for package compatibility.")

    print(f"Proto generation complete. Stubs saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    generate()
