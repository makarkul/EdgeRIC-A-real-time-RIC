# EdgeRIC muApps Comparison

## Overview

EdgeRIC includes five different muApps, each designed for specific use cases and optimization goals:

| muApp | Purpose | State Space | Optimization | Deployment | Training Required |
|-------|---------|-------------|--------------|------------|------------------|
| **muApp1** | Real-time inference | [BL, CQI, MB] | Pre-trained model | Load model | ✅ (offline) |
| **muApp2** | RL training | [BL, CQI, MB] | Throughput | Train model | ✅ (online) |
| **muApp3** | Baselines | [BL, CQI, MB] | Various algorithms | Direct | ❌ |
| **muApp4** | Latency RL training | [BL, CQI, LAT, MB, LP] | Latency (training) | Train → Convert | ✅ (online) |
| **muApp5** | Real-time latency | [BL, CQI, MB] | Latency (real-time) | Direct | ❌ |

## Detailed Comparison

### muApp1: Real-time Inference Engine
- **Best for**: Production deployment with pre-trained models
- **Pros**: Fast inference, proven performance, Redis integration
- **Cons**: Requires trained models, static behavior
- **Use case**: When you have good models and need consistent performance

### muApp2: Throughput Optimization Trainer
- **Best for**: Training models that maximize throughput
- **Pros**: Proven RL training pipeline, good baseline performance
- **Cons**: Focuses on throughput, not latency
- **Use case**: When throughput is the primary objective

### muApp3: Baseline Algorithms
- **Best for**: Benchmarking and comparison
- **Pros**: Simple, interpretable, various algorithms
- **Cons**: Not optimized for specific objectives
- **Use case**: Performance comparison and baseline establishment

### muApp4: Latency-Aware Training
- **Best for**: Training latency-optimized models
- **Pros**: Sophisticated latency rewards, advanced state space
- **Cons**: Complex training, requires model conversion for deployment
- **Use case**: When you need the best possible latency optimization and can invest in training

### muApp5: Real-time Latency Optimization ⭐
- **Best for**: Immediate latency optimization deployment
- **Pros**: No training needed, real-time adaptation, interpretable
- **Cons**: Algorithmic (not learned), may not be optimal for all scenarios
- **Use case**: When you need latency optimization NOW without training overhead

## Usage Recommendations

### For Latency-Sensitive Applications:

1. **Quick deployment**: Use **muApp5** → Immediate latency optimization
2. **Best performance**: Use **muApp4** → Train optimal models → Deploy via muApp1
3. **Baseline comparison**: Use **muApp3** → Establish performance baselines

### For Throughput-Focused Applications:

1. **Proven solution**: Use **muApp2** → Train models → Deploy via muApp1
2. **Quick deployment**: Use **muApp3** with Max-Weight or Proportional Fair

### For Research and Development:

1. **Compare all approaches**: Run muApp3 (baselines) vs muApp5 (latency) vs muApp1 (trained models)
2. **Develop new algorithms**: Extend muApp5 with new scheduling logic
3. **Advanced training**: Use muApp4 for cutting-edge latency optimization

## Performance Expectations

### Latency Performance (Lower is Better)
```
muApp5 (Aggressive) < muApp4 (Trained) < muApp1 (Trained) < muApp3 (Baselines) < muApp2 (Throughput)
```

### Throughput Performance (Higher is Better)  
```
muApp2 (Throughput) > muApp1 (Trained) > muApp3 (Baselines) > muApp4 (Trained) > muApp5 (Aggressive)
```

### Deployment Speed (Faster is Better)
```
muApp5 (Immediate) > muApp3 (Immediate) > muApp1 (Load model) > muApp2 (Train) > muApp4 (Train + Convert)
```

## Integration Matrix

| Feature | muApp1 | muApp2 | muApp3 | muApp4 | muApp5 |
|---------|---------|---------|---------|---------|---------|
| **Redis Integration** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Web Dashboard** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Real-time Metrics** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Logging** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Hot-swapping** | ✅ | ❌ | ✅ | ❌ | ✅ |
| **Configuration** | Redis | YAML | Code | YAML | JSON/CLI |

## File Structure

```
edgeric/
├── muApp1/                 # Real-time inference
│   ├── muApp1_run_DL_scheduling.py
│   └── rl_model/          # Pre-trained models
├── muApp2/                 # Throughput training
│   ├── muApp2_train_RL_DL_scheduling.py
│   └── outputs/           # Training outputs
├── muApp3/                 # Baseline algorithms
│   └── muApp3_algorithms.py
├── muApp4/                 # Latency training
│   ├── muApp4_train_RL_latency_scheduling.py
│   ├── convert_muapp4_to_muapp1.py
│   └── outputs/           # Training outputs
└── muApp5/                 # Real-time latency
    ├── muApp5_latency_scheduler.py
    ├── muApp5_config.json
    └── analyze_muapp5_logs.py
```

## Quick Start Guide

### Option 1: Need Latency Optimization NOW
```bash
cd edgeric/muApp5
python muApp5_latency_scheduler.py --target-latency 5.0 --episodes 10000
```

### Option 2: Want Best Possible Performance (Long-term)
```bash
# Step 1: Train the model
cd edgeric/muApp4  
python muApp4_train_RL_latency_scheduling.py --num-epochs 100

# Step 2: Convert for deployment
python convert_muapp4_to_muapp1.py --source-model outputs/.../model_best.pt --output-dir ../muApp1/rl_model/

# Step 3: Deploy
cd ../muApp1
redis-cli SET selected_model "Latency Optimized Model"
python muApp1_run_DL_scheduling.py
```

### Option 3: Compare Different Approaches
```bash
# Test muApp5 (real-time latency)
cd muApp5 && python muApp5_latency_scheduler.py --episodes 1000 &

# Test muApp1 (trained model)  
cd muApp1 && python muApp1_run_DL_scheduling.py &

# Compare results via web dashboard at http://localhost:8050
```

## Summary

- **muApp5** is the **recommended starting point** for latency optimization
- **muApp4** is for **advanced users** who need maximum performance
- **muApp1** is for **production deployment** with proven models
- **muApp2** is for **throughput-focused** applications
- **muApp3** is for **benchmarking** and **research**

Choose based on your immediate needs, available time, and performance requirements!
