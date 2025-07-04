from stream_rl.registry import register_reward


@register_reward("default")
def default_reward(self, *, arg_1=None, arg_2=None, **kwargs):
    pass


@register_reward("throughput")
def throughput(total_bytes_transferred, backlog_lens, stalls):
    #return 8*total_bytes_transferred
    return total_bytes_transferred


@register_reward("negative_backlog_len")
def neg_bl(total_bytes_transferred, backlog_lens, stalls):
    return -1 * sum(backlog_lens)


@register_reward("stalls")
def stalls(total_bytes_transferred, backlog_lens, stalls):
    return stalls


@register_reward("SimpleCost")
def simple_cost(action, no_playout_previously, cost_params):
    backlog_action, playout_action = action
    r = cost_params["r"]
    c_1 = cost_params["c_1"]
    c_2 = cost_params["c_2"]
    lmbda_ = cost_params["lambda"]
    if not playout_action:
        cost = c_2 if no_playout_previously else c_1
    else:
        cost = -r * playout_action
    cost += lmbda_ * backlog_action**1.1
    return -1 * cost


@register_reward("Cost_1")
def cost1(beta_Ut, Y_t, V_t, cost_params):
    r = cost_params["r"]
    lmbda_ = cost_params["lambda"]
    cost = -r * beta_Ut if Y_t > 0 else 0
    cost += lmbda_ * V_t
    return -1 * cost


@register_reward("negative_latency")
def negative_latency(total_bytes_transferred, backlog_lens, stalls, avg_latency=None, latency_config=None):
    """
    Latency-optimized reward function.
    Minimizes latency while maintaining reasonable throughput.
    """
    if avg_latency is None or latency_config is None:
        # Fallback to throughput if latency data not available
        return total_bytes_transferred
    
    target_latency = latency_config.get("target_latency", 10000)  # 10ms default
    latency_penalty_weight = latency_config.get("latency_penalty_weight", 1.0)
    throughput_weight = latency_config.get("throughput_weight", 0.1)
    max_latency_penalty = latency_config.get("max_latency_penalty", 1000)
    
    # Calculate latency penalty (higher latency = higher penalty)
    latency_excess = max(0, avg_latency - target_latency)
    latency_penalty = min(latency_penalty_weight * latency_excess, max_latency_penalty)
    
    # Small positive reward for throughput to maintain QoS
    throughput_reward = throughput_weight * total_bytes_transferred
    
    # Combined reward: minimize latency, maintain throughput
    reward = throughput_reward - latency_penalty
    
    return reward


@register_reward("latency_weighted")
def latency_weighted(total_bytes_transferred, backlog_lens, stalls, avg_latency=None, latency_config=None):
    """
    Alternative latency reward: inverse latency weighting.
    Higher reward for lower latency.
    """
    if avg_latency is None or latency_config is None:
        return total_bytes_transferred
    
    throughput_weight = latency_config.get("throughput_weight", 0.5)
    latency_weight = latency_config.get("latency_penalty_weight", 1.0)
    
    # Inverse latency reward (lower latency = higher reward)
    # Add small constant to avoid division by zero
    latency_reward = latency_weight * (1000000.0 / (avg_latency + 1000))
    
    # Throughput component
    throughput_reward = throughput_weight * total_bytes_transferred / 1000000.0
    
    return latency_reward + throughput_reward
