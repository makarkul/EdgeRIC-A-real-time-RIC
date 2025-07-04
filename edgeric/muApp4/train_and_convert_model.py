#!/usr/bin/env python3
"""
Train and Convert muApp4 Model for muApp1
=========================================

This script provides an end-to-end workflow to:
1. Train a latency-optimized model using muApp4
2. Convert the trained model for use in muApp1
3. Validate the converted model

Usage:
    python train_and_convert_model.py [--quick-train] [--iterations 50]
"""

import argparse
import os
import sys
import subprocess
import time
from pathlib import Path

def train_muapp4_model(iterations=50, quick_train=False):
    """Train a muApp4 latency optimization model"""
    
    print("=" * 60)
    print("STEP 1: Training muApp4 Latency Optimization Model")
    print("=" * 60)
    
    # Get the muApp4 directory
    muapp4_dir = Path(__file__).parent
    
    # Prepare training command
    if quick_train:
        # Quick training for testing
        train_cmd = [
            "python", "muApp4_train_RL_latency_scheduling.py",
            "--num-epochs", "5",
            "--save-model-interval", "2",
            "--num-processes", "1",
            "--log-interval", "1",
            "--seed", "42"
        ]
        print("🚀 Starting quick training (5 epochs)...")
    else:
        # Full training
        train_cmd = [
            "python", "muApp4_train_RL_latency_scheduling.py",
            "--num-epochs", str(iterations),
            "--save-model-interval", "10",
            "--num-processes", "1",
            "--log-interval", "5",
            "--seed", "42"
        ]
        print(f"🚀 Starting full training ({iterations} epochs)...")
    
    # Change to muApp4 directory and run training
    original_dir = os.getcwd()
    try:
        os.chdir(muapp4_dir)
        
        # Run training
        start_time = time.time()
        result = subprocess.run(train_cmd, capture_output=True, text=True)
        end_time = time.time()
        
        if result.returncode == 0:
            print(f"✓ Training completed successfully in {end_time - start_time:.1f} seconds")
            
            # Find the best model
            outputs_dir = muapp4_dir / "outputs"
            if outputs_dir.exists():
                # Find the most recent run directory
                run_dirs = [d for d in outputs_dir.iterdir() if d.is_dir()]
                if run_dirs:
                    latest_run = max(run_dirs, key=lambda d: d.stat().st_mtime)
                    best_model = latest_run / "model_best.pt"
                    if best_model.exists():
                        print(f"✓ Best model saved at: {best_model}")
                        return str(best_model)
                    else:
                        print("⚠ Warning: model_best.pt not found, looking for checkpoint...")
                        # Look for checkpoint models
                        checkpoint_files = list(latest_run.glob("model_latency_*.pt"))
                        if checkpoint_files:
                            latest_checkpoint = max(checkpoint_files, key=lambda f: f.stat().st_mtime)
                            print(f"✓ Using checkpoint model: {latest_checkpoint}")
                            return str(latest_checkpoint)
            
            print("⚠ Warning: Could not find trained model file")
            return None
            
        else:
            print("✗ Training failed:")
            print(result.stderr)
            return None
            
    finally:
        os.chdir(original_dir)


def convert_model_for_muapp1(source_model_path, output_dir=None):
    """Convert the trained muApp4 model for muApp1"""
    
    print("=" * 60)
    print("STEP 2: Converting Model for muApp1")
    print("=" * 60)
    
    if not source_model_path or not os.path.exists(source_model_path):
        print("✗ Error: Source model not found")
        return False
    
    # Default output directory
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "muApp1" / "rl_model"
    
    # Run conversion script
    conversion_cmd = [
        "python", "convert_muapp4_to_muapp1.py",
        "--source-model", source_model_path,
        "--output-dir", str(output_dir),
        "--model-name", "model_latency_optimized.pt"
    ]
    
    print(f"🔄 Converting model: {source_model_path}")
    print(f"📁 Output directory: {output_dir}")
    
    muapp4_dir = Path(__file__).parent
    original_dir = os.getcwd()
    
    try:
        os.chdir(muapp4_dir)
        result = subprocess.run(conversion_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Model conversion completed successfully")
            print(result.stdout)
            
            converted_model = output_dir / "model_latency_optimized.pt"
            if converted_model.exists():
                print(f"✓ Converted model available at: {converted_model}")
                return str(converted_model)
            else:
                print("⚠ Warning: Converted model file not found")
                return None
        else:
            print("✗ Model conversion failed:")
            print(result.stderr)
            return None
            
    finally:
        os.chdir(original_dir)


def validate_converted_model(converted_model_path):
    """Validate the converted model can be loaded by muApp1"""
    
    print("=" * 60)
    print("STEP 3: Validating Converted Model")
    print("=" * 60)
    
    if not converted_model_path or not os.path.exists(converted_model_path):
        print("✗ Error: Converted model not found")
        return False
    
    try:
        import torch
        
        # Try to load the converted model
        print(f"🔍 Loading converted model: {converted_model_path}")
        model = torch.load(converted_model_path, map_location=torch.device('cpu'))
        
        # Test with dummy input (muApp1 format)
        dummy_input = torch.randn(1, 6)  # 2 UEs * 3 features (BL, CQI, MB)
        
        print("🧪 Testing model with dummy input...")
        with torch.no_grad():
            action = model.select_action(dummy_input)
            print(f"✓ Model output shape: {action.shape}")
            print(f"✓ Model output: {action}")
        
        print("✓ Model validation successful!")
        return True
        
    except Exception as e:
        print(f"✗ Model validation failed: {e}")
        return False


def update_muapp1_config(converted_model_path):
    """Update muApp1 configuration to use the new model"""
    
    print("=" * 60)
    print("STEP 4: Updating muApp1 Configuration")
    print("=" * 60)
    
    muapp1_dir = Path(__file__).parent.parent / "muApp1"
    muapp1_script = muapp1_dir / "muApp1_run_DL_scheduling.py"
    
    if not muapp1_script.exists():
        print("⚠ Warning: muApp1 script not found. Manual configuration needed.")
        return False
    
    # Read current script
    with open(muapp1_script, 'r') as f:
        content = f.read()
    
    # Add latency-optimized model to the mapping
    if "Latency Optimized Model" not in content:
        # Find the rl_model_mapping section
        mapping_start = content.find("rl_model_mapping = {")
        if mapping_start != -1:
            mapping_end = content.find("}", mapping_start)
            if mapping_end != -1:
                # Insert the new model mapping
                new_mapping = '    "Latency Optimized Model": "./rl_model/model_latency_optimized.pt",\n'
                insert_pos = mapping_end
                # Find the last entry to add comma if needed
                last_entry = content.rfind('"', mapping_start, mapping_end)
                if last_entry != -1:
                    content = content[:insert_pos] + new_mapping + content[insert_pos:]
                    
                    # Write back to file
                    with open(muapp1_script, 'w') as f:
                        f.write(content)
                    
                    print("✓ Updated muApp1 configuration with latency-optimized model")
                    return True
    
    print("⚠ muApp1 configuration may need manual update")
    return False


def main():
    parser = argparse.ArgumentParser(description="Train and convert muApp4 model for muApp1")
    parser.add_argument("--quick-train", action="store_true", 
                       help="Quick training mode (5 epochs)")
    parser.add_argument("--iterations", type=int, default=50,
                       help="Number of training iterations for full training")
    parser.add_argument("--skip-training", action="store_true",
                       help="Skip training and use existing model")
    parser.add_argument("--source-model", 
                       help="Path to existing model to convert (when skipping training)")
    parser.add_argument("--output-dir", 
                       help="Output directory for converted model")
    
    args = parser.parse_args()
    
    print("🎯 muApp4 → muApp1 Model Generation Pipeline")
    print("=" * 60)
    print("This script will:")
    print("1. Train a latency-optimized model using muApp4")
    print("2. Convert the model for use in muApp1")
    print("3. Validate the converted model")
    print("4. Update muApp1 configuration")
    print()
    
    # Step 1: Train the model (or use existing)
    if args.skip_training:
        if args.source_model:
            source_model_path = args.source_model
            print(f"📁 Using existing model: {source_model_path}")
        else:
            print("✗ Error: --source-model required when --skip-training is used")
            return 1
    else:
        source_model_path = train_muapp4_model(args.iterations, args.quick_train)
        if not source_model_path:
            print("✗ Training failed. Exiting.")
            return 1
    
    # Step 2: Convert the model
    converted_model_path = convert_model_for_muapp1(source_model_path, args.output_dir)
    if not converted_model_path:
        print("✗ Model conversion failed. Exiting.")
        return 1
    
    # Step 3: Validate the model
    if not validate_converted_model(converted_model_path):
        print("✗ Model validation failed. Exiting.")
        return 1
    
    # Step 4: Update muApp1 configuration
    update_muapp1_config(converted_model_path)
    
    print("=" * 60)
    print("🎉 SUCCESS: Model generation and conversion completed!")
    print("=" * 60)
    print(f"📁 Trained model: {source_model_path}")
    print(f"📁 Converted model: {converted_model_path}")
    print()
    print("Next steps:")
    print("1. The converted model is ready for use in muApp1")
    print("2. Update muApp1's Redis configuration to use 'Latency Optimized Model'")
    print("3. Run muApp1 with the new latency-optimized scheduler")
    print()
    print("To use the model in muApp1:")
    print("redis-cli SET selected_model 'Latency Optimized Model'")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
