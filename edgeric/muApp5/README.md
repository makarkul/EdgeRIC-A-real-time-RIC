# muApp5: Real-time Latency-Optimized Scheduler

## Overview

muApp5 is a **real-time latency-optimized scheduler** designed to work directly with EdgeRIC's live system. Unlike muApp4 (which is for training) and muApp1 (which uses pre-trained models), muApp5 implements **algorithmic latency optimization** that adapts in real-time.

## Key Features

### ✅ **Direct Integration**
- Uses the same state space as muApp1: `[Backlog, CQI, Buffer_Size]`
- No model conversion or training required
- Immediate deployment capability

### ✅ **Real-time Latency Optimization**
- **Latency Estimation**: Estimates UE latency based on backlog, CQI, and service history
- **Adaptive Scheduling**: Prioritizes UEs with higher latency urgency
- **Channel Awareness**: Considers CQI for efficient resource allocation

### ✅ **Configurable Policies**
- **Aggressive Latency**: Minimizes latency at all costs
- **Balanced**: Balances latency, throughput, and fairness
- **Fairness Focused**: Ensures fair resource allocation

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
