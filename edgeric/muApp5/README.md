# muApp5: Model-based Latency-Optimized Scheduler

## Overview

muApp5 is a **model-based latency-optimized scheduler** that uses trained models from muApp4 for real-time scheduling decisions. It provides the best of both worlds: the sophistication of machine learning with the practicality of real-time deployment.

## Architecture

```
muApp4 (Training) → Trained Model → muApp5 (Inference) → EdgeRIC
```

### Training Pipeline (muApp4)
1. **Train** latency-optimized RL model with advanced reward functions
2. **Save** best model to `muApp5/muApp5_trained_model.pt`
3. **Evaluate** model performance in simulation

### Inference Pipeline (muApp5)  
1. **Load** trained model from muApp4
2. **Convert** real-time UE data to model input format
3. **Inference** using trained model for scheduling decisions
4. **Fallback** to algorithmic scheduler if model fails

## Key Features

### ✅ **Model-based Optimization**
- Uses sophisticated RL models trained specifically for latency optimization
- Learns optimal scheduling policies from training data
- Adapts to complex patterns in network behavior

### ✅ **Robust Deployment**  
- Automatic model loading from muApp4 training outputs
- Intelligent fallback to algorithmic scheduling
- Real-time latency estimation when not available in training

### ✅ **State Space Adaptation**
- Converts muApp1 format `[BL, CQI, MB]` to muApp4 format `[BL, CQI, LAT, MB, LP]`
- Estimates missing latency values using heuristics
- Maintains compatibility with existing EdgeRIC system

## Architecture

```
EdgeRIC System
      ↓
  UE Metrics: [Backlog, CQI, Tx_brate, ...]
      ↓
muApp5 Scheduler
      ↓
Latency Estimation & Priority Calculation
      ↓
Scheduling Weights: [RNTI, Weight, RNTI, Weight, ...]
      ↓
EdgeRIC Controller
```

## Quick Start

### 1. Basic Usage
```bash
cd edgeric/muApp5
python muApp5_latency_scheduler.py --episodes 10000
```

### 2. Custom Configuration
```bash
python muApp5_latency_scheduler.py \
    --target-latency 5.0 \
    --latency-weight 0.5 \
    --episodes 5000
```

### 3. Using Config File
```bash
python muApp5_latency_scheduler.py \
    --config-file muApp5_config.json \
    --episodes 10000
```

## Configuration Options

### Command Line Arguments
- `--episodes`: Number of scheduling episodes (default: 10000)
- `--target-latency`: Target latency in milliseconds (default: 10.0)
- `--latency-weight`: Weight for latency in scheduling (default: 0.3)
- `--backlog-weight`: Weight for backlog in scheduling (default: 0.3)
- `--cqi-weight`: Weight for CQI in scheduling (default: 0.4)
- `--fairness-factor`: Fairness adjustment factor (default: 0.1)

### Pre-defined Policies

#### Aggressive Latency
```bash
python muApp5_latency_scheduler.py \
    --target-latency 5.0 \
    --latency-weight 0.6 \
    --backlog-weight 0.2 \
    --cqi-weight 0.2 \
    --fairness-factor 0.05
```

#### Balanced (Default)
```bash
python muApp5_latency_scheduler.py \
    --target-latency 10.0 \
    --latency-weight 0.3 \
    --backlog-weight 0.3 \
    --cqi-weight 0.4 \
    --fairness-factor 0.1
```

#### Fairness Focused
```bash
python muApp5_latency_scheduler.py \
    --target-latency 15.0 \
    --latency-weight 0.2 \
    --backlog-weight 0.3 \
    --cqi-weight 0.3 \
    --fairness-factor 0.2
```

## How It Works

### Latency Estimation Algorithm

muApp5 estimates UE latency using:

1. **Backlog Factor**: Higher backlog → Higher latency
   ```python
   backlog_factor = min(backlog / 100000, 5.0)
   ```

2. **CQI Factor**: Better channel → Lower latency
   ```python
   cqi_factor = max(1.0, 15.0 - cqi) / 15.0
   ```

3. **Service History**: Recent service patterns
   ```python
   service_factor = avg_service_interval / 1000
   ```

4. **Combined Estimate**:
   ```python
   estimated_latency = target_latency * (1 + backlog_factor * cqi_factor * service_factor)
   ```

### Priority Calculation

Scheduling priority combines:
- **Latency Urgency**: How much current latency exceeds target
- **Backlog Urgency**: Buffer utilization ratio
- **Channel Opportunity**: CQI-based transmission efficiency

```python
priority = (
    latency_weight * latency_urgency +
    backlog_weight * backlog_urgency +
    cqi_weight * channel_opportunity
)
```

### Weight Normalization

Priorities are normalized to scheduling weights:
```python
normalized_weights = priorities / sum(priorities)
# Apply fairness adjustment
final_weights = normalized_weights * (1 - fairness_factor) + fairness_factor / num_ues
```

## Integration with EdgeRIC

### Automatic Integration

muApp5 integrates seamlessly with EdgeRIC:

1. **Metrics Collection**: Uses `get_metrics_multi()` from `edgeric_messenger`
2. **Weight Transmission**: Uses `send_scheduling_weight()` to EdgeRIC
3. **Redis Integration**: Updates algorithm status in Redis
4. **Logging**: Writes detailed logs to `muApp5_latency_log.txt`

### Real-time Monitoring

Monitor muApp5 through:
- **Console Output**: Real-time episode progress and metrics
- **Log Files**: Detailed scheduling decisions and latency estimates
- **Web Dashboard**: Visual metrics at `http://localhost:8050`
- **Redis**: Algorithm status and configuration

## Performance Expectations

### Latency Performance
- **Target**: Configurable (5-20ms typical)
- **Adaptation**: Real-time adjustment based on actual conditions
- **Responsiveness**: Sub-millisecond scheduling decisions

### Throughput Impact
- **Balanced Mode**: Minimal throughput reduction
- **Aggressive Mode**: Some throughput trade-off for lower latency
- **Fairness Mode**: Prioritizes fair resource allocation

## Monitoring and Debugging

### Real-time Monitoring
```bash
# Watch console output
python muApp5_latency_scheduler.py --episodes 1000

# Monitor log file
tail -f muApp5_latency_log.txt

# Check Redis status
redis-cli GET algo
```

### Debug Mode
```bash
# Enable verbose logging
python muApp5_latency_scheduler.py --episodes 100 --debug
```

### Performance Analysis
```bash
# Analyze log files
python analyze_muapp5_logs.py muApp5_latency_log.txt
```

## Comparison with Other muApps

| Feature | muApp1 | muApp2 | muApp4 | muApp5 |
|---------|---------|---------|---------|---------|
| **Purpose** | Real-time inference | Training | Latency training | Real-time latency |
| **State Space** | [BL, CQI, MB] | [BL, CQI, MB] | [BL, CQI, LAT, MB, LP] | [BL, CQI, MB] |
| **Optimization** | Pre-trained model | Throughput | Latency (training) | Latency (real-time) |
| **Deployment** | Load model | Train model | Train model | Direct deployment |
| **Adaptation** | Static | Learning | Learning | Real-time |

## Advantages of muApp5

### ✅ **No Training Required**
- Immediate deployment
- No model conversion
- No training data needed

### ✅ **Real-time Adaptation**
- Adapts to changing conditions
- No retraining needed
- Immediate response to network changes

### ✅ **Interpretable Decisions**
- Clear algorithmic logic
- Traceable scheduling decisions
- Easy to debug and tune

### ✅ **Low Computational Overhead**
- No neural network inference
- Fast priority calculations
- Minimal memory usage

## Use Cases

### 1. **Ultra-Low Latency Applications**
```bash
# Gaming, AR/VR, real-time control
python muApp5_latency_scheduler.py --target-latency 1.0 --latency-weight 0.8
```

### 2. **Balanced Performance**
```bash
# General purpose with latency awareness
python muApp5_latency_scheduler.py --config-file muApp5_config.json
```

### 3. **Fair Resource Allocation**
```bash
# Ensure all UEs get fair treatment
python muApp5_latency_scheduler.py --fairness-factor 0.3
```

## Troubleshooting

### Common Issues

1. **No UE Data**
   - Check EdgeRIC system is running
   - Verify UEs are connected
   - Check `get_metrics_multi()` function

2. **High Latency Estimates**
   - Reduce `target_latency_ms`
   - Increase `latency_weight`
   - Check backlog accumulation

3. **Unfair Scheduling**
   - Increase `fairness_factor`
   - Reduce `latency_weight`
   - Monitor per-UE weights

### Debug Commands
```bash
# Check EdgeRIC connection
python -c "from edgeric_messenger import get_metrics_multi; print(get_metrics_multi())"

# Validate configuration
python muApp5_latency_scheduler.py --episodes 1 --config-file muApp5_config.json
```

## Future Enhancements

- **Machine Learning Integration**: Learn optimal weights from historical data
- **Multi-objective Optimization**: Pareto-optimal latency/throughput trade-offs
- **Predictive Scheduling**: Anticipate UE requirements
- **Dynamic Policy Switching**: Adapt policy based on traffic patterns

## Files

- `muApp5_latency_scheduler.py`: Main scheduler implementation
- `muApp5_config.json`: Configuration file with preset policies
- `README.md`: This documentation
- `muApp5_latency_log.txt`: Runtime log file (created during execution)

## Integration with Other muApps

muApp5 can work alongside other muApps:
- **muApp1**: Switch between model-based and algorithmic scheduling
- **muApp2**: Compare performance against throughput-optimized approaches
- **muApp4**: Use as baseline for training data generation

For more information, see the main EdgeRIC documentation.
