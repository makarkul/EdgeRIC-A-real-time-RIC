#!/usr/bin/env python3
"""
Model Conversion Script: muApp4 to muApp1
==========================================

This script converts a trained muApp4 latency-optimized model to be compatible 
with muApp1's inference format. It handles the differences in state space 
representation and ensures proper model compatibility.

Usage:
    python convert_muapp4_to_muapp1.py --source-model path/to/muapp4_model.pt --output-dir path/to/muapp1/rl_model/
"""

import argparse
import os
import sys
import torch
import numpy as np
import pickle
from pathlib import Path
from datetime import datetime

# Add the edgeric directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.mlp_policy import Policy
from models.mlp_policy_disc import DiscretePolicy


class LatencyOptimizedModel:
    """Wrapper class to adapt muApp4 latency model for muApp1 inference"""
    
    def __init__(self, policy_net, num_ues=2, augment_state=True):
        self.policy_net = policy_net
        self.num_ues = num_ues
        self.augment_state = augment_state
        
    def select_action(self, state):
        """
        Convert muApp1 state format to muApp4 format and get action
        
        muApp1 expects: [BL1, CQI1, MB1, BL2, CQI2, MB2, ...]
        muApp4 expects: [BL1, CQI1, LAT1, MB1, LP1, BL2, CQI2, LAT2, MB2, LP2, ...] (if augmented)
                   or: [BL1, CQI1, LAT1, MB1, BL2, CQI2, LAT2, MB2, ...] (if not augmented)
        """
        # Convert from muApp1 format to muApp4 format
        if len(state.shape) == 1:
            state = state.unsqueeze(0)
        
        # Extract components from muApp1 state: [BL1, CQI1, MB1, BL2, CQI2, MB2, ...]
        batch_size = state.shape[0]
        state_flat = state.view(batch_size, -1)
        
        # Assume default latency values when not available
        default_latency = 10000.0  # 10ms in microseconds
        
        if self.augment_state:
            # Create augmented state: [BL1, CQI1, LAT1, MB1, LP1, BL2, CQI2, LAT2, MB2, LP2, ...]
            augmented_state = torch.zeros(batch_size, self.num_ues * 5, device=state.device)
            
            for ue in range(self.num_ues):
                # Extract BL, CQI, MB from muApp1 state
                bl = state_flat[:, ue * 3]
                cqi = state_flat[:, ue * 3 + 1] 
                mb = state_flat[:, ue * 3 + 2]
                
                # Add latency and latency priority
                latency = torch.full_like(bl, default_latency)
                latency_priority = cqi * latency
                
                # Fill augmented state
                augmented_state[:, ue * 5] = bl
                augmented_state[:, ue * 5 + 1] = cqi
                augmented_state[:, ue * 5 + 2] = latency
                augmented_state[:, ue * 5 + 3] = mb
                augmented_state[:, ue * 5 + 4] = latency_priority
        else:
            # Create non-augmented state: [BL1, CQI1, LAT1, MB1, BL2, CQI2, LAT2, MB2, ...]
            augmented_state = torch.zeros(batch_size, self.num_ues * 4, device=state.device)
            
            for ue in range(self.num_ues):
                # Extract BL, CQI, MB from muApp1 state
                bl = state_flat[:, ue * 3]
                cqi = state_flat[:, ue * 3 + 1]
                mb = state_flat[:, ue * 3 + 2]
                
                # Add latency
                latency = torch.full_like(bl, default_latency)
                
                # Fill state
                augmented_state[:, ue * 4] = bl
                augmented_state[:, ue * 4 + 1] = cqi
                augmented_state[:, ue * 4 + 2] = latency
                augmented_state[:, ue * 4 + 3] = mb
        
        # Get action from the policy network
        with torch.no_grad():
            action = self.policy_net.select_action(augmented_state)
        
        return action


def convert_model(source_model_path, output_dir, model_name="model_latency_optimized.pt"):
    """
    Convert muApp4 model to muApp1 compatible format
    
    Args:
        source_model_path: Path to the trained muApp4 model
        output_dir: Directory to save the converted model
        model_name: Name of the output model file
    """
    # Load the source model
    print(f"Loading source model from: {source_model_path}")
    try:
        policy_net = torch.load(source_model_path, map_location=torch.device('cpu'))
        print("✓ Successfully loaded source model")
    except Exception as e:
        print(f"✗ Error loading source model: {e}")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if model uses augmented state space (try to infer from model structure)
    input_dim = None
    try:
        # Try to get model dimensions to infer state space
        if hasattr(policy_net, 'actor') and hasattr(policy_net.actor, 'fc'):
            input_dim = policy_net.actor.fc.in_features
        elif hasattr(policy_net, 'fc1'):
            input_dim = policy_net.fc1.in_features
        else:
            print("Warning: Could not determine input dimensions. Assuming augmented state space.")
            input_dim = 10  # Default for 2 UEs with augmented state
        
        # Infer parameters
        if input_dim == 10:  # 2 UEs * 5 features (augmented)
            num_ues = 2
            augment_state = True
        elif input_dim == 8:   # 2 UEs * 4 features (non-augmented)
            num_ues = 2
            augment_state = False
        else:
            print(f"Warning: Unexpected input dimension {input_dim}. Using default settings.")
            num_ues = 2
            augment_state = True
        
        print(f"✓ Detected model configuration: {num_ues} UEs, augmented_state={augment_state}")
        
    except Exception as e:
        print(f"Warning: Could not determine model configuration: {e}")
        num_ues = 2
        augment_state = True
        input_dim = None
    
    # Create the wrapper model
    wrapped_model = LatencyOptimizedModel(policy_net, num_ues, augment_state)
    
    # Save the wrapped model
    output_path = output_dir / model_name
    try:
        torch.save(wrapped_model, output_path)
        print(f"✓ Successfully saved converted model to: {output_path}")
        
        # Save model info
        info_path = output_dir / f"{model_name.replace('.pt', '_info.txt')}"
        with open(info_path, 'w') as f:
            f.write(f"Latency-Optimized Model (converted from muApp4)\n")
            f.write(f"==============================================\n")
            f.write(f"Source model: {source_model_path}\n")
            f.write(f"Number of UEs: {num_ues}\n")
            f.write(f"Augmented state space: {augment_state}\n")
            if input_dim is not None:
                f.write(f"Input dimensions: {input_dim}\n")
            else:
                f.write(f"Input dimensions: Unknown\n")
            f.write(f"Conversion date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"✓ Model info saved to: {info_path}")
        return True
        
    except Exception as e:
        print(f"✗ Error saving converted model: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Convert muApp4 latency model to muApp1 format")
    parser.add_argument("--source-model", required=True, help="Path to the trained muApp4 model")
    parser.add_argument("--output-dir", required=True, help="Directory to save the converted model")
    parser.add_argument("--model-name", default="model_latency_optimized.pt", 
                       help="Name of the output model file")
    
    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.source_model):
        print(f"✗ Error: Source model not found at {args.source_model}")
        return 1
    
    print("muApp4 to muApp1 Model Conversion")
    print("=" * 40)
    print(f"Source model: {args.source_model}")
    print(f"Output directory: {args.output_dir}")
    print(f"Output model name: {args.model_name}")
    print()
    
    # Convert the model
    success = convert_model(args.source_model, args.output_dir, args.model_name)
    
    if success:
        print("\n✓ Model conversion completed successfully!")
        print(f"\nTo use the converted model in muApp1:")
        print(f"1. Copy the model to muApp1/rl_model/")
        print(f"2. Update the model path in muApp1_run_DL_scheduling.py")
        print(f"3. The model will now use latency-optimized scheduling")
        return 0
    else:
        print("\n✗ Model conversion failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
