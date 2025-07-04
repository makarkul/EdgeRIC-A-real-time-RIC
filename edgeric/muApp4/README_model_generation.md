# muApp4 → muApp1 Model Generation Guide

This guide explains how to generate a latency-optimized model from muApp4 and use it in muApp1 for real-time scheduling.

## Overview

The muApp4 → muApp1 workflow allows you to:
1. **Train** a latency-optimized model using muApp4's advanced RL environment
2. **Convert** the model format for compatibility with muApp1
3. **Deploy** the model in muApp1 for real-time scheduling

## Quick Start

### Option 1: Complete Pipeline (Recommended)
```bash
# Train and convert model in one step
cd edgeric/muApp4
python train_and_convert_model.py --quick-train

# For full training (more iterations)
python train_and_convert_model.py --iterations 100
```

### Option 2: Manual Steps

#### Step 1: Train muApp4 Model
```bash
cd edgeric/muApp4
python muApp4_train_RL_latency_scheduling.py --num-epochs 50 --seed 42
```

#### Step 2: Convert for muApp1
```bash
python convert_muapp4_to_muapp1.py \
    --source-model outputs/YYYY-MM-DD_HH-MM-SS/model_best.pt \
    --output-dir ../muApp1/rl_model/ \
    --model-name model_latency_optimized.pt
```

#### Step 3: Use in muApp1
```bash
# Set Redis configuration
redis-cli SET selected_model "Latency Optimized Model"

# Run muApp1 with latency-optimized scheduling
cd ../muApp1
python muApp1_run_DL_scheduling.py
```

## Understanding the Model Conversion

### State Space Transformation

**muApp1 Input Format:**
```
[BL1, CQI1, MB1, BL2, CQI2, MB2, ...]
```

**muApp4 Input Format (Augmented):**
```
[BL1, CQI1, LAT1, MB1, LP1, BL2, CQI2, LAT2, MB2, LP2, ...]
```

Where:
- `BL`: Backlog length
- `CQI`: Channel Quality Indicator
- `MB`: Maximum Buffer size
- `LAT`: Latency (added by muApp4)
- `LP`: Latency Priority (CQI × Latency)

### Model Adaptation

The conversion script creates a wrapper that:
1. **Transforms input**: Adds default latency values when muApp1 provides standard state
2. **Maintains compatibility**: Preserves the original model's learned parameters
3. **Optimizes for latency**: Leverages muApp4's latency-aware training

## Configuration Options

### Training Parameters
```python
# In muApp4/conf/edge_ric_latency.yaml
latency_config:
  target_latency: 10000        # Target latency in microseconds (10ms)
  latency_penalty_weight: 1.0  # Weight for latency penalty
  throughput_weight: 0.1       # Weight for throughput maintenance
  max_latency_penalty: 1000    # Maximum penalty for high latency
```

### muApp1 Integration
```python
# In muApp1/muApp1_run_DL_scheduling.py
rl_model_mapping = {
    "Initial Model": "./rl_model/initial_model",
    "Half Trained Model": "./rl_model/half_trained_model",
    "Fully Trained Model": "./rl_model/fully_trained_model",
    "Latency Optimized Model": "./rl_model/model_latency_optimized.pt"  # New!
}
```

## Performance Expectations

### Latency Improvements
- **Target**: < 10ms average latency
- **Optimization**: Prioritizes low-latency UEs
- **Balance**: Maintains reasonable throughput

### Throughput Trade-offs
- **Primary Goal**: Minimize latency
- **Secondary Goal**: Maintain QoS through throughput weighting
- **Adaptive**: Adjusts based on network conditions

## Monitoring and Validation

### Model Validation
```bash
# Check model compatibility
python -c "
import torch
model = torch.load('muApp1/rl_model/model_latency_optimized.pt')
dummy_input = torch.randn(1, 6)  # 2 UEs × 3 features
output = model.select_action(dummy_input)
print('Model validation successful:', output.shape)
"
```

### Real-time Monitoring
- **Web Dashboard**: Monitor latency metrics in real-time
- **Redis Logs**: Track scheduling decisions
- **Performance Metrics**: Compare against baseline algorithms

## Troubleshooting

### Common Issues

1. **Model Loading Errors**
   ```bash
   # Check model file exists
   ls -la muApp1/rl_model/model_latency_optimized.pt
   
   # Verify model format
   python -c "import torch; print(torch.load('path/to/model.pt'))"
   ```

2. **State Space Mismatch**
   - Ensure muApp4 training used correct UE count
   - Check augmented vs non-augmented state space setting

3. **Performance Issues**
   - Adjust latency penalty weights in config
   - Retrain with different reward parameters
   - Monitor throughput vs latency trade-offs

### Debug Mode
```bash
# Run with debug output
python muApp1_run_DL_scheduling.py --debug

# Check Redis configuration
redis-cli GET selected_model
redis-cli GET selected_algorithm
```

## Advanced Usage

### Custom Training
```bash
# Train with custom parameters
python muApp4_train_RL_latency_scheduling.py \
    --num-epochs 100 \
    --save-model-interval 10 \
    --target-latency 5000 \
    --latency-weight 2.0
```

### Batch Conversion
```bash
# Convert multiple models
for model in outputs/*/model_best.pt; do
    python convert_muapp4_to_muapp1.py \
        --source-model "$model" \
        --output-dir ../muApp1/rl_model/ \
        --model-name "model_$(basename $(dirname $model)).pt"
done
```

### A/B Testing
```bash
# Compare different models
redis-cli SET selected_model "Latency Optimized Model"
# Run tests, collect metrics
redis-cli SET selected_model "Fully Trained Model"
# Run tests, compare results
```

## Integration with EdgeRIC

### Container Deployment
The latency-optimized model integrates seamlessly with EdgeRIC's container environment:

```bash
# Start EdgeRIC with latency optimization
./start_edgeric_with_screen.sh bridge test

# In Window 1 (muApp1): Model will auto-load if configured
# In Window 11 (Dashboard): Monitor latency metrics
```

### Real-time Adaptation
The model adapts to real-time conditions:
- **Dynamic Latency**: Adjusts to actual measured latency
- **CQI-aware**: Considers channel quality for scheduling
- **Backlog-sensitive**: Balances latency and throughput

## Files Created

After running the conversion process, you'll have:

```
muApp4/
├── outputs/YYYY-MM-DD_HH-MM-SS/
│   ├── model_best.pt                    # Trained muApp4 model
│   ├── model_latency_1.pt              # Checkpoint models
│   └── best_model_info.txt             # Training info
├── convert_muapp4_to_muapp1.py         # Conversion script
└── train_and_convert_model.py          # Complete pipeline

muApp1/
└── rl_model/
    ├── model_latency_optimized.pt      # Converted model
    └── model_latency_optimized_info.txt # Conversion info
```

## Next Steps

1. **Validate Performance**: Run A/B tests comparing latency vs throughput
2. **Tune Parameters**: Adjust latency targets based on your use case
3. **Monitor Deployment**: Use the web dashboard to track real-time performance
4. **Iterate**: Retrain models with different configurations as needed

For more details, see the individual script help:
```bash
python train_and_convert_model.py --help
python convert_muapp4_to_muapp1.py --help
```
